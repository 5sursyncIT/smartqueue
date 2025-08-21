# apps/queues/views.py
"""
ViewSets pour les files d'attente SmartQueue
Gèrent les requêtes HTTP et la logique métier des files d'attente
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils import timezone
from .models import Queue
from .serializers import (
    QueueListSerializer, QueueDetailSerializer,
    QueueCreateSerializer, QueueUpdateSerializer,
    QueueStatsSerializer, QueueActionSerializer
)

@extend_schema_view(
    list=extend_schema(
        summary="Liste des files d'attente",
        description="Récupérer toutes les files d'attente avec filtrage possible",
        tags=["Files d'attente"]
    ),
    retrieve=extend_schema(
        summary="Détails d'une file d'attente",
        description="Récupérer toutes les informations d'une file d'attente spécifique",
        tags=["Files d'attente"]
    ),
    create=extend_schema(
        summary="Créer une file d'attente",
        description="Créer une nouvelle file d'attente pour un service",
        tags=["Files d'attente"]
    ),
    update=extend_schema(
        summary="Modifier une file d'attente",
        description="Modifier les paramètres d'une file d'attente existante",
        tags=["Files d'attente"]
    ),
    destroy=extend_schema(
        summary="Supprimer une file d'attente",
        description="Supprimer définitivement une file d'attente",
        tags=["Files d'attente"]
    )
)
class QueueViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal pour les files d'attente
    
    Fournit les opérations CRUD complètes + actions temps réel :
    - GET /api/queues/ (liste)
    - GET /api/queues/1/ (détails)
    - POST /api/queues/ (création)
    - PUT/PATCH /api/queues/1/ (modification)
    - DELETE /api/queues/1/ (suppression)
    
    Actions temps réel :
    - POST /api/queues/1/call_next/ (appeler suivant)
    - POST /api/queues/1/pause/ (mettre en pause)
    - GET /api/queues/1/stats/ (statistiques)
    """
    
    queryset = Queue.objects.select_related('organization', 'service').all()
    
    # Filtrage et recherche
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'organization', 'service', 'queue_type', 'current_status',
        'processing_strategy', 'is_active'
    ]
    search_fields = ['name', 'description', 'service__name', 'organization__name']
    ordering_fields = ['name', 'created_at', 'waiting_tickets_count', 'daily_tickets_issued']
    ordering = ['-current_status', 'name']  # Files actives en premier
    
    def get_serializer_class(self):
        """
        Retourne le bon serializer selon l'action
        """
        if self.action == 'list':
            return QueueListSerializer
        elif self.action == 'retrieve':
            return QueueDetailSerializer
        elif self.action == 'create':
            return QueueCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return QueueUpdateSerializer
        elif self.action == 'stats':
            return QueueStatsSerializer
        elif self.action in ['call_next', 'pause', 'resume', 'skip_ticket', 'reset_daily']:
            return QueueActionSerializer
        
        return QueueDetailSerializer
    
    def get_permissions(self):
        """
        Définit les permissions selon l'action et le type d'utilisateur
        """
        if self.action in ['list', 'retrieve', 'stats']:
            # Lecture : tout le monde peut voir les files publiques
            permission_classes = [permissions.AllowAny]
        elif self.action == 'create':
            # Création : admins d'organisation et super admins
            permission_classes = [permissions.IsAuthenticated, IsOrganizationAdminOrSuperAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Modification : admin de l'organisation ou super admin
            permission_classes = [permissions.IsAuthenticated, IsQueueOwnerOrSuperAdmin]
        elif self.action in ['call_next', 'pause', 'resume', 'skip_ticket']:
            # Actions temps réel : staff de l'organisation
            permission_classes = [permissions.IsAuthenticated, IsQueueStaffOrSuperAdmin]
        else:
            # Actions administratives : admin organisation
            permission_classes = [permissions.IsAuthenticated, IsQueueOwnerOrSuperAdmin]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filtre le queryset selon le type d'utilisateur
        """
        user = self.request.user
        
        if not user.is_authenticated:
            # Utilisateurs anonymes : files actives des organisations actives
            return Queue.objects.filter(
                is_active=True,
                organization__is_active=True
            ).select_related('organization', 'service')
        
        if user.is_super_admin:
            # Super admin voit toutes les files
            return Queue.objects.select_related('organization', 'service').all()
        elif user.is_organization_admin or user.is_staff:
            # Staff voit les files de son organisation
            if hasattr(user, 'staff_profile'):
                return Queue.objects.filter(
                    organization=user.staff_profile.organization
                ).select_related('organization', 'service')
        
        # Autres utilisateurs : files actives seulement
        return Queue.objects.filter(
            is_active=True,
            organization__is_active=True
        ).select_related('organization', 'service')
    
    @extend_schema(
        summary="Statistiques d'une file d'attente",
        description="Récupérer les statistiques en temps réel d'une file",
        tags=["Files d'attente", "Statistiques"]
    )
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Endpoint pour les statistiques d'une file
        GET /api/queues/1/stats/
        """
        queue = self.get_object()
        serializer = QueueStatsSerializer(queue)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Appeler le ticket suivant",
        description="Appelle le prochain ticket dans la file d'attente",
        request=QueueActionSerializer,
        tags=["Files d'attente", "Actions temps réel"]
    )
    @action(detail=True, methods=['post'])
    def call_next(self, request, pk=None):
        """
        Appeler le ticket suivant
        POST /api/queues/1/call_next/
        """
        queue = self.get_object()
        
        if queue.current_status != 'active':
            return Response({
                'error': 'La file d\'attente n\'est pas active',
                'current_status': queue.get_current_status_display()
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if queue.waiting_tickets_count == 0:
            return Response({
                'error': 'Aucun ticket en attente',
                'message': 'La file est vide'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Trouver le prochain ticket selon la stratégie
        next_ticket = self._get_next_ticket(queue)
        
        if not next_ticket:
            return Response({
                'error': 'Aucun ticket valide trouvé',
                'message': 'Tous les tickets sont expirés ou invalides'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Appeler le ticket
        next_ticket.status = 'called'
        next_ticket.called_at = timezone.now()
        next_ticket.save()
        
        # Mettre à jour la file
        queue.current_ticket_number = next_ticket.number
        queue.waiting_tickets_count = max(0, queue.waiting_tickets_count - 1)
        queue.save()
        
        return Response({
            'success': True,
            'message': f'Ticket {next_ticket.number} appelé',
            'ticket': {
                'id': next_ticket.id,
                'number': next_ticket.number,
                'customer_name': next_ticket.customer_name,
                'priority': next_ticket.priority,
                'wait_time_minutes': (timezone.now() - next_ticket.created_at).total_seconds() // 60
            },
            'queue_status': {
                'current_ticket': queue.current_ticket_number,
                'waiting_count': queue.waiting_tickets_count,
                'estimated_wait_time': queue.estimated_wait_time
            }
        })
    
    @extend_schema(
        summary="Mettre en pause la file",
        description="Met temporairement en pause la file d'attente",
        request=QueueActionSerializer,
        tags=["Files d'attente", "Actions temps réel"]
    )
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """
        Mettre en pause la file d'attente
        POST /api/queues/1/pause/
        """
        queue = self.get_object()
        
        if queue.current_status == 'paused':
            return Response({
                'error': 'La file est déjà en pause'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queue.current_status = 'paused'
        queue.save()
        
        return Response({
            'success': True,
            'message': 'File d\'attente mise en pause',
            'new_status': queue.get_current_status_display()
        })
    
    @extend_schema(
        summary="Reprendre la file",
        description="Remet en marche une file d'attente en pause",
        request=QueueActionSerializer,
        tags=["Files d'attente", "Actions temps réel"]
    )
    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """
        Reprendre la file d'attente
        POST /api/queues/1/resume/
        """
        queue = self.get_object()
        
        if queue.current_status != 'paused':
            return Response({
                'error': 'La file n\'est pas en pause'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queue.current_status = 'active'
        queue.save()
        
        return Response({
            'success': True,
            'message': 'File d\'attente reprise',
            'new_status': queue.get_current_status_display()
        })
    
    @extend_schema(
        summary="Passer un ticket",
        description="Marque un ticket comme sauté (client absent)",
        request=QueueActionSerializer,
        tags=["Files d'attente", "Actions temps réel"]
    )
    @action(detail=True, methods=['post'])
    def skip_ticket(self, request, pk=None):
        """
        Passer/sauter un ticket (client absent)
        POST /api/queues/1/skip_ticket/
        """
        queue = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        ticket_id = serializer.validated_data.get('ticket_id')
        reason = serializer.validated_data.get('reason', 'Client absent')
        
        if not ticket_id:
            return Response({
                'error': 'ticket_id requis pour cette action'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Trouver le ticket
            from apps.tickets.models import Ticket
            ticket = Ticket.objects.get(id=ticket_id, queue=queue)
            
            if ticket.status not in ['waiting', 'called']:
                return Response({
                    'error': f'Ticket {ticket.number} ne peut pas être sauté',
                    'current_status': ticket.get_status_display()
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Marquer comme sauté
            ticket.status = 'skipped'
            ticket.notes = reason
            ticket.save()
            
            # Mettre à jour la file si c'était le ticket courant
            if queue.current_ticket_number == ticket.number:
                queue.waiting_tickets_count = max(0, queue.waiting_tickets_count - 1)
                queue.save()
            
            return Response({
                'success': True,
                'message': f'Ticket {ticket.number} sauté',
                'reason': reason
            })
            
        except Ticket.DoesNotExist:
            return Response({
                'error': 'Ticket non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @extend_schema(
        summary="Reset journalier",
        description="Remet à zéro les compteurs de la journée",
        request=QueueActionSerializer,
        tags=["Files d'attente", "Administration"]
    )
    @action(detail=True, methods=['post'])
    def reset_daily(self, request, pk=None):
        """
        Reset des statistiques journalières
        POST /api/queues/1/reset_daily/
        """
        queue = self.get_object()
        
        # Reset des compteurs
        queue.last_ticket_number = 0
        queue.current_ticket_number = 0
        queue.waiting_tickets_count = 0
        queue.daily_tickets_issued = 0
        queue.daily_tickets_served = 0
        queue.daily_average_wait_time = 0
        queue.stats_date = timezone.now().date()
        queue.save()
        
        return Response({
            'success': True,
            'message': 'Compteurs journaliers remis à zéro',
            'date': queue.stats_date
        })
    
    @extend_schema(
        summary="Tickets de la file",
        description="Récupérer tous les tickets de cette file d'attente",
        tags=["Files d'attente", "Tickets"]
    )
    @action(detail=True, methods=['get'])
    def tickets(self, request, pk=None):
        """
        Liste des tickets de cette file
        GET /api/queues/1/tickets/
        """
        queue = self.get_object()
        tickets = queue.tickets.all().order_by('-created_at')[:50]
        
        # Import dynamique pour éviter les imports circulaires
        from apps.tickets.serializers import TicketListSerializer
        serializer = TicketListSerializer(tickets, many=True)
        
        return Response({
            'queue': queue.name,
            'organization': queue.organization.name,
            'service': queue.service.name,
            'tickets_count': tickets.count(),
            'tickets': serializer.data
        })
    
    def _get_next_ticket(self, queue):
        """
        Trouve le prochain ticket selon la stratégie de traitement
        """
        from apps.tickets.models import Ticket
        
        # Tickets en attente
        waiting_tickets = Ticket.objects.filter(
            queue=queue, 
            status='waiting'
        )
        
        if queue.processing_strategy == 'fifo':
            # Premier arrivé, premier servi
            return waiting_tickets.order_by('created_at').first()
        
        elif queue.processing_strategy == 'priority':
            # Par priorité puis FIFO
            return waiting_tickets.order_by('-priority_level', 'created_at').first()
        
        elif queue.processing_strategy == 'appointment_first':
            # RDV d'abord puis FIFO
            appointment_tickets = waiting_tickets.filter(has_appointment=True)
            if appointment_tickets.exists():
                return appointment_tickets.order_by('appointment_time').first()
            else:
                return waiting_tickets.order_by('created_at').first()
        
        else:  # mixed
            # Stratégie mixte complexe (simplifié pour MVP)
            return waiting_tickets.order_by('-priority_level', 'created_at').first()


# ==============================================
# PERMISSIONS PERSONNALISÉES
# ==============================================

class IsSuperAdmin(permissions.BasePermission):
    """Permission pour les super admins SmartQueue uniquement"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_super_admin


class IsOrganizationAdminOrSuperAdmin(permissions.BasePermission):
    """Permission pour super admins et admins d'organisation"""
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.is_super_admin or user.is_organization_admin


class IsQueueOwnerOrSuperAdmin(permissions.BasePermission):
    """Permission pour super admins et admins de l'organisation propriétaire"""
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if user.is_super_admin:
            return True
        
        if user.is_organization_admin and hasattr(user, 'staff_profile'):
            return user.staff_profile.organization == obj.organization
        
        return False


class IsQueueStaffOrSuperAdmin(permissions.BasePermission):
    """Permission pour super admins et staff de l'organisation (actions temps réel)"""
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        if user.is_super_admin:
            return True
        
        # Staff ou admin de l'organisation
        if hasattr(user, 'staff_profile'):
            return user.staff_profile.organization == obj.organization
        
        return False


# ==============================================
# VIEWSETS SUPPLÉMENTAIRES
# ==============================================

class PublicQueueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet public pour les files d'attente (sans authentification)
    
    Usage : App mobile grand public pour voir l'état des files
    GET /api/public/queues/
    """
    queryset = Queue.objects.filter(
        is_active=True,
        organization__is_active=True,
        current_status='active'
    ).select_related('organization', 'service')
    
    serializer_class = QueueListSerializer
    permission_classes = [permissions.AllowAny]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['organization', 'service', 'queue_type']
    search_fields = ['name', 'service__name', 'organization__name']
    ordering = ['waiting_tickets_count']  # Moins d'attente en premier