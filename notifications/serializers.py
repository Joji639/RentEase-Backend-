from rest_framework import serializers
from .models import PushSubscription, Notification


class PushSubscriptionSerializer(serializers.Serializer):
    endpoint = serializers.URLField(max_length=500)
    p256dh = serializers.CharField(max_length=256)
    auth = serializers.CharField(max_length=256)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "title", "body", "is_read", "created_at"]
