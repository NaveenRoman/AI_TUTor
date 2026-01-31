from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# ✅ IMPORT SIGNUP VIEW
from core.views.views_auth import signup

urlpatterns = [

    # =========================
    # ADMIN
    # =========================
    path("admin/", admin.site.urls),

    # =========================
    # AUTHENTICATION
    # =========================
    path("accounts/signup/", signup, name="signup"),
    path("accounts/", include("django.contrib.auth.urls")),

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
