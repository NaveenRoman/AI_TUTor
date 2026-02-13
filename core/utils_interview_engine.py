from django.utils import timezone
from django.db.models import Avg

from core.models import InterviewSession, SkillProfile


# ======================================================
# WEEK CALCULATION
# ======================================================
def get_week_start():
    today = timezone.now().date()
    return today - timezone.timedelta(days=today.weekday())


# ======================================================
# CREATE / FETCH WEEKLY SESSION (WITH HARD LOCK)
# ======================================================
def get_or_create_weekly_session(user):

    week_start = get_week_start()

    session = InterviewSession.objects.filter(
        user=user,
        week_start=week_start
    ).first()

    # 🔒 HARD LOCK — Already Completed
    if session and session.completed:
        raise Exception("Weekly interview already completed.")

    # Create new session if not exists
    if not session:
        difficulty = get_user_next_difficulty(user)

        session = InterviewSession.objects.create(
            user=user,
            week_start=week_start,
            difficulty=difficulty
        )

    return session


# ======================================================
# GET NEXT DIFFICULTY FROM PROFILE
# ======================================================
def get_user_next_difficulty(user):
    profile, _ = SkillProfile.objects.get_or_create(user=user)

    # Safety fallback
    if not hasattr(profile, "next_difficulty"):
        return "medium"

    return profile.next_difficulty


# ======================================================
# ADAPTIVE DIFFICULTY ENGINE
# ======================================================
def update_adaptive_difficulty(user):

    recent_sessions = (
        InterviewSession.objects
        .filter(user=user, completed=True)
        .order_by("-created_at")[:3]
    )

    if recent_sessions.count() == 0:
        return

    avg_score = (
        recent_sessions.aggregate(avg=Avg("average_score"))["avg"] or 0
    )

    profile, _ = SkillProfile.objects.get_or_create(user=user)

    if avg_score >= 75:
        profile.next_difficulty = "hard"
    elif avg_score <= 40:
        profile.next_difficulty = "easy"
    else:
        profile.next_difficulty = "medium"

    profile.save()

