# apps/analytics/urls.py
"""
URLs pour les analytics SmartQueue Sénégal
APIs pour métriques, KPIs et tableaux de bord
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrganizationMetricsViewSet,
    ServiceMetricsViewSet,
    QueueMetricsViewSet,
    CustomerSatisfactionViewSet,
    dashboard_overview,
    realtime_metrics,
    custom_report,
    satisfaction_stats
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'organization-metrics', OrganizationMetricsViewSet, basename='organization-metrics')
router.register(r'service-metrics', ServiceMetricsViewSet, basename='service-metrics')
router.register(r'queue-metrics', QueueMetricsViewSet, basename='queue-metrics')
router.register(r'satisfaction', CustomerSatisfactionViewSet, basename='customer-satisfaction')

app_name = 'analytics'

urlpatterns = [
    # APIs REST principales (CRUD)
    path('api/', include(router.urls)),
    
    # Endpoints spécialisés analytics
    path('api/dashboard/', dashboard_overview, name='dashboard-overview'),
    path('api/realtime/', realtime_metrics, name='realtime-metrics'),
    path('api/reports/custom/', custom_report, name='custom-report'),
    path('api/satisfaction/stats/', satisfaction_stats, name='satisfaction-stats'),
]

"""
URLs disponibles:

=== CRUD Métriques ===
- GET    /api/organization-metrics/           - Liste métriques organisations
- GET    /api/organization-metrics/{id}/      - Détails métriques organisation
- GET    /api/service-metrics/                - Liste métriques services  
- GET    /api/service-metrics/{id}/           - Détails métriques service
- GET    /api/queue-metrics/                  - Liste métriques files d'attente
- GET    /api/queue-metrics/{id}/             - Détails métriques file

=== Satisfaction Client ===
- GET    /api/satisfaction/                   - Liste évaluations satisfaction
- POST   /api/satisfaction/                   - Créer évaluation (clients)
- GET    /api/satisfaction/{id}/              - Détails évaluation
- PUT    /api/satisfaction/{id}/              - Modifier évaluation (client propriétaire)
- DELETE /api/satisfaction/{id}/              - Supprimer évaluation (client propriétaire)

=== Dashboard et Analytics ===
- GET    /api/dashboard/                      - Dashboard principal avec KPIs
- GET    /api/realtime/                       - Métriques temps réel
- POST   /api/reports/custom/                 - Génération rapports personnalisés
- GET    /api/satisfaction/stats/             - Statistiques satisfaction détaillées

=== Paramètres de filtrage ===

Dashboard (/api/dashboard/):
- Pas de paramètres - retourne les KPIs selon les permissions utilisateur

Temps réel (/api/realtime/):
- Pas de paramètres - état actuel de toutes les files accessibles

Rapport personnalisé (/api/reports/custom/):
POST avec body JSON:
{
    "type": "organization|service|queue",
    "date_from": "YYYY-MM-DD",
    "date_to": "YYYY-MM-DD",
    "organization_ids": [1, 2, 3],  // optionnel
    "service_ids": [1, 2, 3],       // optionnel
    "metrics": ["tickets_issued", "tickets_served", "avg_wait_time"]
}

Statistiques satisfaction (/api/satisfaction/stats/):
- ?days=30                          - Période en jours (défaut: 30)
- ?organization_id=1                - Filtrer par organisation
- ?service_id=1                     - Filtrer par service

=== Filtres communs pour les ViewSets ===

Organization Metrics:
- ?organization=1                   - Filtrer par organisation
- ?date=2024-01-15                  - Filtrer par date
- ?date__gte=2024-01-01             - Depuis une date
- ?date__lte=2024-01-31             - Jusqu'à une date

Service Metrics:
- ?service=1                        - Filtrer par service  
- ?organization=1                   - Filtrer par organisation
- ?date=2024-01-15                  - Filtrer par date

Queue Metrics:
- ?queue=1                          - Filtrer par file
- ?queue_status=active              - Filtrer par statut
- ?timestamp__gte=2024-01-15T10:00  - Depuis timestamp

Customer Satisfaction:
- ?organization=1                   - Filtrer par organisation
- ?service=1                        - Filtrer par service
- ?rating=5                         - Filtrer par note
- ?rating__gte=4                    - Note minimum

=== Permissions ===
- Super Admin: Accès à toutes les métriques
- Organization Admin: Métriques de ses organisations seulement
- Staff: Métriques de son organisation seulement  
- Customer: Peut créer des évaluations et voir les siennes
"""