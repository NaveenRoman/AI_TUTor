# core/utils_skill_engine.py

from django.db.models import Avg
from django.utils import timezone
from statistics import pstdev

from .models import (
    TopicStat,
    QuizAttempt,
    SkillProfile,
)


# =========================================================
# MAIN FUNCTION — RECOMPUTE USER SKILL PROFILE
# =========================================================
def recompute_skill_profile(user):

    # ----------------------------
    # 1️⃣ TECHNICAL SCORE
    # ----------------------------
    technical = (
        TopicStat.objects
        .filter(user=user)
        .aggregate(avg=Avg("mastery_score"))["avg"] or 0
    )

    # ----------------------------
    # 2️⃣ ACCURACY SCORE
    # ----------------------------
    attempts = QuizAttempt.objects.filter(
        user=user,
        score__isnull=False
    )

    accuracy = (
        attempts.aggregate(avg=Avg("score"))["avg"] or 0
    ) if attempts.exists() else 0

    # ----------------------------
    # Fetch existing profile first
    # ----------------------------
    profile, _ = SkillProfile.objects.get_or_create(user=user)

    # ----------------------------
    # 3️⃣ COMMUNICATION SCORE
    # Use stored interview value
    # ----------------------------
    communication = profile.communication_score or 0

    # ----------------------------
    # 4️⃣ CONSISTENCY SCORE
    # ----------------------------
    last_five = list(
        attempts.order_by("-submitted_at")
        .values_list("score", flat=True)[:5]
    )

    if len(last_five) >= 2:
        deviation = pstdev(last_five)
        consistency = max(0, 100 - (deviation * 2))
    else:
        consistency = 0

    # ----------------------------
    # 5️⃣ CONFIDENCE SCORE
    # ----------------------------
    confidence = profile.confidence_score or min(100, accuracy + 10)

    # ----------------------------
    # 6️⃣ READINESS SCORE
    # ----------------------------
    readiness = (
        technical * 0.5 +
        communication * 0.2 +
        consistency * 0.2 +
        confidence * 0.1
    )

    # ----------------------------
    # STORE
    # ----------------------------
    profile.technical_score = round(technical, 2)
    profile.accuracy_score = round(accuracy, 2)
    profile.communication_score = round(communication, 2)
    profile.consistency_score = round(consistency, 2)
    profile.confidence_score = round(confidence, 2)
    profile.readiness_score = round(readiness, 2)

    profile.last_updated = timezone.now()
    profile.save()



    from core.models import ReadinessHistory

# Only create one entry per day
    today = timezone.now().date()

    already_logged = ReadinessHistory.objects.filter(
    user=user,
    recorded_at__date=today).exists()

    if not already_logged:
        ReadinessHistory.objects.create(
        user=user,
        readiness_score=profile.readiness_score
    )



    return profile

