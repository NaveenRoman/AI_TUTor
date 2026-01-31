"""
core/views.py

Central re-export file.
Do NOT write logic here.
"""

# ======================================================
# PAGE / STATIC VIEWS (re-export)
# ======================================================
from .views.views_pages import (
    index_page,
    categories_page,
    ai_tutor_page,
    contact_page,
    interview_page,   # ✅ REQUIRED for /interview/
)

# ======================================================
# DASHBOARD VIEW (re-export)
# ======================================================
from .views.views_dashboard import dashboard
