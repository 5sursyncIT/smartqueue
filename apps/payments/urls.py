# apps/payments/urls.py
"""
URLs pour les paiements SmartQueue Sénégal
APIs Wave Money, Orange Money, Free Money
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentProviderViewSet,
    PaymentViewSet, 
    PaymentMethodViewSet,
    PaymentPlanViewSet,
    wave_callback,
    orange_callback,
    free_callback,
    payment_stats
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'providers', PaymentProviderViewSet, basename='payment-provider')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'methods', PaymentMethodViewSet, basename='payment-method')

app_name = 'payments'

urlpatterns = [
    # APIs REST principales
    path('api/', include(router.urls)),
    
    # Endpoints spéciaux
    path('api/plans/', PaymentPlanViewSet.as_view(), name='payment-plans'),
    path('api/payments/stats/', payment_stats, name='payment-stats'),
    
    # Webhooks des providers (URLs publiques)
    path('webhooks/wave/', wave_callback, name='wave-callback'),
    path('webhooks/orange/', orange_callback, name='orange-callback'),
    path('webhooks/free/', free_callback, name='free-callback'),
]

"""
URLs disponibles:

CRUD Providers (Admin seulement):
- GET    /api/providers/                 - Liste des providers
- GET    /api/providers/{id}/            - Détails d'un provider
- POST   /api/providers/                 - Créer provider
- PUT    /api/providers/{id}/            - Modifier provider
- DELETE /api/providers/{id}/            - Supprimer provider

CRUD Paiements:
- GET    /api/payments/                  - Historique paiements utilisateur
- POST   /api/payments/                  - Créer nouveau paiement
- GET    /api/payments/{id}/             - Détails d'un paiement
- POST   /api/payments/{id}/cancel/      - Annuler paiement
- GET    /api/payments/{id}/status_check/ - Vérifier statut

Méthodes de paiement:
- GET    /api/methods/                   - Méthodes sauvegardées
- POST   /api/methods/                   - Ajouter méthode
- DELETE /api/methods/{id}/              - Supprimer méthode

Plans tarifaires:
- GET    /api/plans/                     - Plans disponibles

Statistiques:
- GET    /api/payments/stats/            - Stats utilisateur

Webhooks (publics):
- POST   /webhooks/wave/                 - Callback Wave Money
- POST   /webhooks/orange/               - Callback Orange Money  
- POST   /webhooks/free/                 - Callback Free Money
"""