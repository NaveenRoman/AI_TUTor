# core/apps.py

from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):

        # 1️⃣ Load signals
        try:
            import core.signals
            print("[INFO] Signals loaded.")
        except Exception as e:
            print(f"[WARN] Signals load failed: {e}")

        # 2️⃣ Load books into memory
        try:
            from .books_loader import load_books
            load_books()
            print("[INFO] Books loaded into memory.")
        except Exception as e:
            print(f"[WARN] Book loader failed: {e}")

       