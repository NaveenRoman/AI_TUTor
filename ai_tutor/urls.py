from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core.views_college import college_dashboard


# ✅ IMPORT SIGNUP VIEW
from core.views.views_auth import role_based_redirect


urlpatterns = [

    # =========================
    # ADMIN
    # =========================
    path("admin/", admin.site.urls),

    # =========================
    # AUTHENTICATION
    # =========================
    path("accounts/redirect/", role_based_redirect, name="role_redirect"),

    path("accounts/", include("django.contrib.auth.urls")),

    path("college/dashboard/", college_dashboard, name="college_dashboard"),


    # =========================
    # CORE APP (ALL PAGES + APIs)
    # =========================
    path("", include("core.urls")),
]

# =========================
# MEDIA FILES (DEV ONLY)
# =========================
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
