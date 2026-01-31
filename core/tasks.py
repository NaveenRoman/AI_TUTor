# core/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.mail import send_mail

import json
import os

# ============================================================
# IMPORT MODELS + QUIZ GENERATORS
# ============================================================
from .models import QuizChapter, QuizAttempt, Notification, TopicStat
from .utils import extract_text, summarize_text, build_embeddings
from .quiz_generator import generate_full_quiz, generate_weekly_quiz_for_text

User = get_user_model()


# ============================================================
# 1) ASYNC FILE PROCESSING (PHASE 1)
# ============================================================
@shared_task
def process_file_async(path, original_name):
    """
    Background task to:
        - Extract text
        - Summaries
        - Embeddings
        - Save .meta.json
    """
    try:
        text = extract_text(path)
        summary_data = summarize_text(text)
        embeddings = build_embeddings(text)

        meta = {
            "summary": summary_data.get("summary"),
            "keyPointsHtml": summary_data.get("keyPointsHtml")
        }

        with open(path + ".meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)

        print(f"[OK] Finished file: {original_name}")

    except Exception as e:
        print("[ERROR] process_file_async:", e)



# ============================================================
# 2) DAILY QUIZ GENERATOR (PHASE 3)
# ============================================================
@shared_task
def generate_daily_quizzes():
    """
    Auto-generates quizzes daily for every chapter in BOOK_KB.
    Runs via Celery Beat every morning at 6 AM.
    """
    try:
        from .books_loader import BOOK_KB

        print("[INFO] Daily quiz generation started...")

        for subject, subject_data in BOOK_KB.items():
            sections = subject_data.get("sections", {})

            for chapter_name, chapter_data in sections.items():
                sentences = chapter_data.get("sentences", [])
                raw_text = " ".join(sentences)

                # Generate a 25-question quiz
                quiz = generate_full_quiz(raw_text)

                QuizChapter.objects.create(
                    subject=subject,
                    chapter=chapter_name,
                    quiz_type="daily",
                    questions_json=quiz
                )

                print(f"[OK] Daily quiz created: {subject} — {chapter_name}")

        print("[DONE] Daily quiz generation completed.")

    except Exception as e:
        print("[ERROR] Daily quiz generation failed:", e)



# ============================================================
# 3) WEEKLY QUIZ GENERATOR (PHASE 4)
# ============================================================
@shared_task
def generate_weekly_quizzes():
    """
    Creates weekly quizzes based on weak topics for each active user.
    Triggered by Celery every Monday at 6 AM.
    """
    users = User.objects.filter(is_active=True)

    for user in users:
        # Fetch bottom 5 weak topics
        weak_topics = TopicStat.objects.filter(user=user).order_by('mastery_score')[:5]
        topic_list = [t.topic for t in weak_topics]

        # Generate quiz from weak topics
        quiz_json = generate_weekly_quiz_for_text(topic_list, num_questions=25)

        quiz_obj = QuizChapter.objects.create(
            subject="weekly",
            chapter=f"week-{timezone.now().isocalendar()[1]}",
            quiz_type="weekly",
            questions_json=quiz_json
        )

        # Notification for frontend
        Notification.objects.create(
            user=user,
            title="Your weekly quiz is ready!",
            body="We created your weekly 25-question test based on your weak topics.",
            payload={"quiz_id": quiz_obj.id}
        )

        # Email (optional)
        try:
            send_mail(
                subject="Your Weekly Quiz is Ready!",
                message="Log in to the AI Tutor to take your weekly quiz.",
                from_email="no-reply@navindhu-ai.com",
                recipient_list=[user.email],
                fail_silently=True
            )
        except Exception:
            pass

    print("[DONE] Weekly quizzes generated.")



# ============================================================
# 4) UPDATE WEAK TOPICS DAILY (PHASE 5)
# ============================================================
@shared_task
def update_user_weak_topics():
    """
    Recalculates mastery score for each topic for every user.
    """
    try:
        for stat in TopicStat.objects.all():
            if stat.attempts > 0:
                stat.mastery_score = stat.correct / stat.attempts
                stat.save()

        print("[OK] Weak-topic stats updated.")

    except Exception as e:
        print("[ERROR] update_user_weak_topics failed:", e)
