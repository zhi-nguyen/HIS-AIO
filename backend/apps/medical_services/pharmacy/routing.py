from django.urls import re_path
from .consumers import PharmacistConsumer

websocket_urlpatterns = [
    re_path(r"^ws/pharmacist/updates/$", PharmacistConsumer.as_asgi()),
]
