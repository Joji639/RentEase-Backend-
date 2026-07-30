import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rentease.settings")
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from chat.middleware import JWTAuthMiddleware
import chat.routing
import bookings.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(chat.routing.websocket_urlpatterns + bookings.routing.websocket_urlpatterns)
    ),
})