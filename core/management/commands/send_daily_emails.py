from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.utils import send_daily_study_email

User = get_user_model()


class Command(BaseCommand):
    help = "Send daily AI-generated study plan emails"

    def handle(self, *args, **kwargs):
        sent = 0

        for user in User.objects.filter(is_active=True):
            if user.email:
                send_daily_study_email(user)
                sent += 1

        self.stdout.write(
            self.style.SUCCESS(f"✅ Daily study emails sent to {sent} users")
        )
