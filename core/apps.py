# core/apps.py
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # --- load signals ---
        try:
            import core.signals
            print("[INFO] Signals loaded.")
        except Exception as e:
            print(f"[WARN] Signals load failed: {e}")

        # --- load books at startup ---
        try:
            from .books_loader import load_books
            load_books()
            print("[INFO] Books loaded.")
        except Exception as e:
            print(f"[WARN] Books load skipped: {e}")
