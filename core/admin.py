from django.contrib import admin
from .models import Book, Chapter, UserProfile, BookProgress, UserChapterProgress

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "created_at")
    prepopulated_fields = {"slug": ("title",)}

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ("title", "book", "order")
    list_filter = ("book",)
    ordering = ("book", "order")

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "level", "xp", "streak")  
    # Removed timezone, weekly_quiz_enabled, updated_at (not in model)

@admin.register(BookProgress)
class BookProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "percent_complete", "last_updated")
    list_filter = ("book",)

@admin.register(UserChapterProgress)
class UserChapterProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "chapter", "completed", "completed_at")
    list_filter = ("completed", "chapter__book")
