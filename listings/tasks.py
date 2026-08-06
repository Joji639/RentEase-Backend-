from celery import shared_task
from django.utils import timezone
from .models import Listing

@shared_task
def reactivate_expired_listings():
    Listing.objects.filter(
        is_active=False,
        available_to__lt=timezone.now().date(),
    ).update(is_active=True)

@shared_task
def index_listing_task(listing_id):
    from rag.services import index_listing
    try:
        listing = Listing.objects.get(id=listing_id)
    except Listing.DoesNotExist:
        return
    index_listing(listing)