"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early to ensure AppRegistry is populated
# before importing consumers or routing.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from apps.core_services.scanner import routing as scanner_routing
from apps.core_services.reception import routing as reception_routing
from apps.core_services.qms import routing as qms_routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(
        scanner_routing.websocket_urlpatterns
        + reception_routing.websocket_urlpatterns
        + qms_routing.websocket_urlpatterns
    ),
})
