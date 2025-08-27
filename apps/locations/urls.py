# apps/locations/urls.py
"""
URLs pour géolocalisation intelligente SmartQueue
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'locations'

urlpatterns = [
    # Régions et communes
    path('regions/', views.RegionListView.as_view(), name='regions-list'),
    path('communes/', views.CommuneListView.as_view(), name='communes-list'),
    path('regions/<int:region_id>/communes/', views.CommunesByRegionView.as_view(), name='communes-by-region'),
    
    # Localisation utilisateur
    path('user/location/update/', views.UpdateUserLocationView.as_view(), name='update-location'),
    path('user/location/', views.GetUserLocationView.as_view(), name='get-location'),
    
    # Calculs de temps de trajet
    path('calculate-travel-time/', views.CalculateTravelTimeView.as_view(), name='calculate-travel-time'),
    path('user/travel-estimates/', views.UserTravelEstimatesView.as_view(), name='user-travel-estimates'),
    
    # Conditions de circulation
    path('traffic-conditions/', views.TrafficConditionsView.as_view(), name='traffic-conditions'),
    
    # Organisations proches
    path('nearby-organizations/', views.NearbyOrganizationsView.as_view(), name='nearby-organizations'),
    
    # Réorganisation des files
    path('queues/<int:queue_id>/reorganize/', views.trigger_queue_reorganization, name='trigger-queue-reorganization'),
]