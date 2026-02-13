import json
import re

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from core.utils_interview_engine import (
    get_or_create_weekly_session,
    update_adaptive_difficulty
)
from core.utils_behavior_engine import analyze_session_behavior
from core.utils_skill_engine import recompute_skill_profile

from core.models import (
    InterviewResponse,
    UsageLog,
    InterviewSession,
    SkillProfile
)


# ======================================================
# LOCAL HR INTERVIEW EVALUATOR
# ======================================================
@csrf_exempt
def hr_interviewer(request):

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=403)

    try:
        data = json.loads(request.body or "{}")

        question = data.get("question", "").strip()
        answer = data.get("answer", "").strip()

        if not question or not answer:
            return JsonResponse(
                {"error": "Question and answer required"},
                status=400
            )

        # ----------------------------------------
        # BASIC SCORING LOGIC
        # ----------------------------------------
        word_count = len(answer.split())

        java_keywords = [
            "java", "jvm", "class", "object",
            "method", "memory", "runtime",
            "inheritance", "polymorphism"
        ]

        keyword_hits = sum(
            1 for k in java_keywords
            if re.search(rf"\b{k}\b", answer.lower())
        )

        technical_score = min(10, 3 + keyword_hits)
        clarity_score = 8 if word_count > 60 else 5
        communication_score = 7 if "." in answer else 5
        confidence_score = 7 if word_count > 40 else 5

        total_score = round(
            (technical_score + clarity_score + communication_score + confidence_score) / 4,
            1
        )

        # ----------------------------------------
        # WEEKLY SESSION LOCK
        # ----------------------------------------
        try:
            session = get_or_create_weekly_session(request.user)
        except Exception:
            return JsonResponse({
                "error": "You have already completed this week's interview."
            }, status=403)

        # ----------------------------------------
        # SAVE RESPONSE
        # ----------------------------------------
        InterviewResponse.objects.create(
            session=session,
            question_text=question,
            answer_text=answer,
            technical_score=technical_score,
            clarity_score=clarity_score,
            communication_score=communication_score,
            confidence_score=confidence_score,
            total_score=total_score,
            answer_length=word_count,
            time_taken_seconds=data.get("time_taken", 0)
        )

        # ----------------------------------------
        # UPDATE SESSION ANALYTICS
        # ----------------------------------------
        responses = session.responses.all()
        session.total_questions = responses.count()

        if session.total_questions > 0:
            session.average_score = (
                sum(r.total_score for r in responses) / session.total_questions
            )
            session.avg_answer_length = (
                sum(r.answer_length for r in responses) / session.total_questions
            )
            session.avg_time_taken = (
                sum(r.time_taken_seconds for r in responses) / session.total_questions
            )

        session.save()

        # ----------------------------------------
        # BEHAVIOR ANALYSIS
        # ----------------------------------------
        analyze_session_behavior(session)

        # ----------------------------------------
        # MARK COMPLETE (5 Q rule)
        # ----------------------------------------
        if session.total_questions >= 5:
            session.completed = True
            session.save()

        # ----------------------------------------
        # ADAPTIVE DIFFICULTY UPDATE
        # ----------------------------------------
        update_adaptive_difficulty(request.user)

        # ----------------------------------------
        # UPDATE SKILL PROFILE
        # ----------------------------------------
        profile, _ = SkillProfile.objects.get_or_create(user=request.user)

        profile.communication_score = communication_score * 10
        profile.confidence_score = confidence_score * 10
        profile.save()

        recompute_skill_profile(request.user)

        # ----------------------------------------
        # USAGE TRACKING
        # ----------------------------------------
        UsageLog.objects.create(
            user=request.user,
            action="interview"
        )

        # ----------------------------------------
        # FEEDBACK
        # ----------------------------------------
        if total_score >= 8:
            feedback = "Excellent answer. Strong fundamentals."
        elif total_score >= 6:
            feedback = "Good answer. Add more structured explanation."
        else:
            feedback = "Basic understanding. Revise core concepts."

        # ----------------------------------------
        # RESPONSE
        # ----------------------------------------
        return JsonResponse({
            "technical_score": technical_score,
            "clarity_score": clarity_score,
            "communication_score": communication_score,
            "confidence_score": confidence_score,
            "total_score": total_score,
            "feedback": feedback
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ======================================================
# WEEKLY STATUS API
# ======================================================
def weekly_status(request):

    if not request.user.is_authenticated:
        return JsonResponse({"error": "Login required"}, status=403)

    today = timezone.now().date()
    week_start = today - timezone.timedelta(days=today.weekday())

    session = InterviewSession.objects.filter(
        user=request.user,
        week_start=week_start
    ).first()

    if not session:
        return JsonResponse({"status": "not_started"})

    if session.completed:
        return JsonResponse({"status": "completed"})

    return JsonResponse({
        "status": "in_progress",
        "questions_answered": session.total_questions
    })
