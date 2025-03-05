import os
from django import setup

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_app_backend.settings')
setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from Home.routing import websocket_urlpatterns
from Accounts.channels_middleware import JWTWebsocketMiddleware


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTWebsocketMiddleware(
        AuthMiddlewareStack(
            URLRouter(
            websocket_urlpatterns
        ))
    ),
})
