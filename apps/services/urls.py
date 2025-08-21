# apps/services/urls.py
"""
URLs pour les APIs des services SmartQueue
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ServiceViewSet, ServiceCategoryViewSet, PublicServiceViewSet

# Router principal pour les ViewSets
router = DefaultRouter()
router.register(r'services', ServiceViewSet, basename='service')
router.register(r'service-categories', ServiceCategoryViewSet, basename='servicecategory')
router.register(r'public/services', PublicServiceViewSet, basename='public-service')

# URLs générées automatiquement par le router :
# /api/services/                         - Liste et création
# /api/services/{id}/                    - Détails, modification, suppression
# /api/services/{id}/stats/              - Statistiques
# /api/services/{id}/queues/             - Files d'attente
# /api/services/{id}/tickets_history/    - Historique tickets
# /api/services/by_organization/         - Services par organisation
# /api/services/by_category/             - Services par catégorie
#
# /api/service-categories/               - Catégories CRUD
# 
# /api/public/services/                  - Services publics

urlpatterns = [
    path('api/', include(router.urls)),
]