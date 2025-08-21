# apps/organizations/urls.py
"""
URLs pour les APIs des organisations SmartQueue
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet, PublicOrganizationViewSet

# Router principal pour les ViewSets
router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'public/organizations', PublicOrganizationViewSet, basename='public-organization')

# URLs générées automatiquement par le router :
# /api/organizations/                    - Liste et création
# /api/organizations/{id}/               - Détails, modification, suppression
# /api/organizations/{id}/stats/         - Statistiques
# /api/organizations/{id}/services/      - Services
# /api/organizations/{id}/queues/        - Files d'attente
# /api/organizations/{id}/dashboard/     - Tableau de bord
# /api/organizations/nearby/             - Recherche géolocalisée
# 
# /api/public/organizations/             - Liste publique
# /api/public/organizations/{id}/        - Détails publics
# /api/public/organizations/{id}/public_services/ - Services publics

urlpatterns = [
    path('api/', include(router.urls)),
]
