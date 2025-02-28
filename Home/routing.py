from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/user/notification/", consumers.NotificatonConsumer.as_asgi()),
]
