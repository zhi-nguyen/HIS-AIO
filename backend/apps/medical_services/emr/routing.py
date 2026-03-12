from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/clinical/(?P<visit_id>[0-9a-f-]+)/updates/?$', consumers.ClinicalConsumer.as_asgi()),
]
