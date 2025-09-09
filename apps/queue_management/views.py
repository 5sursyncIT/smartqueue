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