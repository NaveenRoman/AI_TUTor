import os
import json
import traceback
import nltk
from django.core.mail import EmailMultiAlternatives

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes

# 🔹 Django REST Framework
from rest_framework.decorators import api_view
from rest_framework.response import Response

# 🔹 Django shortcuts & utils
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings

from core.models import QuizChapter
import random

from django.utils import timezone   # ADD THIS AT TOP

from django.http import JsonResponse, Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from core.books_loader import BOOK_KB
from core.utils import extract_text
from core.utils_format import format_answer_core
from core.views.views_chat import (
    get_model,
    retrieve_top_k,
    detect_template_type,
    choose_language,
    VOICE_STATE,
)

from core.models import (
    Book,
    Chapter,
    UserChapterProgress,
)




# ======================================================
# BOOKS PAGE (HTML)
# ======================================================
def book_topics_page(request):
    books = {
        subject: {
            "topics": list(info["sections"].keys()),
            "count": len(info["sections"]),
        }
        for subject, info in BOOK_KB.items()
    }
    return render(request, "books/topics.html", {"books": books})


# ADD THIS FUNCTION BACK
def book_topic_page(request, subject, page):
    subject = subject.lower()
    template_path = f"books/{subject}/{page}.html"
    try:
        return render(request, template_path)
    except Exception:
        raise Http404("Topic not found")





# ======================================================
# ASK QUESTION FROM SPECIFIC TOPIC (API)
# ======================================================
@csrf_exempt
def ask_book_topic(request):
    try:
        data = json.loads(request.body or "{}")

        subject = data.get("subject")
        topic = data.get("topic") or data.get("page")
        question = data.get("question", "").strip()
        full = bool(data.get("full", False))

        if not subject or not topic:
            return JsonResponse({"error": "subject and topic required"}, status=400)

        subject = subject.lower()

        if subject not in BOOK_KB:
            return JsonResponse({"error": "Subject not found"}, status=404)

        folder = BOOK_KB[subject]["folder"]
        topic_path = os.path.join(folder, topic)

        if not os.path.isfile(topic_path):
            return JsonResponse({"error": "Topic not found"}, status=404)

        # ======================================================
        # 🎤 INTERVIEW MODE DETECTION
        # ======================================================
        if "interview question" in question.lower():

            import random

            interview_templates = [
                "Explain JVM architecture.",
                "What is the difference between JDK, JRE and JVM?",
                "Explain OOP principles in Java.",
                "What is multithreading in Java?",
                "What is the difference between HashMap and Hashtable?",
                "Explain exception handling in Java.",
                "What is garbage collection?",
                "What is the difference between abstract class and interface?"
            ]

            clean_question = random.choice(interview_templates)

            return JsonResponse({
                "answer": clean_question,
                "subject": subject,
                "topic": topic,
                "mode": "interview",
            })

        # ======================================================
        # 📘 NORMAL TUTOR MODE
        # ======================================================

        text = extract_text(topic_path)
        sentences = nltk.sent_tokenize(text)

        embeddings = get_model().encode(sentences, convert_to_tensor=True)

        best_text = retrieve_top_k(sentences, embeddings, question)

        mode = detect_template_type(question, data)
        language = choose_language(data, question)

        if full:
            mode = "full_topic"

        answer = format_answer_core(
            question=question,
            content=best_text,
            detail_level="long" if full else "auto",
            history=None,
            template_type=mode,
            language=language,
        )

        return JsonResponse({
            "answer": answer,
            "subject": subject,
            "topic": topic,
            "mode": mode,
            "voice": {"autoplay": VOICE_STATE.get("autoplay", False)},
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


# ======================================================
# MARK TOPIC COMPLETED (API) ✅ FIXED
# ======================================================
# ======================================================
# MARK TOPIC COMPLETED (API)
# ======================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def topic_complete_api(request):
    print("🔥 topic_complete_api CALLED")

    user = request.user
    subject = request.data.get("subject")
    topic_slug = request.data.get("topic")

    if not subject or not topic_slug:
        return Response({"success": False}, status=400)

    import re
    match = re.search(r"(\d+)$", topic_slug)
    if not match:
        return Response({"success": False}, status=400)

    order = int(match.group(1))

    chapter = get_object_or_404(
        Chapter,
        book__slug=subject,
        order=order
    )

    # ✅ Get or create progress
    progress, created = UserChapterProgress.objects.get_or_create(
        user=user,
        chapter=chapter
    )

    # ✅ Prevent duplicate completion
    if progress.completed:
        return Response({"success": True})

    # ✅ Mark as completed
    progress.completed = True
    progress.completed_at = timezone.now()
    progress.save()

    # =====================================================
    # 🔥 SMART QUIZ GENERATOR
    # =====================================================

    folder = os.path.join(settings.BASE_DIR, "templates", "books", subject)
    file_name = f"{subject}-topic{order}.html"
    file_path = os.path.join(folder, file_name)

    if not os.path.exists(file_path):
        return Response(
            {"success": False, "error": "Chapter file not found"},
            status=500
        )

    text = extract_text(file_path)
    sentences = nltk.sent_tokenize(text)

    questions = []

    if len(sentences) >= 5:
        selected = random.sample(sentences, 5)
    else:
        selected = sentences

    for sentence in selected:
        words = sentence.split()

        if len(words) < 6:
            continue

        answer_word = random.choice(words[1:-1])
        question_text = sentence.replace(answer_word, "______", 1)

        options = [answer_word]

        while len(options) < 4:
            fake = random.choice(words)
            if fake not in options:
                options.append(fake)

        random.shuffle(options)

        questions.append({
            "question": question_text,
            "options": options,
            "answer": answer_word
        })

    # 🔹 Fallback (if no valid questions generated)
    if not questions:
        questions.append({
            "question": f"What is the main concept of {chapter.title}?",
            "options": ["Concept A", "Concept B", "Concept C", "Concept D"],
            "answer": "Concept A"
        })

    # =====================================================
    # ✅ CREATE QUIZ RECORD
    # =====================================================

    quiz = QuizChapter.objects.create(
        subject=subject,
        chapter=chapter.title,
        quiz_type="chapter",
        questions_json=questions
    )

    quiz_url = request.build_absolute_uri(
    f"/quiz/{quiz.id}/")


    # =====================================================
    # 📧 SEND EMAIL
    # =====================================================

    subject_line = "🎯 Topic Completed – Quiz Unlocked"
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [user.email]

    text_content = f"""
Hi {user.username},

You completed: {chapter.title}

Start your quiz here:
{quiz_url}
"""

    html_content = f"""
<h2>🎯 Quiz Unlocked!</h2>
<p>Hi <strong>{user.username}</strong>,</p>
<p>You completed: <b>{chapter.title}</b></p>

<p>
<a href="{quiz_url}" style="
  padding:12px 20px;
  background:#2563eb;
  color:white;
  text-decoration:none;
  border-radius:6px;
  font-weight:bold;">
  🚀 Start Quiz
</a>
</p>

<p>Keep learning and growing! 💪</p>
"""

    msg = EmailMultiAlternatives(subject_line, text_content, from_email, to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    print("✅ EMAIL FUNCTION FINISHED")

    return Response({"success": True})




# ======================================================
# BOOK PROGRESS (FINAL – STRONG SEQUENTIAL UNLOCK)
# ======================================================
from django.contrib.auth.decorators import login_required

@login_required
def book_progress_api(request):
    subject = request.GET.get("subject")

    try:
        book = Book.objects.get(slug=subject)
    except Book.DoesNotExist:
        return JsonResponse({
            "completed_chapters": 0,
            "total_chapters": 0,
            "percent_complete": 0,
            "chapters": []
        })

    chapters = Chapter.objects.filter(book=book).order_by("order")
    total = chapters.count()

    user = request.user

    completed_chapters = UserChapterProgress.objects.filter(
        user=user,
        chapter__book=book,
        completed=True
    ).values_list("chapter_id", flat=True)

    completed_set = set(completed_chapters)
    completed_count = len(completed_set)

    percent = int((completed_count / total) * 100) if total else 0

    chapter_list = []
    previous_completed = True  # first chapter unlocked

    for ch in chapters:

        completed = ch.id in completed_set

        # unlock only if previous chapter was completed
        if previous_completed:
            unlocked = True
        else:
            unlocked = False

        chapter_list.append({
            "id": ch.id,
            "order": ch.order,
            "title": ch.title,
            "completed": completed,
            "unlocked": unlocked,
        })

        previous_completed = completed  # next depends on this

    return JsonResponse({
        "completed_chapters": completed_count,
        "total_chapters": total,
        "percent_complete": percent,
        "chapters": chapter_list,
    })

