# core/views_quiz.py (SAFE + SKILL ENGINE VERSION)

import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import QuizChapter, QuizAttempt, TopicStat, Book
from core.utils_skill_engine import recompute_skill_profile


# ======================================================
# GET QUIZ
# ======================================================
@csrf_exempt
def get_quiz(request):
    """Return latest quiz (exam mode)"""
    quiz_id = request.GET.get('quiz_id')

    if quiz_id:
        try:
            qc = QuizChapter.objects.get(pk=quiz_id)
            return JsonResponse({
                'quiz_id': qc.id,
                'questions': qc.questions_json
            })
        except QuizChapter.DoesNotExist:
            return JsonResponse({'error': 'Quiz not found'}, status=404)

    # Return latest quiz
    qc = QuizChapter.objects.order_by('-created_at').first()
    if not qc:
        return JsonResponse({'questions': []})

    return JsonResponse({
        'quiz_id': qc.id,
        'questions': qc.questions_json
    })


# ======================================================
# START QUIZ
# ======================================================
@csrf_exempt
def start_quiz(request):
    """
    Simple start — DOES NOT require QuizInstance.
    Returns timestamp only.
    """
    try:
        data = json.loads(request.body or '{}')
        quiz_id = data.get("quiz_id")

        qc = QuizChapter.objects.get(pk=quiz_id)

        return JsonResponse({
            "started": True,
            "quiz_id": quiz_id,
            "started_at": timezone.now().isoformat()
        })

    except Exception as e:
        return HttpResponseBadRequest(str(e))


# ======================================================
# SUBMIT QUIZ (MASTER VERSION)
# ======================================================
@csrf_exempt
def submit_quiz(request):
    try:
        data = json.loads(request.body or '{}')

        quiz_id = data.get("quiz_id")
        answers = data.get("answers", [])

        qc = QuizChapter.objects.get(pk=quiz_id)
        questions = qc.questions_json.get("questions", [])

        correct = 0
        total = len(questions)

        # -------------------------
        # Evaluate answers
        # -------------------------
        for i, q in enumerate(questions):
            if i < len(answers) and answers[i] == q.get("answer"):
                correct += 1

        score = (correct / total * 100) if total else 0

        if request.user.is_authenticated:
            from core.utils_skill_engine import recompute_skill_profile
            recompute_skill_profile(request.user)


        # -------------------------
        # Save QuizAttempt
        # -------------------------
        attempt = QuizAttempt.objects.create(
            user=request.user if request.user.is_authenticated else None,
            quiz=qc,
            answers_json=answers,
            submitted_at=timezone.now(),
            score=score,
            correct_count=correct,
            total_questions=total
        )

        # -------------------------
        # 🔥 UPDATE TOPIC STAT
        # -------------------------
        if request.user.is_authenticated:
            book = Book.objects.filter(slug=qc.subject).first()

            if book:
                topic_stat, _ = TopicStat.objects.get_or_create(
                    user=request.user,
                    book=book,
                    topic=qc.chapter
                )

                topic_stat.attempts += 1
                topic_stat.correct += correct

                topic_stat.mastery_score = (
                    (topic_stat.correct / (topic_stat.attempts * total)) * 100
                    if total else 0
                )

                topic_stat.last_attempted = timezone.now()
                topic_stat.save()

                # 🔥 RECOMPUTE SKILL PROFILE
                recompute_skill_profile(request.user)

        # -------------------------
        # Final Response
        # -------------------------
        return JsonResponse({
            "status": "submitted",
            "score": round(score, 2),
            "attempt_id": attempt.id
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ======================================================
# PROCTOR LOG (DISABLED)
# ======================================================
@csrf_exempt
def proctor_log(request):
    return JsonResponse({"ok": True})


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

    # 🔥 RECOMPUTE SKILL PROFILE AFTER WEEKLY SCORE UPDATE
    from core.utils_skill_engine import recompute_skill_profile
    recompute_skill_profile(request.user)

    return JsonResponse({
        "score": quiz.score,
        "total": total
    })
