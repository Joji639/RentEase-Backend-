import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ServiceRequest

class TrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.request_id = self.scope["url_route"]["kwargs"]["request_id"]
        self.group_name = f"tracking_{self.request_id}"
        user = self.scope["user"]

        await self.accept()

        if not user:
            await self.send(text_data=json.dumps({"error": "Authentication failed. Please log in again."}))
            await self.close(code=4003)
            return

        is_participant, reason = await self.check_participant(user)
        if not is_participant:
            await self.send(text_data=json.dumps({"error": reason}))
            await self.close(code=4003)
            return

        try:
            await self.channel_layer.group_add(self.group_name, self.channel_name)
        except Exception as e:
            await self.send(text_data=json.dumps({"error": f"Backend channel error: {e}"}))
            await self.close(code=4004)
            return

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        except Exception:
            pass

    async def location_update(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def check_participant(self, user):
        req = ServiceRequest.objects.filter(id=self.request_id).first()
        if not req:
            return False, "Service request not found."
        if user.id == req.user_id:
            return True, ""
        if hasattr(req, "technician") and req.technician and req.technician.user_id == user.id:
            return True, ""
        return False, "You are not a participant of this request."