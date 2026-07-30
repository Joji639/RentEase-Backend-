from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from common.responses import APIResponse
from .serializers import PushSubscriptionSerializer, NotificationSerializer
from .models import PushSubscription
from .services import NotificationService


class SubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=serializer.validated_data["endpoint"],
            defaults={
                "p256dh": serializer.validated_data["p256dh"],
                "auth": serializer.validated_data["auth"],
            },
        )
        return APIResponse.success(message="Subscribed.", status=status.HTTP_201_CREATED)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = NotificationService.list_notifications(request.user.id)
        return APIResponse.success(
            data=NotificationSerializer(notifications, many=True).data,
            message="Notifications fetched.",
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        notification_id = request.data.get("id")
        if notification_id:
            NotificationService.mark_as_read(notification_id, request.user.id)
        else:
            NotificationService.mark_all_as_read(request.user.id)
        return APIResponse.success(message="Marked as read.", status=status.HTTP_200_OK)
