from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def assign_user_group(sender, instance, created, **kwargs):
    if created:
        group, group_created = Group.objects.get_or_create(name=instance.role)
        instance.groups.add(group)

        if group_created:
            _assign_default_permissions(group, instance.role)


def _assign_default_permissions(group: Group, role: str):
    content_type = ContentType.objects.get_for_model(CustomUser)

    if role in ("USER", "TECHNICIAN"):
        try:
            perm = Permission.objects.get(
                codename="can_enable_2fa", content_type=content_type
            )
            group.permissions.add(perm)
        except Permission.DoesNotExist:
            pass