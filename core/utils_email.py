from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from core.models import TopicStat

User = get_user_model()

def send_daily_study_plan_emails():
    users = User.objects.all()

    for user in users:
        if not user.email:
            continue

        weak_topics = (
            TopicStat.objects
            .filter(user=user, mastery_score__lt=40)
            .order_by("mastery_score")[:2]
        )

        if not weak_topics.exists():
            continue

        study_plan = [
            f"Revise {t.topic} + practice 10 questions"
            for t in weak_topics
        ]

        send_mail(
            subject="📘 Your AI Study Plan for Today",
            message="\n".join(study_plan),
            from_email="ai@aitutor.com",
            recipient_list=[user.email],
            fail_silently=True
        )
