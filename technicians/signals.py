from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache
from .models import TechnicianProfile


@receiver([post_save, post_delete], sender=TechnicianProfile)
def invalidate_technicians_by_category_cache(sender, instance, **kwargs):
    if instance.specialization_id:
        cache.delete(f"technicians_by_category:{instance.specialization_id}")
    if kwargs.get("update_fields") is None and instance.pk:
        try:
            old = TechnicianProfile.objects.get(pk=instance.pk)
            if old.specialization_id and old.specialization_id != instance.specialization_id:
                cache.delete(f"technicians_by_category:{old.specialization_id}")
        except TechnicianProfile.DoesNotExist:
            pass
