# apps/tickets/views.py
"""
ViewSets pour les tickets SmartQueue
Gèrent la prise de tickets et le suivi en temps réel
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta, datetime
from .models import Ticket
from .serializers import (
    TicketListSerializer, TicketDetailSerializer,
    TicketCreateSerializer, TicketUpdateSerializer,
    TicketActionSerializer, TicketStatsSerializer
)

@extend_schema_view(
    list=extend_schema(
        summary="Liste des tickets",
        description="Récupérer tous les tickets avec filtrage possible",
        tags=["Tickets"]
    ),
    retrieve=extend_schema(
        summary="Détails d'un ticket",
        description="Récupérer toutes les informations d'un ticket spécifique",
        tags=["Tickets"]
    ),
    create=extend_schema(
        summary="Prendre un ticket",
        description="Créer un nouveau ticket (prise de ticket par un client)",
        tags=["Tickets"]
    ),
    update=extend_schema(
        summary="Modifier un ticket",
        description="Modifier les informations d'un ticket existant",
        tags=["Tickets"]
    ),
    destroy=extend_schema(
        summary="Supprimer un ticket",
        description="Supprimer définitivement un ticket",
        tags=["Tickets"]
    )
)
class TicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal pour les tickets
    
    Fournit les opérations CRUD complètes + actions spécialisées :
    - GET /api/tickets/ (liste)
    - GET /api/tickets/1/ (détails)
    - POST /api/tickets/ (prise de ticket)
    - PUT/PATCH /api/tickets/1/ (modification)
    - DELETE /api/tickets/1/ (suppression)
    
    Actions spécialisées :
    - POST /api/tickets/1/cancel/ (annuler)
    - POST /api/tickets/1/transfer/ (transférer)
    - GET /api/tickets/my_tickets/ (mes tickets)
    - GET /api/tickets/stats/ (statistiques)
    """
    
    queryset = Ticket.objects.select_related(
        'queue', 'service', 'customer', 'serving_agent'
    ).all()
    
    # Filtrage et recherche
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'queue', 'service', 'customer', 'status', 'priority',
        'creation_channel', 'serving_agent'
    ]
    search_fields = [
        'ticket_number', 'customer_notes', 
        'customer__first_name', 'customer__last_name',
        'service__name', 'queue__name'
    ]
    ordering_fields = ['created_at', 'queue_position', 'wait_time_minutes']
    ordering = ['-created_at']  # Plus récents en premier
    
    def get_serializer_class(self):
        """
        Retourne le bon serializer selon l'action
        """
        if self.action == 'list':
            return TicketListSerializer
        elif self.action == 'retrieve':
            return TicketDetailSerializer
        elif self.action == 'create':
            return TicketCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TicketUpdateSerializer
        elif self.action in ['cancel', 'transfer', 'extend', 'call_again']:
            return TicketActionSerializer
        elif self.action == 'stats':
            return TicketStatsSerializer
        
        return TicketDetailSerializer
    
    def get_permissions(self):
        """
        Définit les permissions selon l'action et le type d'utilisateur
        """
        if self.action == 'create':
            # Prise de ticket : tout le monde (même anonyme)
            permission_classes = [permissions.AllowAny]
        elif self.action in ['list', 'retrieve']:
            # Lecture : utilisateur connecté
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update']:
            # Modification : propriétaire du ticket ou staff
            permission_classes = [permissions.IsAuthenticated, IsTicketOwnerOrStaff]
        elif self.action in ['cancel', 'extend']:
            # Actions client : propriétaire du ticket
            permission_classes = [permissions.IsAuthenticated, IsTicketOwner]
        elif self.action in ['transfer', 'call_again']:
            # Actions staff : staff de l'organisation
            permission_classes = [permissions.IsAuthenticated, IsOrganizationStaff]
        elif self.action == 'destroy':
            # Suppression : super admin seulement
            permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
        else:
            # Actions générales : utilisateur connecté
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filtre le queryset selon le type d'utilisateur
        """
        user = self.request.user
        
        if not user.is_authenticated:
            # Utilisateurs anonymes : aucun ticket visible
            return Ticket.objects.none()
        
        if user.is_super_admin:
            # Super admin voit tous les tickets
            return Ticket.objects.select_related(
                'queue', 'service', 'customer', 'serving_agent'
            ).all()
        elif user.is_organization_admin or user.is_staff:
            # Staff voit les tickets de son organisation
            if hasattr(user, 'staff_profile'):
                return Ticket.objects.filter(
                    queue__organization=user.staff_profile.organization
                ).select_related('queue', 'service', 'customer', 'serving_agent')
        elif user.is_customer:
            # Clients voient seulement leurs propres tickets
            return Ticket.objects.filter(
                customer=user
            ).select_related('queue', 'service', 'serving_agent')
        
        # Par défaut : aucun ticket
        return Ticket.objects.none()
    
    @extend_schema(
        summary="Mes tickets",
        description="Récupérer tous les tickets du client connecté",
        tags=["Tickets", "Client"]
    )
    @action(detail=False, methods=['get'])
    def my_tickets(self, request):
        """
        Liste des tickets du client connecté
        GET /api/tickets/my_tickets/
        """
        if not request.user.is_authenticated:
            return Response({
                'error': 'Authentification requise'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Tickets du client
        tickets = Ticket.objects.filter(
            customer=request.user
        ).select_related('queue', 'service').order_by('-created_at')
        
        # Séparer par statut
        active_tickets = tickets.filter(status__in=['waiting', 'called', 'serving'])
        completed_tickets = tickets.filter(status__in=['served', 'cancelled', 'expired', 'no_show'])[:10]
        
        return Response({
            'active_tickets': TicketListSerializer(active_tickets, many=True).data,
            'completed_tickets': TicketListSerializer(completed_tickets, many=True).data,
            'total_tickets': tickets.count(),
            'success_rate': self._calculate_user_success_rate(request.user)
        })
    
    @extend_schema(
        summary="Annuler un ticket",
        description="Permet au client d'annuler son ticket",
        request=TicketActionSerializer,
        tags=["Tickets", "Actions client"]
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Annuler un ticket
        POST /api/tickets/1/cancel/
        """
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if ticket.status not in ['waiting', 'called']:
            return Response({
                'error': f'Impossible d\'annuler un ticket {ticket.get_status_display().lower()}',
                'current_status': ticket.get_status_display()
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Annuler le ticket
        ticket.status = 'cancelled'
        ticket.customer_notes += f"\nAnnulé le {timezone.now().strftime('%d/%m/%Y à %H:%M')}"
        ticket.save()
        
        # Mettre à jour la file
        if ticket.status == 'waiting':
            ticket.queue.waiting_tickets_count = max(0, ticket.queue.waiting_tickets_count - 1)
            ticket.queue.save()
        
        return Response({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} annulé avec succès',
            'new_status': ticket.get_status_display()
        })
    
    @extend_schema(
        summary="Transférer un ticket",
        description="Transférer un ticket vers une autre file d'attente",
        request=TicketActionSerializer,
        tags=["Tickets", "Actions staff"]
    )
    @action(detail=True, methods=['post'])
    def transfer(self, request, pk=None):
        """
        Transférer un ticket vers une autre file
        POST /api/tickets/1/transfer/
        """
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        target_queue_id = serializer.validated_data.get('target_queue_id')
        reason = serializer.validated_data.get('reason', 'Transfert demandé')
        
        if not target_queue_id:
            return Response({
                'error': 'target_queue_id requis pour le transfert'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from apps.queues.models import Queue
            target_queue = Queue.objects.get(id=target_queue_id)
            
            if target_queue == ticket.queue:
                return Response({
                    'error': 'Impossible de transférer vers la même file'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if target_queue.current_status != 'active':
                return Response({
                    'error': f'La file cible est {target_queue.get_current_status_display().lower()}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Effectuer le transfert
            old_queue = ticket.queue
            ticket.queue = target_queue
            ticket.service = target_queue.service
            ticket.queue_position = target_queue.waiting_tickets_count + 1
            ticket.status = 'transferred'
            ticket.customer_notes += f"\nTransféré de {old_queue.name} vers {target_queue.name}: {reason}"
            ticket.save()
            
            # Mettre à jour les files
            old_queue.waiting_tickets_count = max(0, old_queue.waiting_tickets_count - 1)
            old_queue.save()
            
            target_queue.waiting_tickets_count += 1
            target_queue.save()
            
            return Response({
                'success': True,
                'message': f'Ticket {ticket.ticket_number} transféré avec succès',
                'old_queue': old_queue.name,
                'new_queue': target_queue.name,
                'new_position': ticket.queue_position
            })
            
        except Queue.DoesNotExist:
            return Response({
                'error': 'File d\'attente cible introuvable'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @extend_schema(
        summary="Prolonger un ticket",
        description="Prolonger la validité d'un ticket",
        request=TicketActionSerializer,
        tags=["Tickets", "Actions client"]
    )
    @action(detail=True, methods=['post'])
    def extend(self, request, pk=None):
        """
        Prolonger la validité d'un ticket
        POST /api/tickets/1/extend/
        """
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        extend_minutes = serializer.validated_data.get('extend_minutes', 15)
        
        if ticket.status != 'waiting':
            return Response({
                'error': f'Impossible de prolonger un ticket {ticket.get_status_display().lower()}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier que le ticket n'a pas déjà été prolongé trop de fois
        extensions_count = ticket.customer_notes.count('Prolongé')
        if extensions_count >= 2:
            return Response({
                'error': 'Nombre maximum d\'extensions atteint (2)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prolonger
        ticket.expires_at += timedelta(minutes=extend_minutes)
        ticket.customer_notes += f"\nProlongé de {extend_minutes} minutes le {timezone.now().strftime('%d/%m/%Y à %H:%M')}"
        ticket.save()
        
        return Response({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} prolongé de {extend_minutes} minutes',
            'new_expiry': ticket.expires_at
        })
    
    @extend_schema(
        summary="Rappeler un ticket",
        description="Appeler à nouveau un ticket (par le staff)",
        request=TicketActionSerializer,
        tags=["Tickets", "Actions staff"]
    )
    @action(detail=True, methods=['post'])
    def call_again(self, request, pk=None):
        """
        Rappeler un ticket
        POST /api/tickets/1/call_again/
        """
        ticket = self.get_object()
        
        if ticket.status not in ['called', 'waiting']:
            return Response({
                'error': f'Impossible de rappeler un ticket {ticket.get_status_display().lower()}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Rappeler
        ticket.status = 'called'
        ticket.called_at = timezone.now()
        ticket.call_count += 1
        ticket.save()
        
        return Response({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} rappelé ({ticket.call_count}e fois)',
            'call_count': ticket.call_count
        })
    
    @extend_schema(
        summary="Statistiques des tickets",
        description="Récupérer les statistiques globales des tickets",
        tags=["Tickets", "Statistiques"]
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Statistiques globales des tickets
        GET /api/tickets/stats/
        """
        # Filtrer selon l'utilisateur
        queryset = self.get_queryset()
        
        # Statistiques générales
        total_tickets = queryset.count()
        
        # Par statut
        status_counts = queryset.values('status').annotate(count=Count('id'))
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        # Temps moyens
        avg_stats = queryset.aggregate(
            avg_wait_time=Avg('wait_time_minutes'),
            avg_service_time=Avg('service_time_minutes')
        )
        
        # Statistiques aujourd'hui
        today = timezone.now().date()
        today_tickets = queryset.filter(created_at__date=today)
        
        # Taux de succès
        served_count = status_dict.get('served', 0)
        success_rate = (served_count / total_tickets * 100) if total_tickets > 0 else 0
        
        return Response({
            'total_tickets': total_tickets,
            'waiting_tickets': status_dict.get('waiting', 0),
            'served_tickets': status_dict.get('served', 0),
            'cancelled_tickets': status_dict.get('cancelled', 0),
            'expired_tickets': status_dict.get('expired', 0),
            
            'average_wait_time': avg_stats['avg_wait_time'] or 0,
            'average_service_time': avg_stats['avg_service_time'] or 0,
            'success_rate': round(success_rate, 1),
            
            'today_stats': {
                'total': today_tickets.count(),
                'served': today_tickets.filter(status='served').count(),
                'waiting': today_tickets.filter(status='waiting').count()
            },
            
            'weekly_stats': self._get_weekly_stats(queryset)
        })
    
    def _calculate_user_success_rate(self, user):
        """Calcule le taux de succès d'un utilisateur"""
        user_tickets = Ticket.objects.filter(customer=user)
        total = user_tickets.count()
        served = user_tickets.filter(status='served').count()
        
        if total == 0:
            return 0.0
        return round((served / total) * 100, 1)
    
    def _get_weekly_stats(self, queryset):
        """Statistiques des 7 derniers jours"""
        weekly_stats = []
        today = timezone.now().date()
        
        for i in range(7):
            date = today - timedelta(days=i)
            day_tickets = queryset.filter(created_at__date=date)
            
            weekly_stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'day_name': date.strftime('%A'),
                'total': day_tickets.count(),
                'served': day_tickets.filter(status='served').count(),
                'cancelled': day_tickets.filter(status='cancelled').count()
            })
        
        return list(reversed(weekly_stats))


# ==============================================
# PERMISSIONS PERSONNALISÉES
# ==============================================

class IsSuperAdmin(permissions.BasePermission):
    """Permission pour les super admins SmartQueue uniquement"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_super_admin


class IsTicketOwner(permissions.BasePermission):
    """Permission pour le propriétaire du ticket"""
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        return obj.customer == request.user


class IsTicketOwnerOrStaff(permissions.BasePermission):
    """Permission pour le propriétaire du ticket ou le staff de l'organisation"""
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Propriétaire du ticket
        if obj.customer == user:
            return True
        
        # Super admin
        if user.is_super_admin:
            return True
        
        # Staff de l'organisation
        if hasattr(user, 'staff_profile'):
            return user.staff_profile.organization == obj.queue.organization
        
        return False


class IsOrganizationStaff(permissions.BasePermission):
    """Permission pour le staff de l'organisation"""
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Super admin
        if user.is_super_admin:
            return True
        
        # Staff de l'organisation
        if hasattr(user, 'staff_profile'):
            return user.staff_profile.organization == obj.queue.organization
        
        return False


# ==============================================
# VIEWSETS SUPPLÉMENTAIRES
# ==============================================

class PublicTicketViewSet(viewsets.GenericViewSet):
    """
    ViewSet public pour prendre des tickets (sans authentification)
    
    Usage : Bornes tactiles, prise de ticket rapide
    POST /api/public/tickets/
    """
    queryset = Ticket.objects.none()  # Pas de liste publique
    serializer_class = TicketCreateSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_permissions(self):
        """Seule la création est autorisée"""
        if self.action == 'create':
            return [permissions.AllowAny()]
        else:
            return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        """Prise de ticket anonyme (bornes tactiles)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = serializer.save()
        
        return Response({
            'success': True,
            'ticket_number': ticket.ticket_number,
            'queue_name': ticket.queue.name,
            'service_name': ticket.service.name,
            'queue_position': ticket.queue_position,
            'estimated_wait_time': ticket.queue.estimated_wait_time,
            'expires_at': ticket.expires_at,
            'message': f'Votre ticket {ticket.ticket_number} a été généré avec succès!'
        })
    
