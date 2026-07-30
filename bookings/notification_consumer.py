import json
from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user:
            await self.close(code=4003)
            return

        self.user_id = str(user.id)
        self.group_name = f"notify_{self.user_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add("technician_updates", self.channel_name)

        if getattr(user, "role", "") == "ADMIN":
            await self.channel_layer.group_add("notify_admin", self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            pass
        try:
            await self.channel_layer.group_discard("technician_updates", self.channel_name)
        except Exception:
            pass
        try:
            await self.channel_layer.group_discard("notify_admin", self.channel_name)
        except Exception:
            pass

    async def notification(self, event):
        await self.send(text_data=json.dumps(event))
