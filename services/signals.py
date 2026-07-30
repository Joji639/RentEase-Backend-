from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import ServiceCategory


@receiver([post_save, post_delete], sender=ServiceCategory)
def invalidate_service_categories_cache(sender, **kwargs):
    cache.delete("service_categories")
