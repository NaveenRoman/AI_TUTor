from datetime import timedelta
import json

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.utils import timezone

from core.models import (
    QuizAttempt,
    TopicStat,
    WeeklyQuiz,
    UserChapterProgress,
    Chapter,
    DailyQuizAttempt,
)


# ==========================================
# HELPER — DAILY STREAK COUNT
# ==========================================
def get_daily_streak(user):
    today = timezone.now().date()
    streak = 0

    for i in range(0, 30):
        day = today - timedelta(days=i)

        attempted = DailyQuizAttempt.objects.filter(
            user=user,
            date=day
        ).exists()

        if attempted:
            streak += 1
        else:
            break

    return streak


# ==========================================
# HELPER — STREAK CHART DATA (LAST 7 DAYS)
# ==========================================
def get_streak_data(user):
    today = timezone.now().date()
    labels = []
    values = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)

        attempted = DailyQuizAttempt.objects.filter(
            user=user,
            date=day
        ).exists()

        labels.append(day.strftime("%d %b"))
        values.append(1 if attempted else 0)

    return labels, values


# ==========================================
# MAIN DASHBOARD VIEW
# ==========================================
@login_required
def dashboard(request):
    user = request.user

    # --------------------------------------
    # 1️⃣ Average Quiz Score
    # --------------------------------------
    attempts = QuizAttempt.objects.filter(
        user=user,
        score__isnull=False
    )

    avg_score = attempts.aggregate(avg=Avg("score"))["avg"] or 0
    avg_score = round(avg_score, 2)

    # --------------------------------------
    # 2️⃣ Percentile (Comparison)
    # --------------------------------------
    all_users_avg = (
        QuizAttempt.objects
        .values("user")
        .annotate(avg=Avg("score"))
    )

    below = sum(
        1 for u in all_users_avg
        if u["avg"] is not None and u["avg"] < avg_score
    )

    total_users = len(all_users_avg) if all_users_avg else 1
    percentile = int((below / total_users) * 100)

    # --------------------------------------
    # 3️⃣ Course Progress
    # --------------------------------------
    completed = UserChapterProgress.objects.filter(
        user=user,
        completed=True
    )

    completed_count = completed.count()

    books_started = (
        completed
        .values("chapter__book")
        .distinct()
        .count()
    )

    total_chapters = Chapter.objects.count()
    overall_course_percent = (
        int((completed_count / total_chapters) * 100)
        if total_chapters else 0
    )

    # --------------------------------------
    # 4️⃣ Strong / Weak Topics
    # --------------------------------------
    strong_topics = TopicStat.objects.filter(
        user=user,
        mastery_score__gte=70
    ).order_by("-mastery_score")[:5]

    weak_topics = TopicStat.objects.filter(
        user=user,
        mastery_score__lt=40
    ).order_by("mastery_score")[:5]

    # --------------------------------------
    # 5️⃣ Weekly Performance Chart
    # --------------------------------------
    weekly = (
        WeeklyQuiz.objects
        .filter(user=user)
        .order_by("week_start")
        .values("week_start", "score")
    )

    weekly_labels = [
        w["week_start"].strftime("%d %b")
        for w in weekly
    ]

    weekly_scores = [
        round(w["score"] or 0, 1)
        for w in weekly
    ]

    # --------------------------------------
    # 6️⃣ Daily Streak
    # --------------------------------------
    streak = get_daily_streak(user)
    streak_labels, streak_values = get_streak_data(user)

    # --------------------------------------
    # 7️⃣ Tomorrow Study Plan (Smart Logic)
    # --------------------------------------
    if avg_score < 40:
        tomorrow_plan = [
            "Revise weak fundamentals",
            "Retake previous quiz",
            "Solve 15 MCQs"
        ]
    elif avg_score < 70:
        tomorrow_plan = [
            "Practice moderate questions",
            "Review mistakes",
            "Attempt one mock test"
        ]
    else:
        tomorrow_plan = [
            "Attempt advanced problems",
            "Focus on weak micro-topics",
            "Solve interview-level questions"
        ]

    # --------------------------------------
    # FINAL CONTEXT
    # --------------------------------------
    context = {
        "avg_score": avg_score,
        "percentile": percentile,
        "completed_count": completed_count,
        "books_started": books_started,
        "overall_course_percent": overall_course_percent,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "streak": streak,
        "study_plan": tomorrow_plan,

        # Chart Data (JSON safe)
        "weekly_labels": json.dumps(weekly_labels),
        "weekly_scores": json.dumps(weekly_scores),
        "streak_labels": json.dumps(streak_labels),
        "streak_values": json.dumps(streak_values),
    }

    return render(request, "core/dashboard.html", context)
