from celery import shared_task
from django.conf import settings
from django.utils import timezone
from pywebpush import webpush, WebPushException
from .models import PushSubscription, Notification


@shared_task(bind=True, max_retries=2, default_retry_delay=10)
def send_push_notification(self, user_id, title, body, url=None):
    subscriptions = PushSubscription.objects.filter(user_id=user_id)
    if not subscriptions.exists():
        return

    payload = {
        "title": title,
        "body": body,
        "icon": "/favicon.svg",
    }
    if url:
        payload["data"] = {"url": url}

    vapid_claims = {
        "sub": "mailto:crudproject77@gmail.com",
        "aud": settings.VAPID_CLAIMS_AUDIENCE,
    }

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
            )
        except WebPushException as exc:
            if exc.response and exc.response.status_code in (410, 404):
                sub.delete()


class NotificationService:
    @staticmethod
    def create_notification(user_id, title, body=""):
        return Notification.objects.create(user_id=user_id, title=title, body=body)

    @staticmethod
    def list_notifications(user_id):
        return Notification.objects.filter(user_id=user_id)

    @staticmethod
    def mark_as_read(notification_id, user_id):
        return Notification.objects.filter(id=notification_id, user_id=user_id).update(is_read=True)

    @staticmethod
    def mark_all_as_read(user_id):
        return Notification.objects.filter(user_id=user_id, is_read=False).update(is_read=True)
