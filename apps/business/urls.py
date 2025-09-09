# apps/business/urls.py
"""
URLs unifiées pour Business (Organizations + Services)
Structure cohérente selon approche superviseur
"""

from django.urls import path
from . import views

app_name = 'business'

urlpatterns = [
    # ============================================
    # ORGANIZATIONS
    # ============================================
    path('organizations/', views.organization_list_create_view, name='organization-list-create'),
    path('organizations/<int:pk>/', views.OrganizationDetailView.as_view(), name='organization-detail'),
    
    # Services d'une organisation
    path('organizations/<int:organization_id>/services/', views.OrganizationServicesView.as_view(), name='organization-services'),
    
    # ============================================
    # SERVICES 
    # ============================================
    path('services/', views.service_list_create_view, name='service-list-create'),
    path('services/<int:pk>/', views.ServiceDetailView.as_view(), name='service-detail'),
    
    # ============================================
    # UTILITAIRES
    # ============================================
    path('stats/', views.business_stats, name='business-stats'),
]