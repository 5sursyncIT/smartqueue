# config/asgi.py
"""
Configuration ASGI pour SmartQueue
Support WebSockets pour notifications temps réel géolocalisation
"""

import os
from django.core.asgi import get_asgi_application

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Applications ASGI
django_asgi_app = get_asgi_application()

# WebSockets routing
try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from apps.core.routing import websocket_urlpatterns
    
    application = ProtocolTypeRouter({
        # HTTP traditionnel
        "http": django_asgi_app,
        
        # WebSockets
        "websocket": AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })
    
    print("🔌 WebSockets activés pour notifications géolocalisation")
    
except ImportError:
    # Fallback si channels pas installé
    application = django_asgi_app
    print("⚠️ WebSockets désactivés - Channels non installé")
