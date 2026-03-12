from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/billing/$', consumers.BillingConsumer.as_asgi()),
]
