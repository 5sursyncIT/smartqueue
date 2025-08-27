# apps/core/urls.py
"""
URLs pour l'application core SmartQueue
Routes utilitaires, health check, configuration
"""

from django.urls import path, include
from . import views

app_name = 'core'

urlpatterns = [
    # Health check et status
    path('health/', views.HealthCheckView.as_view(), name='health'),
    path('status/', views.SystemStatusView.as_view(), name='status'),
    
    # Configuration publique (lecture seule)
    path('config/', views.PublicConfigView.as_view(), name='config'),
    
    # Utilitaires
    path('utils/validate-phone/', views.ValidatePhoneView.as_view(), name='validate-phone'),
    path('utils/regions/', views.SenegalRegionsView.as_view(), name='senegal-regions'),
    
    # Logs et monitoring (admin seulement)
    path('logs/', views.ActivityLogListView.as_view(), name='activity-logs'),
    path('logs/<int:pk>/', views.ActivityLogDetailView.as_view(), name='activity-log-detail'),
    
    # Maintenance mode
    path('maintenance/', views.MaintenanceView.as_view(), name='maintenance'),
]