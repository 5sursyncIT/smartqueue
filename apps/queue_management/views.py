# apps/queue_management/views.py
"""
Vues unifiées pour la gestion des Files d'attente et Tickets
Approche superviseur : logique métier cohérente avec géolocalisation intelligente
"""

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone

# Import depuis les modèles séparés
from .models import Queue, Ticket
from .serializers import (
    QueueCreateSerializer, QueueListSerializer, QueueDetailSerializer,
    TicketCreateSerializer, TicketListSerializer, TicketDetailSerializer
)

# ============================================
# VUES QUEUES (FILES D'ATTENTE)
# ============================================

@api_view(['GET', 'POST'])
def queue_list_create_view(request):
    """Liste et création de files d'attente - Custom view pour contrôle ID"""
    if request.method == 'POST':
        serializer = QueueCreateSerializer(data=request.data)
        if serializer.is_valid():
            queue = serializer.save()
            response_data = {
                'id': queue.id,
                'name': queue.name,
                'queue_type': queue.queue_type,
                'current_status': queue.current_status
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # GET - Liste des files
    queues = Queue.objects.filter(is_active=True)
    
    # Filtrage basique par paramètres GET
    organization = request.GET.get('organization')
    service = request.GET.get('service')
    queue_type = request.GET.get('queue_type')
    current_status = request.GET.get('current_status')
    
    if organization:
        queues = queues.filter(organization=organization)
    if service:
        queues = queues.filter(service=service) 
    if queue_type:
        queues = queues.filter(queue_type=queue_type)
    if current_status:
        queues = queues.filter(current_status=current_status)
        
    serializer = QueueListSerializer(queues, many=True)
    return Response(serializer.data)

class QueueDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression de file d'attente"""
    queryset = Queue.objects.filter(is_active=True)
    serializer_class = QueueDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

# ============================================
# VUES TICKETS
# ============================================

class TicketListCreateView(generics.ListCreateAPIView):
    """Liste et création de tickets"""
    queryset = Ticket.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TicketCreateSerializer
        return TicketListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['queue', 'customer', 'status', 'priority']
    search_fields = ['ticket_number', 'customer__first_name', 'customer__last_name']
    ordering_fields = ['created_at', 'queue_position', 'estimated_service_time']
    ordering = ['queue_position']

class TicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression de ticket"""
    queryset = Ticket.objects.all()
    serializer_class = TicketDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

# ============================================
# VUES RELATIONS (Queue -> Tickets)
# ============================================

class QueueTicketsView(generics.ListAPIView):
    """Tickets d'une file d'attente spécifique"""
    serializer_class = TicketListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queue_id = self.kwargs['queue_id']
        return Ticket.objects.filter(
            queue_id=queue_id
        ).order_by('queue_position')

# ============================================
# VUES GÉOLOCALISATION INTELLIGENTE
# ============================================

@api_view(['GET'])
def queue_with_travel_time(request, queue_id):
    """File d'attente avec calcul temps de trajet intelligent"""
    try:
        queue = Queue.objects.get(id=queue_id, is_active=True)
        
        # Informations de base de la file
        queue_data = QueueDetailSerializer(queue).data
        
        # Si utilisateur connecté et géolocalisation disponible
        if request.user.is_authenticated and hasattr(request.user, 'current_location'):
            user_location = request.user.current_location
            org_location = queue.organization
            
            # Calculer temps de trajet avec géolocalisation intelligente
            try:
                from apps.locations.services import SmartTravelTimeCalculator
                calculator = SmartTravelTimeCalculator()
                
                travel_data = calculator.calculate_travel_time(
                    origin_lat=float(user_location.latitude),
                    origin_lng=float(user_location.longitude),
                    dest_lat=float(org_location.latitude),
                    dest_lng=float(org_location.longitude),
                    transport_mode=user_location.transport_mode,
                    user=request.user,
                    organization=org_location
                )
                
                queue_data['intelligent_travel'] = travel_data
                
                # Recommandation heure de départ
                if 'total_time_minutes' in travel_data:
                    est_wait = queue.get_estimated_wait_time()
                    service_time = timezone.now() + timezone.timedelta(minutes=est_wait)
                    travel_time = timezone.timedelta(minutes=travel_data['total_time_minutes'])
                    departure_time = service_time - travel_time - timezone.timedelta(minutes=10)  # 10min marge
                    
                    queue_data['recommended_departure'] = departure_time
                    queue_data['estimated_service_time'] = service_time
                
            except Exception as e:
                queue_data['travel_error'] = str(e)
        
        return Response(queue_data)
        
    except Queue.DoesNotExist:
        return Response({'error': 'File non trouvée'}, status=404)

# ============================================
# ACTIONS SUR TICKETS
# ============================================

@api_view(['POST'])
def take_ticket(request, queue_id):
    """Prendre un ticket dans une file - avec géolocalisation intelligente"""
    try:
        queue = Queue.objects.get(id=queue_id, is_active=True, current_status='active')
        user = request.user
        
        # Vérifier si utilisateur peut prendre un ticket
        existing_ticket = Ticket.objects.filter(
            customer=user,
            queue=queue,
            status__in=['waiting', 'called', 'serving']
        ).first()
        
        if existing_ticket:
            return Response({
                'error': 'Vous avez déjà un ticket actif dans cette file',
                'existing_ticket': TicketListSerializer(existing_ticket).data
            }, status=400)
        
        # Créer le ticket
        ticket = Ticket.objects.create(
            customer=user,
            queue=queue,
            service=queue.service,
            creation_channel=request.data.get('channel', 'web'),
            priority=request.data.get('priority', 'low')
        )
        
        # Déclencher géolocalisation intelligente si disponible
        if hasattr(user, 'current_location'):
            try:
                from apps.locations.tasks import calculate_travel_estimates_for_active_tickets
                calculate_travel_estimates_for_active_tickets.delay()
            except:
                pass  # Pas grave si Celery n'est pas disponible
        
        return Response({
            'success': True,
            'message': 'Ticket créé avec succès!',
            'ticket': TicketDetailSerializer(ticket).data
        })
        
    except Queue.DoesNotExist:
        return Response({'error': 'File non trouvée ou fermée'}, status=404)

@api_view(['POST'])
def call_next_ticket(request, queue_id):
    """Appeler le prochain ticket dans la file"""
    try:
        queue = Queue.objects.get(id=queue_id, is_active=True)
        
        # Vérifier permissions
        if not request.user.user_type in ['staff', 'admin', 'super_admin']:
            return Response({'error': 'Permission refusée'}, status=403)
        
        # Trouver le prochain ticket
        next_ticket = Ticket.objects.filter(
            queue=queue,
            status='waiting'
        ).order_by('queue_position').first()
        
        if not next_ticket:
            return Response({'message': 'Aucun ticket en attente'}, status=200)
        
        # Changer statut
        next_ticket.status = 'called'
        next_ticket.called_at = timezone.now()
        next_ticket.save()
        
        return Response({
            'success': True,
            'message': f'Ticket {next_ticket.ticket_number} appelé',
            'ticket': TicketDetailSerializer(next_ticket).data
        })
        
    except Queue.DoesNotExist:
        return Response({'error': 'File non trouvée'}, status=404)

# ============================================
# INTERFACE AGENT (GESTION FILES)
# ============================================

@api_view(['GET'])
def agent_dashboard(request, queue_id):
    """Dashboard agent pour gestion d'une file d'attente"""
    try:
        queue = Queue.objects.get(id=queue_id, is_active=True)

        # Vérifier permissions agent
        if not request.user.user_type in ['staff', 'admin', 'super_admin']:
            return Response({'error': 'Permission refusée'}, status=403)

        # Données dashboard
        dashboard_data = {
            'queue': QueueDetailSerializer(queue).data,
            'tickets_waiting': Ticket.objects.filter(
                queue=queue, status='waiting'
            ).count(),
            'current_ticket': None,
            'next_tickets': [],
            'today_stats': {
                'served': Ticket.objects.filter(
                    queue=queue,
                    status='served',
                    created_at__date=timezone.now().date()
                ).count(),
                'cancelled': Ticket.objects.filter(
                    queue=queue,
                    status='cancelled',
                    created_at__date=timezone.now().date()
                ).count(),
                'no_show': Ticket.objects.filter(
                    queue=queue,
                    status='no_show',
                    created_at__date=timezone.now().date()
                ).count()
            }
        }

        # Ticket actuellement appelé/servi
        current = Ticket.objects.filter(
            queue=queue,
            status__in=['called', 'serving']
        ).first()
        if current:
            dashboard_data['current_ticket'] = TicketDetailSerializer(current).data

        # Prochains tickets en attente
        next_tickets = Ticket.objects.filter(
            queue=queue,
            status='waiting'
        ).order_by('queue_position')[:5]
        dashboard_data['next_tickets'] = TicketListSerializer(next_tickets, many=True).data

        return Response(dashboard_data)

    except Queue.DoesNotExist:
        return Response({'error': 'File non trouvée'}, status=404)

@api_view(['POST'])
def mark_ticket_served(request, ticket_id):
    """Marquer un ticket comme servi"""
    try:
        ticket = Ticket.objects.get(id=ticket_id)

        # Vérifier permissions agent
        if not request.user.user_type in ['staff', 'admin', 'super_admin']:
            return Response({'error': 'Permission refusée'}, status=403)

        # Vérifier statut valide
        if ticket.status not in ['called', 'serving']:
            return Response({
                'error': 'Ticket doit être appelé ou en cours de service'
            }, status=400)

        # Marquer comme servi
        ticket.status = 'served'
        ticket.service_ended_at = timezone.now()
        ticket.save()

        return Response({
            'success': True,
            'message': f'Ticket {ticket.ticket_number} marqué comme servi',
            'ticket': TicketDetailSerializer(ticket).data
        })

    except Ticket.DoesNotExist:
        return Response({'error': 'Ticket non trouvé'}, status=404)

@api_view(['POST'])
def change_queue_status(request, queue_id):
    """Changer le statut d'une file (pause, reprise, fermeture)"""
    try:
        queue = Queue.objects.get(id=queue_id, is_active=True)

        # Vérifier permissions agent
        if not request.user.user_type in ['staff', 'admin', 'super_admin']:
            return Response({'error': 'Permission refusée'}, status=403)

        new_status = request.data.get('status')
        valid_statuses = ['active', 'paused', 'closed', 'maintenance']

        if new_status not in valid_statuses:
            return Response({
                'error': f'Statut invalide. Valeurs possibles: {valid_statuses}'
            }, status=400)

        old_status = queue.current_status
        queue.current_status = new_status
        queue.save()

        return Response({
            'success': True,
            'message': f'File {queue.name} changée de {old_status} à {new_status}',
            'queue': QueueDetailSerializer(queue).data
        })

    except Queue.DoesNotExist:
        return Response({'error': 'File non trouvée'}, status=404)

@api_view(['GET'])
def queue_agent_stats(request, queue_id):
    """Statistiques détaillées pour agent d'une file"""
    try:
        queue = Queue.objects.get(id=queue_id, is_active=True)

        # Vérifier permissions agent
        if not request.user.user_type in ['staff', 'admin', 'super_admin']:
            return Response({'error': 'Permission refusée'}, status=403)

        today = timezone.now().date()

        stats = {
            'queue_name': queue.name,
            'current_status': queue.current_status,
            'today': {
                'total_tickets': Ticket.objects.filter(
                    queue=queue,
                    created_at__date=today
                ).count(),
                'served': Ticket.objects.filter(
                    queue=queue,
                    status='served',
                    created_at__date=today
                ).count(),
                'waiting': Ticket.objects.filter(
                    queue=queue,
                    status='waiting'
                ).count(),
                'cancelled': Ticket.objects.filter(
                    queue=queue,
                    status='cancelled',
                    created_at__date=today
                ).count(),
                'no_show': Ticket.objects.filter(
                    queue=queue,
                    status='no_show',
                    created_at__date=today
                ).count()
            },
            'capacity': {
                'max_capacity': queue.max_capacity,
                'current_usage': Ticket.objects.filter(
                    queue=queue,
                    status__in=['waiting', 'called', 'serving']
                ).count()
            },
            'timing': {
                'estimated_wait_per_person': queue.estimated_wait_time_per_person,
                'total_estimated_wait': queue.get_estimated_wait_time() if hasattr(queue, 'get_estimated_wait_time') else 0
            }
        }

        # Pourcentage d'utilisation capacité
        if queue.max_capacity and queue.max_capacity > 0:
            stats['capacity']['usage_percentage'] = round(
                (stats['capacity']['current_usage'] / queue.max_capacity) * 100, 1
            )
        else:
            stats['capacity']['usage_percentage'] = 0

        # Taux de réussite
        total_processed = stats['today']['served'] + stats['today']['cancelled'] + stats['today']['no_show']
        if total_processed > 0:
            stats['today']['success_rate'] = round(
                (stats['today']['served'] / total_processed) * 100, 1
            )
        else:
            stats['today']['success_rate'] = 0

        return Response(stats)

    except Queue.DoesNotExist:
        return Response({'error': 'File non trouvée'}, status=404)

# ============================================
# STATISTIQUES
# ============================================

@api_view(['GET'])
def queue_management_stats(request):
    """Statistiques générales queue management"""
    stats = {
        'total_queues': Queue.objects.filter(is_active=True).count(),
        'active_queues': Queue.objects.filter(current_status='active').count(),
        'total_tickets_today': Ticket.objects.filter(
            created_at__date=timezone.now().date()
        ).count(),
        'tickets_waiting': Ticket.objects.filter(status='waiting').count(),
        'tickets_being_served': Ticket.objects.filter(status='serving').count()
    }

    return Response(stats)