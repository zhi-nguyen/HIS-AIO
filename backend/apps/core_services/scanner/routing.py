"""
WebSocket URL routing for the Scanner app.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/scanner/(?P<station_id>\w+)/$', consumers.ScannerConsumer.as_asgi()),
]
