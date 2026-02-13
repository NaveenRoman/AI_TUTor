from django.urls import path
from core import views



# ===============================
# DASHBOARD
# ===============================
from core.views.views_dashboard import dashboard
from core.views.views_admin import admin_dashboard
from core.views.views_admin import admin_dashboard, export_placement_report
from core.views.views_super_admin import super_admin_dashboard
from core.views.views_company import company_dashboard, student_profile_view
from core.views.views_hiring import company_filter_students
from core.views.views_auth import signup


from core.views.views_admin import generate_invite_link
from core.views.views_auth import college_join_signup

from core.views.views_public import public_student_profile




# ===============================
# INTERVIEW
# ===============================

from core.views.views_interview import hr_interviewer, weekly_status

from core.views.views_dashboard import student_prediction
 
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
# BOOKS / LEARNING  ✅ FIXED
# ===============================
from core.views.views_books import (
    book_topics_page,
    book_topic_page,   # ✅ IMPORTANT ADD THIS
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
    get_quiz,
    start_quiz,
    submit_quiz,
    proctor_log,
    generate_daily_quiz,
    get_daily_quiz,
    submit_daily_quiz,
    topic_quiz_page,   # ✅ ADD THIS HERE
)


urlpatterns = [


    # =========================
    # SIGNUP
    # =========================
    path("signup/", signup, name="signup"),



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

    path("college/dashboard/", admin_dashboard, name="admin_dashboard"),
    path("college/export-report/", export_placement_report, name="export_report"),
    path("platform/dashboard/", super_admin_dashboard, name="super_admin_dashboard"),

    path("company/dashboard/", company_dashboard, name="company_dashboard"),
    path("company/student/<str:username>/", student_profile_view),
    path("hire/<str:username>/", public_student_profile),



    path("api/company/filter/", company_filter_students),



    

    





    # =====================================================
    # INTERVIEW
    # =====================================================
    path("interview/", interview_page, name="interview"),
    path("api/interview/hr/", hr_interviewer, name="hr_interviewer"),
    path("api/interview/weekly-status/", weekly_status),
    path("api/student/prediction/", student_prediction),

    # =====================================================
    # PROFILE
    # =====================================================
    path("profile/", profile_page, name="my_profile"),
    path("profile/<str:username>/", profile_page, name="user_profile"),
    path("profile/edit/", profile_edit, name="profile_edit"),

    path("api/profile/", profile_api),
    path("api/profile/analytics/", profile_analytics_api),

    path("college/generate-invite/", generate_invite_link, name="generate_invite"),
    path("college/join/<str:token>/", college_join_signup, name="college_join"),

    # =====================================================
    # BOOKS / LEARNING FLOW  ✅ FIXED
    # =====================================================
    path("books/", book_topics_page, name="books"),

    # 🔥 FIXED HERE (NO MORE views.book_topic_page)
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

    path("api/book-progress/", book_progress_api, name="book_progress_api"),
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
    # QUIZ
    # =====================================================
    path("api/generate-daily-quiz/", generate_daily_quiz),
    path("api/get-daily-quiz/", get_daily_quiz),
    path("api/submit-daily-quiz/", submit_daily_quiz),

    path("api/get-quiz/", get_quiz),
    path("api/start-quiz/", start_quiz),
    path("api/submit-quiz/", submit_quiz),
    path("api/proctor-log/", proctor_log),
    path("quiz/<int:quiz_id>/", topic_quiz_page, name="topic_quiz"),

]
