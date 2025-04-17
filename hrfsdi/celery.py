import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrfsdi.settings')

app = Celery('hrfsdi')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic task for auto-rejection
app.conf.beat_schedule = {
    'auto-reject-daily': {
        'task': 'student_data.tasks.auto_reject_expired_applications',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
}