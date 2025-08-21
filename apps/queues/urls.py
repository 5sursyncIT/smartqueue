# apps/queues/urls.py
"""
URLs pour les APIs des files d'attente SmartQueue
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QueueViewSet, PublicQueueViewSet

# Router principal pour les ViewSets
router = DefaultRouter()
router.register(r'queues', QueueViewSet, basename='queue')
router.register(r'public/queues', PublicQueueViewSet, basename='public-queue')

# URLs générées automatiquement par le router :
# /api/queues/                          - Liste et création
# /api/queues/{id}/                     - Détails, modification, suppression
# /api/queues/{id}/stats/               - Statistiques
# /api/queues/{id}/tickets/             - Tickets de la file
# 
# Actions temps réel :
# /api/queues/{id}/call_next/           - Appeler ticket suivant
# /api/queues/{id}/pause/               - Mettre en pause
# /api/queues/{id}/resume/              - Reprendre
# /api/queues/{id}/skip_ticket/         - Passer un ticket
# /api/queues/{id}/reset_daily/         - Reset journalier
#
# /api/public/queues/                   - Files publiques

urlpatterns = [
    path('api/', include(router.urls)),
]