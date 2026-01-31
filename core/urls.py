from django.urls import path
from core import views

# ===============================
# DASHBOARD
# ===============================
from core.views.views_dashboard import dashboard

# ===============================
# INTERVIEW
# ===============================
from core.views.views_interview import hr_interviewer
from core.views.views_pages import interview_page

# ===============================
# PROFILE
# ===============================
from core.views.views_profile import (
    profile_page,
    profile_edit,
    profile_api,
    profile_analytics_api,
)

# ===============================
# BOOKS / LEARNING
# ===============================
from core.views.views_books import (
    book_topics_page,
    book_topic_page,
    ask_book_topic,
    topic_complete_api,
    book_progress_api,
)

# ===============================
# CHAT / AI
# ===============================
from core.views.views_chat import (
    chat,
    ask,
    upload,
    voice_control,
)

# ===============================
# QUIZ
# ===============================
from core.views.views_quiz import (
    topic_quiz_page,          # ✅ PAGE VIEW (IMPORTANT)
    get_quiz,                 # API
    start_quiz,
    submit_quiz,
    proctor_log,
    generate_daily_quiz,
    get_daily_quiz,
    submit_daily_quiz,
)

urlpatterns = [

    # =====================================================
    # STATIC / LANDING PAGES
    # =====================================================
    path("", views.index_page, name="index"),
    path("categories/", views.categories_page, name="categories"),
    path("ai-tutor/", views.ai_tutor_page, name="ai_tutor"),
    path("contact/", views.contact_page, name="contact"),

    # =====================================================
    # DASHBOARD
    # =====================================================
    path("dashboard/", dashboard, name="dashboard"),

    # =====================================================
    # INTERVIEW
    # =====================================================
    path("interview/", interview_page, name="interview"),
    path("api/interview/hr/", hr_interviewer, name="hr_interviewer"),

    # =====================================================
    # PROFILE
    # =====================================================
    path("profile/", profile_page, name="my_profile"),
    path("profile/<str:username>/", profile_page, name="user_profile"),
    path("profile/edit/", profile_edit, name="profile_edit"),
    path("api/profile/", profile_api),
    path("api/profile/analytics/", profile_analytics_api),

    # =====================================================
    # BOOKS / LEARNING FLOW
    # =====================================================
    path("books/", book_topics_page, name="books"),

    path(
        "topic/<str:subject>/<str:page>/",
        book_topic_page,
        name="book_topic"
    ),

    path(
        "api/topic-complete/",
        topic_complete_api,
        name="topic_complete"
    ),

    path(
        "api/book-progress/",
        book_progress_api,
        name="book_progress_api"
    ),

    path("api/ask-book-topic/", ask_book_topic),

    # =====================================================
    # CHAT / AI
    # =====================================================
    path("chat/", chat, name="chat"),
    path("api/chat/", chat),
    path("api/ask/", ask),
    path("api/upload/", upload),
    path("api/voice/", voice_control),

    # =====================================================
    # QUIZ (🔥 CORRECT & WORKING)
    # =====================================================

    # ✅ QUIZ PAGE (EMAIL LINK OPENS THIS)
    path(
        "quiz/topic/<int:quiz_id>/",
        topic_quiz_page,
        name="topic_quiz"
    ),

    # ✅ QUIZ APIs
    path("api/get-quiz/", get_quiz),
    path("api/start-quiz/", start_quiz),
    path("api/submit-quiz/", submit_quiz),
    path("api/proctor-log/", proctor_log),

    # ✅ DAILY QUIZ
    path("api/generate-daily-quiz/", generate_daily_quiz),
    path("api/get-daily-quiz/", get_daily_quiz),
    path("api/submit-daily-quiz/", submit_daily_quiz),
]

