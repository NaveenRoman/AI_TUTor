from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail

from rest_framework.response import Response
from rest_framework.decorators import api_view

from core.models import (
    UserChapterProgress,
    Chapter,
    TopicQuiz
)

print("🚀 api_views.py LOADED")


@api_view(["POST"])
@login_required
def topic_complete_api(request):
    print("🔥 topic_complete_api CALLED")

    user = request.user
    subject = request.data.get("subject")
    topic_slug = request.data.get("topic")

    print("📌 Subject:", subject)
    print("📌 Topic Slug:", topic_slug)

    if not subject or not topic_slug:
        print("❌ Missing subject or topic_slug")
        return Response({"success": False, "error": "Invalid data"}, status=400)

    # Extract number from slug (example: java-topic1 → 1)
    import re
    match = re.search(r"(\d+)$", topic_slug)
    if not match:
        print("❌ Could not extract topic number")
        return Response({"success": False, "error": "Invalid topic"}, status=400)

    order = int(match.group(1))
    print("📌 Extracted order:", order)

    # Get chapter
    chapter = get_object_or_404(
        Chapter,
        book__slug=subject,
        order=order
    )

    print("✅ Chapter Found:", chapter.title)

    # 1️⃣ Mark topic complete
    UserChapterProgress.objects.update_or_create(
        user=user,
        chapter=chapter,
        defaults={"completed": True}
    )

    print("✅ Topic marked completed")

    # 2️⃣ Create quiz
    quiz, created = TopicQuiz.objects.get_or_create(
        user=user,
        topic=chapter
    )

    print("✅ Quiz object ID:", quiz.id, "| Created:", created)

    # 3️⃣ Build quiz URL
    quiz_url = request.build_absolute_uri(
        reverse("topic_quiz", args=[quiz.id])
    )

    print("🔗 Quiz URL:", quiz_url)

    # 4️⃣ Send Email (Console Debug Mode)
    if user.email:
        print("📧 Sending email to:", user.email)

        send_mail(
            subject="🎯 Topic Completed – Quiz Unlocked",
            message=f"""
Hi {user.username},

You completed: {chapter.title}

Your quiz is ready:
{quiz_url}

Complete it to improve your streak 🔥
""",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )

        print("✅ EMAIL FUNCTION FINISHED")
    else:
        print("❌ User has no email")

    return Response({"success": True})

