import os
import json
import traceback
import nltk
import re

from django.db.models import Max
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse, Http404

from django.views.decorators.csrf import csrf_exempt

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.decorators import login_required

from core.models import (
    Book,
    Chapter,
    UserChapterProgress,
    QuizChapter
)

from core.books_loader import BOOK_KB
from core.utils import extract_text
from core.utils_format import format_answer_core

from core.views.views_chat import (
    detect_template_type,
    choose_language,
    VOICE_STATE,
)

from core.views.views_quiz import auto_generate_chapter_quiz



# ======================================================
# BOOKS PAGE (HTML)
# ======================================================
def book_topics_page(request):
    subject = request.GET.get("subject")

    # ✅ Subject-specific page (java, python, etc.)
    if subject:
        subject = subject.lower()
        return render(request, f"books/{subject}.html")

    # ✅ Fallback (if no subject provided)
    books = {
        subject: {
            "topics": list(info["sections"].keys()),
            "count": len(info["sections"]),
        }
        for subject, info in BOOK_KB.items()
    }
    return render(request, "books/topics.html", {"books": books})




# ======================================================
# BOOK TOPIC PAGE (HTML)
# ======================================================
def book_topic_page(request, subject, page):
    subject = subject.lower()
    template_path = f"books/{subject}/{page}.html"
    try:
        return render(request, template_path)
    except Exception:
        raise Http404("Topic not found")


# ======================================================
# ASK QUESTION FROM SPECIFIC TOPIC (API)
# ======================================================
@csrf_exempt
def ask_book_topic(request):
    try:
        data = json.loads(request.body or "{}")

        subject = data.get("subject")
        topic = data.get("topic") or data.get("page")
        question = data.get("question", "").strip()
        full = bool(data.get("full", False))

        if not subject or not topic:
            return JsonResponse({"error": "subject and topic required"}, status=400)

        subject = subject.lower()

        if subject not in BOOK_KB:
            return JsonResponse({"error": "Subject not found"}, status=404)

        folder = BOOK_KB[subject]["folder"]
        topic_path = os.path.join(folder, topic)

        if not os.path.isfile(topic_path):
            return JsonResponse({"error": "Topic not found"}, status=404)

        text = extract_text(topic_path)
        sentences = nltk.sent_tokenize(text)

        # simple keyword-based fallback (no embeddings)
        best_text = ""
        for s in sentences:
            if question.lower() in s.lower():
                best_text += s + " "
        if not best_text:
            best_text = " ".join(sentences[:5])


        mode = detect_template_type(question, data)
        language = choose_language(data, question)
        if full:
            mode = "full_topic"

        answer = format_answer_core(
            question=question,
            content=best_text,
            detail_level="long" if full else "auto",
            history=None,
            template_type=mode,
            language=language,
        )

        return JsonResponse({
            "answer": answer,
            "subject": subject,
            "topic": topic,
            "mode": mode,
            "voice": {"autoplay": VOICE_STATE.get("autoplay", False)},
        })

    except Exception as e:
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

# ======================================================
# MARK TOPIC COMPLETED (API)
# ======================================================
@api_view(["POST"])
@login_required
def topic_complete_api(request):

    print("🔥 topic_complete_api called")

    user = request.user
    subject = request.data.get("subject")
    topic_slug = request.data.get("topic")

    if not subject or not topic_slug:
        return Response(
            {"success": False, "error": "Invalid data"},
            status=400
        )

    # Extract topic number (java-topic1 → 1)
    match = re.search(r"(\d+)$", topic_slug)
    if not match:
        return Response(
            {"success": False, "error": "Invalid topic format"},
            status=400
        )

    order = int(match.group(1))

    # Get chapter from DB
    chapter = get_object_or_404(
        Chapter,
        book__slug=subject,
        order=order
    )

    # 1️⃣ Mark chapter as completed
    UserChapterProgress.objects.update_or_create(
        user=user,
        chapter=chapter,
        defaults={"completed": True}
    )

    # 2️⃣ 🔥 Generate quiz properly
    quiz_obj = auto_generate_chapter_quiz(subject, topic_slug)

    if not quiz_obj:
        quiz_obj = QuizChapter.objects.filter(
            subject=subject,
            chapter=topic_slug
        ).order_by("-created_at").first()

    if not quiz_obj:
        return Response(
            {"success": False, "error": "Quiz generation failed"},
            status=500
        )

    # 3️⃣ Build quiz URL
    quiz_url = request.build_absolute_uri(
        reverse("topic_quiz", args=[quiz_obj.id])
    )

    # 4️⃣ Send email
   # if user.email:
     #   send_mail(
     #       subject="🎯 You unlocked a new quiz!",
     #       message=f"""
#Hi {user.username},

#Great job completing "{chapter.title}" 🎉

#You have a new quiz waiting:
#👉 {quiz_url}

#Complete it to continue your streak 🔥
#""",
  #          from_email=settings.DEFAULT_FROM_EMAIL,
   #         recipient_list=[user.email],
    #        fail_silently=True
     #   )
#
    print("✅ topic_complete_api finished successfully")

    return Response({
        "success": True,
        "quiz_id": quiz_obj.id
    })






# ======================================================
# BOOK PROGRESS (API)
# ======================================================


def book_progress_api(request):
    subject = request.GET.get("subject")

    try:
        book = Book.objects.get(slug=subject)
    except Book.DoesNotExist:
        return JsonResponse({
            "completed_chapters": 0,
            "total_chapters": 0,
            "percent_complete": 0,
            "chapters": []
        })

    chapters = list(
        Chapter.objects.filter(book=book)
        .order_by("order")
        .values("order", "title")
    )

    total = len(chapters)

    if request.user.is_authenticated:
        completed = (
            UserChapterProgress.objects.filter(
                user=request.user,
                chapter__book=book,
                completed=True
            )
            .aggregate(max_order=Max("chapter__order"))
            .get("max_order") or 0
        )
    else:
        completed = 0

    percent = int((completed / total) * 100) if total else 0

    return JsonResponse({
        "completed_chapters": completed,
        "total_chapters": total,
        "percent_complete": percent,
        "chapters": chapters
    })

