# apps/tickets/urls.py
"""
URLs pour les APIs des tickets SmartQueue
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TicketViewSet, PublicTicketViewSet

# Router principal pour les ViewSets
router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'public/tickets', PublicTicketViewSet, basename='public-ticket')

# URLs générées automatiquement par le router :
# /api/tickets/                         - Liste et création (prise de ticket)
# /api/tickets/{id}/                    - Détails, modification, suppression
# /api/tickets/my_tickets/              - Mes tickets (client connecté)
# /api/tickets/stats/                   - Statistiques globales
# 
# Actions spécialisées :
# /api/tickets/{id}/cancel/             - Annuler un ticket
# /api/tickets/{id}/transfer/           - Transférer un ticket (staff)
# /api/tickets/{id}/extend/             - Prolonger un ticket
# /api/tickets/{id}/call_again/         - Rappeler un ticket (staff)
#
# /api/public/tickets/                  - Prise de ticket anonyme (bornes)

urlpatterns = [
    path('api/', include(router.urls)),
]