from django.contrib import admin
from .models import (
    Book,
    Chapter,
    UserProfile,
    BookProgress,
    UserChapterProgress,
    SkillProfile,
    Institution,
    InstitutionMembership,
    BillingRecord,
    InterviewSession,
    InterviewResponse,
    PlatformAdmin,
)

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string








# ===============================
# BOOK SYSTEM
# ===============================

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


@admin.register(BookProgress)
class BookProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "book", "percent_complete", "last_updated")
    list_filter = ("book",)


@admin.register(UserChapterProgress)
class UserChapterProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "chapter", "completed", "completed_at")
    list_filter = ("completed", "chapter__book")


@admin.register(SkillProfile)
class SkillProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "readiness_score", "risk_level")


# ===============================
# MULTI COLLEGE SAAS
# ===============================



@admin.register(InstitutionMembership)
class InstitutionMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "institution", "role", "branch", "batch")
    list_filter = ("role", "branch", "batch", "institution")
    search_fields = ("user__username",)


@admin.register(BillingRecord)
class BillingRecordAdmin(admin.ModelAdmin):
    list_display = ("institution", "amount", "plan", "status", "paid_on")
    list_filter = ("status", "plan")


# ===============================
# INTERVIEW SYSTEM
# ===============================

@admin.register(InterviewSession)
class InterviewSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "week_start",
        "difficulty",
        "average_score",
        "performance_slope",
        "risk_flag",
        "completed",
    )
    list_filter = ("difficulty", "completed", "risk_flag")


@admin.register(InterviewResponse)
class InterviewResponseAdmin(admin.ModelAdmin):
    list_display = ("session", "total_score", "confidence_score", "created_at")
    list_filter = ("created_at",)


# ===============================
# PLATFORM ADMIN
# ===============================

@admin.register(PlatformAdmin)
class PlatformAdminAdmin(admin.ModelAdmin):
    list_display = ("user", "is_super_admin")







@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "admin_email", "plan", "is_active")
    search_fields = ("name", "code", "admin_email")
    list_filter = ("plan", "is_active")

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        # Only create admin user for NEW institution
        if is_new and obj.admin_email:

            base_username = obj.admin_email.split("@")[0]
            username = base_username
            counter = 1

            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            password = "".join(
                secrets.choice(string.ascii_letters + string.digits)
                for _ in range(10)
            )

            user = User.objects.create_user(
                username=username,
                email=obj.admin_email,
                password=password
            )
            user.is_staff = True
            user.save()

            InstitutionMembership.objects.create(
                user=user,
                institution=obj,
                role="college_admin"
            )

            login_url = "http://127.0.0.1:8000/accounts/login/"
            dashboard_url = "http://127.0.0.1:8000/college/dashboard/"

            send_mail(
                subject="College Admin Access",
                message=f"""
Hello,

Your college "{obj.name}" has been registered.

Login URL:
{login_url}

Username: {username}
Password: {password}

After login you will be redirected to:
{dashboard_url}

Please change your password after login.

— AI Tutor Platform
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[obj.admin_email],
                fail_silently=False,
            )
