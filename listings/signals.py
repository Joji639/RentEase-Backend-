from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import ListingCategory


@receiver([post_save, post_delete], sender=ListingCategory)
def invalidate_listing_categories_cache(sender, **kwargs):
    cache.delete("listing_categories")
