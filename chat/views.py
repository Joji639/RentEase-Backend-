from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib.auth import get_user_model
from django.db.models import Q

from common.responses import APIResponse
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

User = get_user_model()


class StartConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        other_user_id = request.data.get("other_user_id")
        listing_id = request.data.get("listing_id")
        service_request_id = request.data.get("service_request_id")

        other_user = User.objects.filter(id=other_user_id).first()
        if not other_user:
            return APIResponse.error(message="User not found.", status=status.HTTP_404_NOT_FOUND)

        conv = Conversation.objects.filter(
            Q(user_a=request.user, user_b=other_user) |
            Q(user_a=other_user, user_b=request.user),
            listing_id=listing_id, service_request_id=service_request_id,
        ).first()

        user_a, user_b = sorted([request.user, other_user], key=lambda u: u.id)

        if conv:
            if conv.user_a_id != user_a.id or conv.user_b_id != user_b.id:
                conv.user_a = user_a
                conv.user_b = user_b
                conv.save(update_fields=["user_a", "user_b"])
        else:
            conv = Conversation.objects.create(
                user_a=user_a, user_b=user_b,
                listing_id=listing_id, service_request_id=service_request_id,
            )

        return APIResponse.success(
            data=ConversationSerializer(conv, context={"request": request}).data,
            message="Conversation ready.", status=status.HTTP_200_OK,
        )


class MyConversationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        convs = Conversation.objects.filter(
            Q(user_a=request.user) | Q(user_b=request.user)
        ).order_by("-created_at")

        seen = set()
        unique = []
        for c in convs:
            key = (min(c.user_a_id, c.user_b_id), max(c.user_a_id, c.user_b_id), c.listing_id, c.service_request_id)
            if key not in seen:
                seen.add(key)
                unique.append(c)

        return APIResponse.success(
            data=ConversationSerializer(unique, many=True, context={"request": request}).data,
            message="Conversations fetched.", status=status.HTTP_200_OK,
        )


class ConversationMessagesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        conv = Conversation.objects.filter(id=conversation_id).first()
        if not conv or request.user.id not in (conv.user_a_id, conv.user_b_id):
            return APIResponse.error(message="Conversation not found.", status=status.HTTP_404_NOT_FOUND)
        messages = conv.messages.all()
        return APIResponse.success(
            data=MessageSerializer(messages, many=True).data,
            message="Messages fetched.", status=status.HTTP_200_OK,
        )