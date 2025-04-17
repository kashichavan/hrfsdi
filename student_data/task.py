from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import RequirementStudent

@shared_task
def auto_reject_expired_applications():
    expired = RequirementStudent.objects.filter(
        status='pending',
        requirement__is_scheduled=True,
        requirement__schedule_date__lt=timezone.now() - timedelta(days=1)
    )
    updated_count = expired.update(status='rejected')
    return f"Rejected {updated_count} applications"