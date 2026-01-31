from core.views.views_quiz import auto_generate_chapter_quiz



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from django.contrib.auth import get_user_model
from django.db.models import Avg, Sum

from core.models import (
    UserProfile,
    BookProgress,
    UserChapterProgress,
    Chapter,
    QuizAttempt,
    TopicStat,
)


# ======================================================
# PROFILE PAGE (HTML)
# ======================================================

@login_required
def profile_page(request):
    return render(request, "core/profile.html")


    if username:
        user_obj = get_object_or_404(User, username=username)
    else:
        user_obj = request.user

    profile = getattr(user_obj, "profile", None)

    progress_qs = (
        BookProgress.objects
        .filter(user=user_obj)
        .select_related("book")
    )

    progress_list = [
        {
            "book_title": p.book.title,
            "book_slug": p.book.slug,
            "completed_chapters": p.completed_chapters,
            "total_chapters": p.total_chapters,
            "percent_complete": round(p.percent_complete, 2),
        }
        for p in progress_qs
    ]

    completed_chapters = (
        UserChapterProgress.objects
        .filter(user=user_obj, completed=True)
        .select_related("chapter__book")
        .order_by("-completed_at")[:10]
    )

    return render(request, "core/profile.html", {
        "profile_user": user_obj,
        "profile": profile,
        "progress_list": progress_list,
        "completed_chapters": completed_chapters,
    })


# ======================================================
# PROFILE EDIT
# ======================================================
@login_required
def profile_edit(request):
    profile = request.user.profile

    if request.method == "POST":
        profile.bio = request.POST.get("bio", profile.bio)
        profile.save()
        return redirect("my_profile")

    return render(request, "core/profile_edit.html", {"profile": profile})


# ======================================================
# PROFILE API (JSON)
# ======================================================
@login_required
def profile_api(request):
    user_obj = request.user
    profile = getattr(user_obj, "profile", None)

    progress = [
        {
            "book_title": p.book.title,
            "book_slug": p.book.slug,
            "completed_chapters": p.completed_chapters,
            "total_chapters": p.total_chapters,
            "percent_complete": round(p.percent_complete, 2),
        }
        for p in BookProgress.objects.filter(user=user_obj).select_related("book")
    ]

    recent_completed = list(
        UserChapterProgress.objects
        .filter(user=user_obj, completed=True)
        .select_related("chapter__book")
        .order_by("-completed_at")[:20]
        .values(
            "chapter__title",
            "chapter__book__title",
            "completed_at"
        )
    )

    return JsonResponse({
        "username": user_obj.username,
        "email": getattr(user_obj, "email", ""),
        "photo": (
            request.build_absolute_uri(profile.photo.url)
            if profile and profile.photo else None
        ),
        "bio": profile.bio if profile else "",
        "progress": progress,
        "recent_completed": recent_completed,
    })


# ======================================================
# 🔥 PROFILE ANALYTICS (NEW – STEP 1)
# ======================================================
@login_required
def profile_analytics_api(request):
    user = request.user

    attempts = QuizAttempt.objects.filter(user=user, score__isnull=False)

    total_quizzes = attempts.count()
    avg_score = attempts.aggregate(avg=Avg("score"))["avg"] or 0

    # Topic mastery
    strong_topics = (
        TopicStat.objects
        .filter(user=user, mastery_score__gte=70)
        .order_by("-mastery_score")
        .values_list("topic", flat=True)[:5]
    )

    weak_topics = (
        TopicStat.objects
        .filter(user=user, mastery_score__lt=40)
        .order_by("mastery_score")
        .values_list("topic", flat=True)[:5]
    )

    profile = getattr(user, "profile", None)

    return JsonResponse({
        "quiz_accuracy": round(avg_score, 2),
        "total_quizzes": total_quizzes,
        "strong_topics": list(strong_topics),
        "weak_topics": list(weak_topics),
        "streak": profile.streak if profile else 0,
        "level": profile.level if profile else 1,
        "xp": profile.xp if profile else 0,
    })


# ======================================================
# MARK CHAPTER COMPLETE
# ======================================================
@login_required
@require_POST
def mark_chapter_complete(request):
    chapter_id = request.POST.get("chapter_id")
    if not chapter_id:
        return JsonResponse({"error": "chapter_id required"}, status=400)

    chapter = get_object_or_404(Chapter, id=chapter_id)
    book = chapter.book   # ✅ NOW book exists

    progress, _ = UserChapterProgress.objects.get_or_create(
        user=request.user,
        chapter=chapter
    )

    if not progress.completed:
        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()

        # 🔥 AUTO GENERATE QUIZ (ONLY ON FIRST COMPLETION)
        auto_generate_chapter_quiz(
            subject=book.slug,   # "java"
            chapter=chapter.heading_id or chapter.title
        )

    total = book.chapters.count()
    completed = UserChapterProgress.objects.filter(
        user=request.user,
        chapter__book=book,
        completed=True
    ).count()

    percent = (completed / total) * 100 if total else 0

    BookProgress.objects.update_or_create(
        user=request.user,
        book=book,
        defaults={
            "completed_chapters": completed,
            "total_chapters": total,
            "percent_complete": percent
        }
    )

    return JsonResponse({
        "status": "ok",
        "book": book.title,
        "completed": completed,
        "total": total,
        "percent": round(percent, 2)
    })


@login_required
def study_plan_api(request):
    user = request.user

    weak_topics = list(
        TopicStat.objects
        .filter(user=user, mastery_score__lt=50)
        .order_by("mastery_score")
        .values_list("topic", flat=True)[:7]
    )

    unread = list(
        UserChapterProgress.objects
        .filter(user=user, completed=False)
        .select_related("chapter")
        .values_list("chapter__title", flat=True)[:7]
    )

    plan = []

    for day in range(7):
        plan.append({
            "day": f"Day {day+1}",
            "study": weak_topics[day] if day < len(weak_topics) else "Revision",
            "practice": unread[day] if day < len(unread) else "Weekly quiz"
        })

    return JsonResponse({
        "plan": plan
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Avg

from core.models import BookProgress, QuizAttempt


@login_required
def dashboard(request):
    user = request.user

    books_completed = BookProgress.objects.filter(
        user=user, percent_complete=100
    ).count()

    hours_studied = (
        QuizAttempt.objects.filter(user=user)
        .aggregate(total=Avg("duration"))["total"] or 0
    )

    avg_score = (
        QuizAttempt.objects.filter(user=user, score__isnull=False)
        .aggregate(avg=Avg("score"))["avg"] or 0
    )

    return render(
        request,
        "core/dashboard.html",
        {
            "books_completed": books_completed,
            "hours_studied": int(hours_studied),
            "avg_score": round(avg_score, 2),
        }
    )
