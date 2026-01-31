import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_tutor.settings')
app = Celery('ai_tutor')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    # weekly at Monday 06:00 (change as needed)
    'generate-weekly-quizzes': {
        'task': 'core.tasks.generate_weekly_quizzes',
        'schedule': crontab(day_of_week='mon', hour=6, minute=0),
    },
    # daily refresh weak topics
    'daily-update-weak-topics': {
        'task': 'core.tasks.update_user_weak_topics',
        'schedule': crontab(hour=4, minute=0), 
    },
}