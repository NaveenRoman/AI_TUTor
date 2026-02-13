from datetime import timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.utils import timezone
from django.db.models import Avg
from core.models import UserChapterProgress, Chapter
from core.models import DailyQuizAttempt
from core.models import UsageLog


from core.models import ReadinessHistory

from core.models import InstitutionMembership
from django.http import HttpResponseForbidden




from core.models import SkillProfile


from core.models import (
    QuizAttempt,
    TopicStat,
    WeeklyQuiz,
    BookProgress,
)


from django.shortcuts import render
from django.contrib.auth.decorators import login_required





# ============================
# HELPER: DAILY STREAK COUNT
# ============================
def get_daily_streak(user):
    today = timezone.now().date()
    streak = 0

    for i in range(0, 365):  # allow long streaks
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





# ============================
# HELPER: STREAK BAR CHART DATA (LAST 7 DAYS)
# ============================
def get_streak_data(user):
    today = timezone.now().date()
    data = []

    for i in range(6, -1, -1):
        day = today - timedelta(days=i)

        attempted = DailyQuizAttempt.objects.filter(
            user=user,
            date=day
        ).exists()

        data.append({
            "date": str(day),
            "attempted": 1 if attempted else 0
        })

    return data



# ============================
# DASHBOARD VIEW
# ============================
@login_required
def dashboard(request):

    # 🔒 BLOCK COLLEGE ADMINS FROM STUDENT DASHBOARD
    if InstitutionMembership.objects.filter(
        user=request.user,
        role="college_admin"
    ).exists():
        return HttpResponseForbidden("College admins cannot access student dashboard")

    user = request.user  # ✅ REQUIRED
  # ✅ REQUIRED

    
    from core.models import InterviewSession
    
    latest_session = (
    InterviewSession.objects
    .filter(user=user)
    .order_by("-created_at")
    .first()
)



    today_date = timezone.now().date()
    daily_active_users = UsageLog.objects.filter(
    created_at__date=today_date
    ).values("user").distinct().count()


    total_interviews = UsageLog.objects.filter(
    user=user,
    action="interview"
    ).count()


    avg_improvement = (
    TopicStat.objects
    .aggregate(avg=Avg("improvement_rate"))["avg"] or 0
)




    # -----------------------------
    # Average quiz score
    # -----------------------------
    avg_score = (
        QuizAttempt.objects
        .filter(user=user, score__isnull=False)
        .aggregate(avg=Avg("score"))["avg"] or 0
    )

    # -----------------------------
    # Percentile
    # -----------------------------
    all_users_avg = (
        QuizAttempt.objects
        .values("user")
        .annotate(avg=Avg("score"))
    )

    below = sum(1 for u in all_users_avg if u["avg"] and u["avg"] < avg_score)
    percentile = int((below / max(len(all_users_avg), 1)) * 100)

    # -----------------------------
    # 📘 COURSE PROGRESS (FIXED)
    # -----------------------------
    completed_chapters = UserChapterProgress.objects.filter(
        user=user,
        completed=True
    )

    completed_count = completed_chapters.count()

    books_started = (
        completed_chapters
        .values("chapter__book")
        .distinct()
        .count()
    )

    total_chapters = Chapter.objects.count()
    overall_course_percent = (
        int((completed_count / total_chapters) * 100)
        if total_chapters else 0
    )

    # -----------------------------
    # Strong & weak topics
    # -----------------------------
    strong_topics = TopicStat.objects.filter(
        user=user, mastery_score__gte=70
    ).order_by("-mastery_score")[:5]

    weak_topics = TopicStat.objects.filter(
        user=user, mastery_score__lt=40
    ).order_by("mastery_score")[:5]

    # -----------------------------
    # Weekly quiz performance
    # -----------------------------
    weekly_data = WeeklyQuiz.objects.filter(user=user).order_by("week_start")
    weekly_labels = [
        w.week_start.strftime("%b %d")
        for w in weekly_data
        ]
    weekly_scores = [
    w.score if w.score is not None else 0
    for w in weekly_data
]



    # -----------------------------
# Study plan
# -----------------------------
    # -----------------------------
# Study plan
# -----------------------------
 # -----------------------------
# Study plan
# -----------------------------
    study_plan = []

# 1️⃣ Priority: Weak topics
    if weak_topics.exists():
        for t in weak_topics[:2]:
            study_plan.append(f"Revise {t.topic} (Mastery: {int(t.mastery_score)}%)"
                              )

# 2️⃣ Next incomplete lesson
    else:
        next_chapter = Chapter.objects.exclude(id__in=UserChapterProgress.objects.filter(user=user,completed=True).values_list("chapter_id", flat=True)
                                               ).order_by("order").first()


        if next_chapter:study_plan.append(f"Next Lesson: {next_chapter.title}")
        else:study_plan.append("You're ahead! Try weekly challenge.")





     # -----------------------------
# Today's Quiz Score
# -----------------------------
    today_attempt = QuizAttempt.objects.filter(
        user=user,
        submitted_at__date=timezone.now().date()
    ).order_by("-submitted_at").first()

    today_score = today_attempt.score if today_attempt else 0

    # -----------------------------
    # Daily streak
    # -----------------------------
    streak = get_daily_streak(user)
    streak_data = get_streak_data(user)
    streak_labels = [d["date"][-5:] for d in streak_data]
    streak_values = [d["attempted"] for d in streak_data]


    skill_profile, _ = SkillProfile.objects.get_or_create(user=user)



    # -----------------------------
# Weekly Growth Engine
# -----------------------------
    today = timezone.now()

    last_7 = ReadinessHistory.objects.filter(
    user=user,
    recorded_at__gte=today - timedelta(days=7)
)

    prev_7 = ReadinessHistory.objects.filter(
    user=user,
    recorded_at__gte=today - timedelta(days=14),
    recorded_at__lt=today - timedelta(days=7)
)

    last_avg = last_7.aggregate(avg=Avg("readiness_score"))["avg"] or 0
    prev_avg = prev_7.aggregate(avg=Avg("readiness_score"))["avg"] or 0

    if prev_avg > 0:
        weekly_growth = ((last_avg - prev_avg) / prev_avg) * 100
    else:
        weekly_growth = 0



    



 

    # -----------------------------
    # FINAL RENDER
    # -----------------------------
    return render(request, "core/dashboard.html", {
        "avg_score": round(avg_score, 2),
        "percentile": percentile,
        "completed_count": completed_count,
        "books_started": books_started,
        "overall_course_percent": overall_course_percent,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "weekly_labels": weekly_labels,
        "weekly_scores": weekly_scores,
        "streak": streak,
        "streak_labels": streak_labels,
        "streak_values": streak_values,
        "study_plan": study_plan,
        "today_score": today_score,
        "skill_profile": skill_profile,
        "total_interviews": total_interviews,
        "daily_active_users": daily_active_users,
        "avg_improvement": round(avg_improvement, 2),
        "latest_session": latest_session,


        "skill": {
            "technical_score": skill_profile.technical_score,
            "communication_score": skill_profile.communication_score,
            "confidence_score": skill_profile.confidence_score,
            "accuracy_score": skill_profile.accuracy_score,
            "consistency_score": skill_profile.consistency_score,
            "weekly_growth": round(weekly_growth, 2),

}





    })



from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from core.utils_prediction_engine import calculate_placement_prediction


@login_required
def student_prediction(request):

    prediction = calculate_placement_prediction(request.user)

    if not prediction:
        return JsonResponse({"error": "No profile data"}, status=404)

    return JsonResponse(prediction)



