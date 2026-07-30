from rest_framework import serializers
from .models import Conversation, Message

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "sender_name", "content", "is_read", "created_at"]
        read_only_fields = ["id", "sender", "created_at"]

class ConversationSerializer(serializers.ModelSerializer):
    other_user_name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ["id", "user_a", "user_b", "listing", "service_request", "other_user_name", "last_message", "created_at"]

    def get_other_user_name(self, obj):
        request_user = self.context["request"].user
        other = obj.user_b if obj.user_a_id == request_user.id else obj.user_a
        return other.full_name

    def get_last_message(self, obj):
        last = obj.messages.last()
        return last.content if last else None