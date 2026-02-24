"""
WebSocket URL routing for the QMS app.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/qms/display/(?P<station_id>[0-9a-f-]+)/$',
        consumers.QueueDisplayConsumer.as_asgi(),
    ),
]
