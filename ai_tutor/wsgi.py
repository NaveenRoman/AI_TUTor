"""
WSGI config for ai_tutor project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_tutor.settings")

application = get_wsgi_application()
