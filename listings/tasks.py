from celery import shared_task
from django.utils import timezone
from .models import Listing

@shared_task
def reactivate_expired_listings():
    Listing.objects.filter(
        is_active=False,
        available_to__lt=timezone.now().date(),
    ).update(is_active=True)