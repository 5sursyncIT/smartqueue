# apps/queue_management/urls.py
"""
URLs unifiées pour Queue Management (Queues + Tickets)
Structure cohérente avec géolocalisation intelligente
"""

from django.urls import path
from . import views

app_name = 'queue_management'

urlpatterns = [
    # ============================================
    # QUEUES (FILES D'ATTENTE)
    # ============================================
    path('queues/', views.QueueListCreateView.as_view(), name='queue-list-create'),
    path('queues/<int:pk>/', views.QueueDetailView.as_view(), name='queue-detail'),
    
    # Tickets d'une file spécifique
    path('queues/<int:queue_id>/tickets/', views.QueueTicketsView.as_view(), name='queue-tickets'),
    
    # Géolocalisation intelligente pour files
    path('queues/<int:queue_id>/with-travel/', views.queue_with_travel_time, name='queue-with-travel'),
    
    # ============================================
    # TICKETS
    # ============================================
    path('tickets/', views.TicketListCreateView.as_view(), name='ticket-list-create'),
    path('tickets/<int:pk>/', views.TicketDetailView.as_view(), name='ticket-detail'),
    
    # Actions sur tickets
    path('queues/<int:queue_id>/take-ticket/', views.take_ticket, name='take-ticket'),
    path('queues/<int:queue_id>/call-next/', views.call_next_ticket, name='call-next-ticket'),
    
    # ============================================
    # STATISTIQUES
    # ============================================
    path('stats/', views.queue_management_stats, name='queue-management-stats'),
]








