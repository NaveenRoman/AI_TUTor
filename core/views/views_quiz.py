import json
import random
import traceback
from datetime import date, timedelta

from core.models import UsageLog

from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone


from core.models import (
    QuizChapter,
    QuizInstance,
    QuizAttempt,
    DailyQuiz,
    ProctorLog,
    WeeklyQuiz,
    TopicStat,
)

from core.books_loader import BOOK_KB
from core.quiz_generator import (
    generate_full_quiz,
    generate_mixed_quiz_from_text,
    combine_texts_from_sections,
)



# ======================================================
# AUTO QUIZ GENERATION (ON CHAPTER COMPLETE)
# ======================================================
def auto_generate_chapter_quiz(subject, topic_slug):
    """
    Generates and stores a quiz for a topic file (java-topic1.html)
    """

    try:
        from core.books_loader import BOOK_KB
        from core.quiz_generator import generate_full_quiz
        from core.models import QuizChapter

        if subject not in BOOK_KB:
            return None

        # Find matching file
        topic_file = f"{topic_slug}.html"

        all_sentences = []

        for heading, data in BOOK_KB[subject]["sections"].items():
            if data.get("file") == topic_file:
                all_sentences.extend(data["sentences"])

        if not all_sentences:
            print("❌ No sentences found for quiz generation")
            return None

        raw_text = " ".join(all_sentences)

        quiz = generate_full_quiz(raw_text)

        return QuizChapter.objects.create(
            subject=subject,
            chapter=topic_slug,   # IMPORTANT
            quiz_type="auto",
            questions_json=quiz
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None





# ======================================================
# PER-CHAPTER QUIZ GENERATION
# ======================================================
@csrf_exempt
@require_http_methods(["POST"])
def generate_quiz(request):
    """
    Generates quiz for a specific subject + chapter
    """
    try:
        payload = json.loads(request.body or "{}")
        subject = payload.get("subject")
        chapter = payload.get("chapter")

        if not subject or not chapter:
            return JsonResponse({"error": "subject & chapter required"}, status=400)

        if subject not in BOOK_KB:
            return JsonResponse({"error": "Subject not found"}, status=404)

        if chapter not in BOOK_KB[subject]["sections"]:
            return JsonResponse({"error": "Chapter not found"}, status=404)

        sentences = BOOK_KB[subject]["sections"][chapter]["sentences"]
        raw_text = " ".join(sentences)

        quiz = generate_full_quiz(raw_text)

        obj = QuizChapter.objects.create(
            subject=subject,
            chapter=chapter,
            quiz_type="full",
            questions_json=quiz
        )

        return JsonResponse({
            "message": "Quiz generated",
            "quiz_id": obj.id,
            "quiz": quiz
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


# ======================================================
# FETCH QUIZ
# ======================================================
@csrf_exempt
def get_quiz(request, quiz_id=None):

    try:
        # If quiz_id comes from URL
        if quiz_id:
            qc = QuizChapter.objects.get(pk=quiz_id)
            return JsonResponse({
                "quiz_id": qc.id,
                "questions": qc.questions_json
            })

        # If quiz_id comes from query param
        quiz_id_param = request.GET.get("quiz_id")

        if quiz_id_param:
            qc = QuizChapter.objects.get(pk=quiz_id_param)
            return JsonResponse({
                "quiz_id": qc.id,
                "questions": qc.questions_json
            })

        # Otherwise return latest quiz
        qc = QuizChapter.objects.order_by("-created_at").first()

        if not qc:
            return JsonResponse({"questions": []})

        return JsonResponse({
            "quiz_id": qc.id,
            "questions": qc.questions_json
        })

    except QuizChapter.DoesNotExist:
        return JsonResponse({"error": "Quiz not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



# ======================================================
# QUIZ INSTANCE (START)
# ======================================================
@csrf_exempt
@require_http_methods(["POST"])
def start_quiz(request):
    try:
        payload = json.loads(request.body or "{}")
        quiz_id = payload.get("quiz_id")
        student_id = payload.get("student_id", "anon")

        quiz = QuizChapter.objects.get(pk=quiz_id)

        inst = QuizInstance.objects.create(
            quiz=quiz,
            student_id=student_id
        )

        return JsonResponse({
            "instance_id": inst.id,
            "started_at": inst.started_at.isoformat()
        })

    except QuizChapter.DoesNotExist:
        return HttpResponseBadRequest("Quiz not found")
    except Exception as e:
        return HttpResponseBadRequest(str(e))

# ======================================================
# SUBMIT QUIZ + PROCTOR DATA
# ======================================================
# ======================================================
# SUBMIT QUIZ + PROCTOR DATA (WEEK 3 INTELLIGENCE VERSION)
# ======================================================
@csrf_exempt
@require_http_methods(["POST"])
def submit_quiz(request):

    
    UsageLog.objects.create(
    user=user,
    action="quiz"
)

    try:
        payload = json.loads(request.body or "{}")

        quiz_id = payload.get("quiz_id")
        answers = payload.get("answers", [])
        instance_id = payload.get("instance_id")
        proctor_events = payload.get("proctor_events", [])

        user = request.user if request.user.is_authenticated else None

        # ----------------------------------
        # FETCH QUIZ
        # ----------------------------------
        quiz = QuizChapter.objects.get(pk=quiz_id)

        # ----------------------------------
        # FETCH QUIZ INSTANCE (OPTIONAL)
        # ----------------------------------
        inst = None
        if instance_id:
            try:
                inst = QuizInstance.objects.get(pk=instance_id)
            except QuizInstance.DoesNotExist:
                inst = None

        # ----------------------------------
        # EVALUATE QUIZ
        # ----------------------------------
        score = 0
        total = 0
        wrong = []

        questions = quiz.questions_json  # assuming list

        for idx, q in enumerate(questions):
            total += 1
            given = answers[idx] if idx < len(answers) else None
            correct_answer = q.get("answer")

            if str(given).strip().lower() == str(correct_answer).strip().lower():
                score += 1
            else:
                wrong.append({
                    "question": q.get("question"),
                    "topic": quiz.chapter
                })

        percent_score = (score / total) * 100 if total else 0

        # ----------------------------------
        # CREATE QUIZ ATTEMPT
        # ----------------------------------
        attempt = QuizAttempt.objects.create(
            user=user,
            quiz=quiz,
            instance=inst,
            answers_json=answers,
            score=percent_score,
            correct_count=score,
            total_questions=total,
            submitted_at=timezone.now()
        )

        # ----------------------------------
        # 🔥 WEEK 3: UPDATE TOPIC STAT (INTELLIGENCE CORE)
        # ----------------------------------
        if user:
            from core.models import Book, TopicStat
            from core.utils_skill_engine import recompute_skill_profile

            book = Book.objects.filter(slug=quiz.subject).first()

            if book:
                topic_stat, _ = TopicStat.objects.get_or_create(
                    user=user,
                    book=book,
                    topic=quiz.chapter
                )

                previous_mastery = topic_stat.mastery_score

                topic_stat.attempts += 1
                topic_stat.correct += score

                # Calculate new mastery
                new_mastery = (
                    (topic_stat.correct / (topic_stat.attempts * total)) * 100
                    if total else 0
                )

                # -------------------------
                # 1️⃣ IMPROVEMENT RATE
                # -------------------------
                improvement = new_mastery - previous_mastery
                topic_stat.improvement_rate = round(improvement, 2)
                topic_stat.last_mastery_score = previous_mastery

                if improvement > 0:
                    topic_stat.last_improved_at = timezone.now()

                # -------------------------
                # 2️⃣ DECAY ENGINE
                # -------------------------
                if topic_stat.last_attempted:
                    days_idle = (timezone.now() - topic_stat.last_attempted).days
                    if days_idle > 14:
                        new_mastery *= 0.95  # 5% decay

                topic_stat.mastery_score = round(new_mastery, 2)
                topic_stat.last_attempted = timezone.now()
                topic_stat.save()

                # -------------------------
                # 3️⃣ ADAPTIVE TRIGGER
                # -------------------------
                recompute_skill_profile(user)

        # ----------------------------------
        # AI TIP GENERATION
        # ----------------------------------
        if wrong:
            attempt.ai_tip = generate_ai_tip(wrong)
            attempt.save()

        # ----------------------------------
        # SAVE PROCTOR EVENTS
        # ----------------------------------
        for ev in proctor_events:
            ProctorLog.objects.create(
                quiz_instance=inst,
                student_id=getattr(user, "username", "anon"),
                event=ev
            )

        # ----------------------------------
        # FINISH QUIZ INSTANCE
        # ----------------------------------
        if inst:
            inst.finished_at = timezone.now()
            inst.save()

        # ----------------------------------
        # FINAL RESPONSE
        # ----------------------------------
        return JsonResponse({
            "status": "submitted",
            "attempt_id": attempt.id,
            "score": percent_score,
            "correct": score,
            "total": total,
            "ai_tip": attempt.ai_tip
        })

    except QuizChapter.DoesNotExist:
        return JsonResponse({"error": "Quiz not found"}, status=404)

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)





# ======================================================
# DAILY QUIZ ROTATION LOGIC
# ======================================================
def _pick_subject_by_rotation():
    subjects = list(BOOK_KB.keys())
    if not subjects:
        return None

    epoch = date(2025, 1, 1)
    today = date.today()
    idx = (today - epoch).days % len(subjects)
    return subjects[idx]

# ======================================================
# GENERATE DAILY QUIZ (BASED ON USER LEARNING)
# ======================================================
@csrf_exempt
@require_http_methods(["POST"])
def generate_daily_quiz(request):
    try:
        payload = json.loads(request.body or "{}")
        force = bool(payload.get("force", False))
        subject_override = payload.get("subject")

        today = date.today()

        existing = DailyQuiz.objects.filter(date=today).first()
        if existing and not force:
            return JsonResponse({"message": "Already exists"})

        # ✅ GET USER'S MOST RECENT LEARNING
        from core.models import ChapterCompletion

        recent = (
            ChapterCompletion.objects
            .filter(user=request.user)
            .order_by("-completed_at")
            .first()
        )

        # ✅ SUBJECT SELECTION LOGIC
        if subject_override and subject_override in BOOK_KB:
            subject = subject_override
        elif recent and recent.subject in BOOK_KB:
            subject = recent.subject
        else:
            subject = _pick_subject_by_rotation()

        sections = BOOK_KB[subject]["sections"]

        chapters = random.sample(
            list(sections.keys()),
            min(len(sections), 6)
        )

        texts = [
            " ".join(sections[ch]["sentences"])
            for ch in chapters
        ]

        raw_text = combine_texts_from_sections(texts)

        quiz = generate_mixed_quiz_from_text(
            raw_text,
            total_questions=25
        )

        dq, _ = DailyQuiz.objects.update_or_create(
            date=today,
            defaults={"questions_json": quiz}
        )

        return JsonResponse({
            "message": "Daily quiz ready",
            "subject": subject,
            "quiz": quiz
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

# ======================================================
# GET DAILY QUIZ
# ======================================================
@csrf_exempt
@require_http_methods(["GET"])
def get_daily_quiz(request):
    try:
        today = date.today()
        dq = DailyQuiz.objects.filter(date=today).first()

        if dq:
            return JsonResponse({
                "date": str(today),
                "quiz": dq.questions_json,
                "new": False
            })

        # auto-generate if missing
        subject = _pick_subject_by_rotation()
        sections = BOOK_KB[subject]["sections"]

        chapters = random.sample(
            list(sections.keys()),
            min(len(sections), 6)
        )

        texts = [
            " ".join(sections[ch]["sentences"])
            for ch in chapters
        ]

        raw_text = combine_texts_from_sections(texts)
        quiz = generate_mixed_quiz_from_text(raw_text, total_questions=25)

        dq = DailyQuiz.objects.create(
            date=today,
            questions_json=quiz
        )

        return JsonResponse({
            "date": str(today),
            "quiz": quiz,
            "new": True
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


# ======================================================
# SUBMIT DAILY QUIZ (AUTO-GRADE)
# ======================================================
@csrf_exempt
@require_http_methods(["POST"])
def submit_daily_quiz(request):
    try:
        payload = json.loads(request.body or "{}")

        answers = payload.get("answers", {})
        date_str = payload.get("date")

        quiz_date = date.fromisoformat(date_str) if date_str else date.today()
        dq = DailyQuiz.objects.filter(date=quiz_date).first()

        if not dq:
            return JsonResponse({"error": "Quiz not found"}, status=404)

        score = 0
        total = 0
        wrong = []

        # ===============================
        # ✅ SAFE MCQ CHECK
        # ===============================
        mcq_answers = answers.get("mcq", [])

        for idx, q in enumerate(dq.questions_json.get("mcq", [])):
            total += 1
            given = mcq_answers[idx] if idx < len(mcq_answers) else None

            if str(given).lower() == str(q.get("answer")).lower():
                score += 1
            else:
                wrong.append({
                    "type": "mcq",
                    "question": q.get("question"),
                    "expected": q.get("answer"),
                    "given": given
                })

        # ===============================
        # ✅ SAFE FILL CHECK
        # ===============================
        fill_answers = answers.get("fill", [])

        for idx, q in enumerate(dq.questions_json.get("fill", [])):
            total += 1
            given = fill_answers[idx] if idx < len(fill_answers) else None

            if str(given).lower() == str(q.get("answer")).lower():
                score += 1
            else:
                wrong.append({
                    "type": "fill",
                    "question": q.get("question"),
                    "expected": q.get("answer"),
                    "given": given
                })

        percent = (score / total) * 100 if total else 0

        return JsonResponse({
            "score": percent,
            "correct": score,
            "total": total,
            "wrong": wrong
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)



# ======================================================
# PROCTOR LOG (LIVE EVENTS)
# ======================================================
@csrf_exempt
@require_http_methods(["POST"])
def proctor_log(request):
    try:
        payload = json.loads(request.body or "{}")
        instance_id = payload.get("instance_id")
        student = payload.get("student", "anon")
        event = payload.get("event")

        inst = None
        if instance_id:
            try:
                inst = QuizInstance.objects.get(pk=instance_id)
            except QuizInstance.DoesNotExist:
                inst = None

        ProctorLog.objects.create(
            quiz_instance=inst,
            student_id=student,
            event=event
        )

        return JsonResponse({"ok": True})

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)


def _week_start():
    today = date.today()
    return today - timedelta(days=today.weekday())

@login_required
def generate_weekly_quiz(request):
    user = request.user
    week = _week_start()

    if WeeklyQuiz.objects.filter(user=user, week_start=week).exists():
        return JsonResponse({"message": "Weekly quiz already generated"})

    weak_topics = (
        TopicStat.objects
        .filter(user=user, mastery_score__lt=40)
        .order_by("mastery_score")
        .values_list("topic", flat=True)[:5]
    )

    texts = []

    for topic in weak_topics:
        for subj, info in BOOK_KB.items():
            if topic in info["sections"]:
                texts.append(
                    " ".join(info["sections"][topic]["sentences"])
                )

    if not texts:
        # fallback
        subj = random.choice(list(BOOK_KB.keys()))
        texts = [
            " ".join(sec["sentences"])
            for sec in list(BOOK_KB[subj]["sections"].values())[:5]
        ]

    quiz = generate_mixed_quiz_from_text(
        " ".join(texts),
        total_questions=30
    )

    WeeklyQuiz.objects.create(
        user=user,
        week_start=week,
        questions_json=quiz
    )

    return JsonResponse({
        "week": str(week),
        "quiz": quiz
    })

@login_required
@require_http_methods(["POST"])
def submit_weekly_quiz(request):
    payload = json.loads(request.body or "{}")
    answers = payload.get("answers", {})

    week = _week_start()
    quiz = get_object_or_404(
        WeeklyQuiz, user=request.user, week_start=week
    )

    score = 0
    total = 0

    for idx, q in enumerate(quiz.questions_json.get("mcq", [])):
        total += 1
        if str(answers.get("mcq", [None])[idx]).lower() == str(q["answer"]).lower():
            score += 1

    quiz.score = (score / total) * 100 if total else 0
    quiz.save()

    return JsonResponse({
        "score": quiz.score,
        "total": total
    })



def generate_ai_tip(wrong_questions):
    if not wrong_questions:
        return "Excellent work! Keep practicing."

    topics = set()
    for q in wrong_questions:
        if "topic" in q:
            topics.add(q["topic"])

    tips = [f"Revise core concepts of {t}" for t in topics]
    return " | ".join(tips)




from django.shortcuts import render

@login_required
def topic_quiz_page(request, quiz_id):
    quiz = get_object_or_404(QuizChapter, id=quiz_id)

    return render(request, "core/topic_quiz.html", {
        "quiz": quiz,
        "quiz_id": quiz.id,
    })


