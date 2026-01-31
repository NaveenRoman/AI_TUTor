# core/utils_progress.py
from .models import BookProgress, UserChapterProgress, Chapter
from django.db import transaction

def recompute_book_progress_for_user(user, book):
    total = Chapter.objects.filter(book=book).count()
    completed = UserChapterProgress.objects.filter(user=user, chapter__book=book, completed=True).count()
    percent = (completed / total * 100) if total else 0.0
    obj, created = BookProgress.objects.get_or_create(user=user, book=book, defaults={
        "completed_chapters": completed, "total_chapters": total, "percent_complete": percent
    })
    if not created:
        obj.completed_chapters = completed
        obj.total_chapters = total
        obj.percent_complete = percent
        obj.save()
