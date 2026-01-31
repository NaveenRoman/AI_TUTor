import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from core.models import Chapter, UserChapterProgress
from core.utils_progress import recompute_book_progress_for_user


# ======================================================
# MARK CHAPTER COMPLETE
# ======================================================
@csrf_exempt
@require_POST
@login_required
def mark_chapter_complete(request):
    """
    Marks a chapter as completed for the logged-in user
    and recomputes overall book progress.
    """
    try:
        data = json.loads(request.body or "{}")
        chapter_id = data.get("chapter_id")

        if not chapter_id:
            return JsonResponse(
                {"error": "chapter_id required"},
                status=400
            )

        try:
            chapter = Chapter.objects.get(pk=chapter_id)
        except Chapter.DoesNotExist:
            return JsonResponse(
                {"error": "Chapter not found"},
                status=404
            )

        # Create or update chapter progress
        progress, _ = UserChapterProgress.objects.get_or_create(
            user=request.user,
            chapter=chapter
        )

        progress.completed = True
        progress.completed_at = timezone.now()
        progress.save()

        # Update aggregate book progress
        recompute_book_progress_for_user(
            request.user,
            chapter.book
        )

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )
