# apps/core/routing.py
"""
Routing WebSockets pour SmartQueue
Notifications temps réel géolocalisation
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Notifications utilisateur individuelles
    re_path(r'ws/notifications/user/(?P<user_id>\w+)/$', consumers.UserNotificationConsumer.as_asgi()),
    
    # Notifications géolocalisation temps réel
    re_path(r'ws/location/updates/(?P<user_id>\w+)/$', consumers.LocationUpdateConsumer.as_asgi()),
    
    # File d'attente temps réel (position, notifications)
    re_path(r'ws/queue/(?P<queue_id>\w+)/$', consumers.QueueUpdatesConsumer.as_asgi()),
    
    # Staff/admin: surveillance globale
    re_path(r'ws/admin/dashboard/$', consumers.AdminDashboardConsumer.as_asgi()),
    
    # Organisation: surveillance des files
    re_path(r'ws/org/(?P<org_id>\w+)/monitor/$', consumers.OrganizationMonitorConsumer.as_asgi()),
]