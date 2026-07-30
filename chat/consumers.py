import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message
from notifications.services import send_push_notification, NotificationService
from bookings.services import notify_user


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.room_group_name = f"chat_{self.conversation_id}"
        user = self.scope["user"]
        await self.accept()

        if not user:
            await self.close(code=4001) 
            return

        is_participant = await self.check_participant(user)
        if not is_participant:
            await self.close(code=4003)  
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get("message", "").strip()
        if not content:
            return

        user = self.scope["user"]
        message = await self.save_message(user, content)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": content,
                "sender_id": str(user.id),
                "sender_name": user.full_name,
                "created_at": message.created_at.isoformat(),
            },
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def check_participant(self, user):
        conv = Conversation.objects.filter(id=self.conversation_id).first()
        if not conv:
            return False
        return user.id in (conv.user_a_id, conv.user_b_id)

    @database_sync_to_async
    def save_message(self, user, content):
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(conversation=conversation, sender=user, content=content)

        other_id = conversation.user_b_id if user.id == conversation.user_a_id else conversation.user_a_id
        send_push_notification.delay(other_id, "New Message", f"{user.full_name}: {content[:80]}")
        NotificationService.create_notification(
            other_id,
            f"New message from {user.full_name}",
            content[:120],
        )
        notify_user(other_id, "new_message", conversation_id=self.conversation_id)

        return message