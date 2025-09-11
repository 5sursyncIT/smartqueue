# apps/analytics/views.py
"""
Vues pour les analytics SmartQueue Sénégal
APIs pour métriques, KPIs et tableaux de bord
"""

from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.db.models import Avg, Sum, Count, Max, Min, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from decimal import Decimal

from .models import (
    OrganizationMetrics, ServiceMetrics, QueueMetrics, 
    CustomerSatisfaction, DashboardWidget
)
from .serializers import (
    OrganizationMetricsSerializer, ServiceMetricsSerializer, 
    QueueMetricsSerializer, CustomerSatisfactionSerializer
)
from apps.business.models import Organization, Service
from apps.queue_management.models import Queue, Ticket
from apps.appointments.models import Appointment


@extend_schema_view(
    list=extend_schema(
        summary="Métriques des organisations",
        description="Récupère les métriques quotidiennes des organisations",
        tags=["Analytics"]
    ),
    retrieve=extend_schema(
        summary="Détails métriques organisation",
        tags=["Analytics"]
    )
)
class OrganizationMetricsViewSet(ReadOnlyModelViewSet):
    """
    ViewSet pour les métriques d'organisations
    Lecture seule - les métriques sont calculées automatiquement
    """
    queryset = OrganizationMetrics.objects.all()
    serializer_class = OrganizationMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['organization', 'date']
    ordering = ['-date']
    
    def get_queryset(self):
        """Filtrer selon les permissions utilisateur"""
        user = self.request.user
        
        if user.user_type == 'super_admin':
            return OrganizationMetrics.objects.all()
        elif user.user_type == 'admin':
            # Admin voit seulement son organisation
            return OrganizationMetrics.objects.filter(
                organization=user.organization
            )
        elif user.user_type == 'staff':
            # Staff voit son organisation
            return OrganizationMetrics.objects.filter(
                organization=user.organization
            )
        else:
            # Clients ne voient pas les métriques internes
            return OrganizationMetrics.objects.none()


@extend_schema_view(
    list=extend_schema(
        summary="Métriques des services",
        description="Performance détaillée par service",
        tags=["Analytics"]
    )
)
class ServiceMetricsViewSet(ReadOnlyModelViewSet):
    """
    ViewSet pour les métriques de services
    """
    queryset = ServiceMetrics.objects.all()
    serializer_class = ServiceMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['service', 'organization', 'date']
    ordering = ['-date']
    
    def get_queryset(self):
        """Filtrer selon les permissions"""
        user = self.request.user
        
        if user.user_type == 'super_admin':
            return ServiceMetrics.objects.all()
        elif user.user_type == 'admin':
            return ServiceMetrics.objects.filter(
                organization=user.organization
            )
        elif user.user_type == 'staff':
            return ServiceMetrics.objects.filter(
                organization=user.organization
            )
        else:
            return ServiceMetrics.objects.none()


@extend_schema_view(
    list=extend_schema(
        summary="Métriques des files d'attente",
        description="Suivi horaire de l'affluence par file",
        tags=["Analytics"]
    )
)
class QueueMetricsViewSet(ReadOnlyModelViewSet):
    """
    ViewSet pour les métriques de files d'attente
    """
    queryset = QueueMetrics.objects.all()
    serializer_class = QueueMetricsSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['queue', 'queue_status', 'timestamp']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        """Filtrer selon les permissions"""
        user = self.request.user
        
        if user.user_type == 'super_admin':
            return QueueMetrics.objects.all()
        elif user.user_type == 'admin':
            return QueueMetrics.objects.filter(
                queue__organization__in=Organization.objects.filter(id=user.organization.id)
            )
        elif user.user_type == 'staff':
            return QueueMetrics.objects.filter(
                queue__organization=user.organization
            )
        else:
            return QueueMetrics.objects.none()


@extend_schema_view(
    list=extend_schema(
        summary="Évaluations satisfaction client",
        description="Notes et commentaires des clients",
        tags=["Analytics"]
    ),
    create=extend_schema(
        summary="Soumettre une évaluation",
        description="Client évalue son expérience",
        tags=["Analytics"]
    )
)
class CustomerSatisfactionViewSet(ModelViewSet):
    """
    ViewSet pour les évaluations de satisfaction
    """
    queryset = CustomerSatisfaction.objects.all()
    serializer_class = CustomerSatisfactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['organization', 'service', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrer selon les permissions et type d'utilisateur"""
        user = self.request.user
        
        if user.user_type == 'super_admin':
            return CustomerSatisfaction.objects.all()
        elif user.user_type == 'admin':
            return CustomerSatisfaction.objects.filter(
                organization__in=Organization.objects.filter(id=user.organization.id)
            )
        elif user.user_type == 'staff':
            return CustomerSatisfaction.objects.filter(
                organization=user.organization
            )
        elif user.user_type == 'customer':
            # Clients voient seulement leurs propres évaluations
            return CustomerSatisfaction.objects.filter(customer=user)
        else:
            return CustomerSatisfaction.objects.none()
    
    def perform_create(self, serializer):
        """Associer l'évaluation au client connecté"""
        serializer.save(customer=self.request.user)


@extend_schema(
    summary="Dashboard principal",
    description="KPIs et métriques principales pour tableau de bord",
    tags=["Analytics", "Dashboard"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard_overview(request):
    """
    Vue principale du dashboard avec KPIs essentiels
    GET /api/analytics/dashboard/
    """
    user = request.user
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)
    
    # Filtrer selon les permissions
    if user.user_type == 'super_admin':
        organizations = Organization.objects.all()
    elif user.user_type == 'admin':
        organizations = Organization.objects.filter(id=user.organization.id)
    elif user.user_type == 'staff':
        organizations = Organization.objects.filter(id=user.organization.id)
    else:
        return Response(
            {'error': 'Accès non autorisé au dashboard'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Calculer les KPIs
    kpis = {}
    
    # Tickets aujourd'hui
    tickets_today = Ticket.objects.filter(
        queue__organization__in=organizations,
        created_at__date=today
    )
    
    kpis['tickets_today'] = {
        'total': tickets_today.count(),
        'served': tickets_today.filter(status='served').count(),
        'waiting': tickets_today.filter(status='waiting').count(),
        'cancelled': tickets_today.filter(status='cancelled').count(),
    }
    
    # Évolution vs hier
    tickets_yesterday = Ticket.objects.filter(
        queue__organization__in=organizations,
        created_at__date=yesterday
    ).count()
    
    kpis['tickets_evolution'] = {
        'yesterday': tickets_yesterday,
        'change': kpis['tickets_today']['total'] - tickets_yesterday,
        'change_percent': (
            (kpis['tickets_today']['total'] - tickets_yesterday) / tickets_yesterday * 100
            if tickets_yesterday > 0 else 0
        )
    }
    
    # RDV aujourd'hui
    appointments_today = Appointment.objects.filter(
        organization__in=organizations,
        scheduled_date=today
    )
    
    kpis['appointments_today'] = {
        'total': appointments_today.count(),
        'completed': appointments_today.filter(status='completed').count(),
        'confirmed': appointments_today.filter(status='confirmed').count(),
        'cancelled': appointments_today.filter(status='cancelled').count(),
    }
    
    # Temps d'attente moyen
    avg_wait_times = OrganizationMetrics.objects.filter(
        organization__in=organizations,
        date=today
    ).aggregate(avg_wait=Avg('avg_wait_time'))
    
    kpis['avg_wait_time'] = avg_wait_times['avg_wait'] or 0
    
    # Satisfaction moyenne
    avg_satisfaction = CustomerSatisfaction.objects.filter(
        organization__in=organizations,
        created_at__date=today
    ).aggregate(avg_rating=Avg('rating'))
    
    kpis['avg_satisfaction'] = avg_satisfaction['avg_rating'] or 0
    
    # Files actives
    active_queues = Queue.objects.filter(
        organization__in=organizations,
        current_status='active'
    ).count()
    
    kpis['active_queues'] = active_queues
    
    # Revenus du jour (si applicable)
    daily_revenue = OrganizationMetrics.objects.filter(
        organization__in=organizations,
        date=today
    ).aggregate(total_revenue=Sum('total_revenue'))
    
    kpis['daily_revenue'] = daily_revenue['total_revenue'] or Decimal('0.00')
    
    # Tendances sur 7 jours
    week_metrics = OrganizationMetrics.objects.filter(
        organization__in=organizations,
        date__gte=last_week
    ).aggregate(
        total_tickets=Sum('tickets_issued'),
        avg_wait_time=Avg('avg_wait_time'),
        avg_satisfaction=Avg('avg_rating')
    )
    
    kpis['week_trends'] = {
        'total_tickets': week_metrics['total_tickets'] or 0,
        'avg_wait_time': week_metrics['avg_wait_time'] or 0,
        'avg_satisfaction': week_metrics['avg_satisfaction'] or 0,
    }
    
    # Top 5 services les plus utilisés
    top_services = ServiceMetrics.objects.filter(
        organization__in=organizations,
        date__gte=last_week
    ).values('service__name').annotate(
        total_tickets=Sum('tickets_issued')
    ).order_by('-total_tickets')[:5]
    
    kpis['top_services'] = list(top_services)
    
    # Heures de pointe (plus communes)
    peak_hours_data = OrganizationMetrics.objects.filter(
        organization__in=organizations,
        date__gte=last_week,
        peak_hour_start__isnull=False
    ).values_list('peak_hour_start', 'peak_hour_end')
    
    # Calculer manuellement les heures les plus communes (contournement SQLite)
    if peak_hours_data:
        peak_starts = [ph[0] for ph in peak_hours_data if ph[0]]
        peak_ends = [ph[1] for ph in peak_hours_data if ph[1]]
        
        # Heure de début la plus commune
        most_common_start = max(set(peak_starts), key=peak_starts.count) if peak_starts else None
        most_common_end = max(set(peak_ends), key=peak_ends.count) if peak_ends else None
        
        peak_hours = {
            'most_common_start': most_common_start,
            'most_common_end': most_common_end
        }
    else:
        peak_hours = {
            'most_common_start': None,
            'most_common_end': None
        }
    
    kpis['peak_hours'] = peak_hours
    
    return Response({
        'date': today,
        'organizations_count': organizations.count(),
        'kpis': kpis
    })


@extend_schema(
    summary="Métriques temps réel",
    description="État actuel de toutes les files d'attente",
    tags=["Analytics", "Real-time"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def realtime_metrics(request):
    """
    Métriques en temps réel pour monitoring
    GET /api/analytics/realtime/
    """
    user = request.user
    
    # Filtrer organisations selon permissions
    if user.user_type == 'super_admin':
        organizations = Organization.objects.all()
    elif user.user_type == 'admin':
        organizations = Organization.objects.filter(id=user.organization.id)
    elif user.user_type == 'staff':
        organizations = Organization.objects.filter(id=user.organization.id)
    else:
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    # État actuel des files
    active_queues = Queue.objects.filter(
        organization__in=organizations,
        is_active=True
    ).select_related('organization', 'service')
    
    queues_status = []
    for queue in active_queues:
        # Tickets en attente
        waiting_tickets = Ticket.objects.filter(
            queue=queue,
            status='waiting'
        ).count()
        
        # Dernier ticket appelé
        current_ticket = Ticket.objects.filter(
            queue=queue,
            status='called'
        ).first()
        
        # Temps d'attente estimé
        estimated_wait = waiting_tickets * queue.service.estimated_duration
        
        queues_status.append({
            'queue_id': queue.id,
            'queue_name': queue.name,
            'organization': queue.organization.name,
            'service': queue.service.name,
            'status': queue.current_status,
            'waiting_tickets': waiting_tickets,
            'current_ticket': current_ticket.ticket_number if current_ticket else None,
            'estimated_wait_minutes': estimated_wait,
            'last_ticket_number': queue.last_ticket_number,
            'max_capacity': queue.max_capacity,
            'is_full': queue.max_capacity > 0 and waiting_tickets >= queue.max_capacity
        })
    
    # Statistiques globales temps réel
    total_waiting = sum(q['waiting_tickets'] for q in queues_status)
    avg_wait_time = sum(q['estimated_wait_minutes'] for q in queues_status) / len(queues_status) if queues_status else 0
    full_queues = len([q for q in queues_status if q['is_full']])
    
    return Response({
        'timestamp': timezone.now(),
        'summary': {
            'active_queues': len(queues_status),
            'total_waiting_customers': total_waiting,
            'avg_wait_time_minutes': round(avg_wait_time, 1),
            'full_queues': full_queues
        },
        'queues': queues_status
    })


@extend_schema(
    summary="Rapports personnalisés",
    description="Génère des rapports sur mesure avec filtres",
    tags=["Analytics", "Reports"]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def custom_report(request):
    """
    Génération de rapports personnalisés
    POST /api/analytics/reports/custom/
    """
    data = request.data
    
    # Paramètres du rapport
    report_type = data.get('type', 'organization')  # organization, service, queue
    date_from = data.get('date_from')
    date_to = data.get('date_to')
    organization_ids = data.get('organization_ids', [])
    service_ids = data.get('service_ids', [])
    metrics = data.get('metrics', ['tickets_issued', 'tickets_served', 'avg_wait_time'])
    
    # Validation dates
    if not date_from or not date_to:
        return Response(
            {'error': 'date_from et date_to sont requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
    except ValueError:
        return Response(
            {'error': 'Format de date invalide (YYYY-MM-DD)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Filtrer selon permissions
    user = request.user
    if user.user_type == 'super_admin':
        allowed_orgs = Organization.objects.all()
    elif user.user_type == 'admin':
        allowed_orgs = Organization.objects.filter(id=user.organization.id)
    elif user.user_type == 'staff':
        allowed_orgs = Organization.objects.filter(id=user.organization.id)
    else:
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    # Filtrer par organisations demandées
    if organization_ids:
        allowed_orgs = allowed_orgs.filter(id__in=organization_ids)
    
    # Générer le rapport selon le type
    if report_type == 'organization':
        report_data = OrganizationMetrics.objects.filter(
            organization__in=allowed_orgs,
            date__gte=date_from,
            date__lte=date_to
        ).select_related('organization')
        
        # Grouper par organisation
        report = {}
        for metric in report_data:
            org_name = metric.organization.name
            if org_name not in report:
                report[org_name] = []
            
            metric_data = {'date': metric.date}
            for field in metrics:
                if hasattr(metric, field):
                    metric_data[field] = getattr(metric, field)
            
            report[org_name].append(metric_data)
    
    elif report_type == 'service':
        report_data = ServiceMetrics.objects.filter(
            organization__in=allowed_orgs,
            date__gte=date_from,
            date__lte=date_to
        ).select_related('service', 'organization')
        
        if service_ids:
            report_data = report_data.filter(service_id__in=service_ids)
        
        # Grouper par service
        report = {}
        for metric in report_data:
            service_name = f"{metric.organization.name} - {metric.service.name}"
            if service_name not in report:
                report[service_name] = []
            
            metric_data = {'date': metric.date}
            for field in metrics:
                if hasattr(metric, field):
                    metric_data[field] = getattr(metric, field)
            
            report[service_name].append(metric_data)
    
    else:
        return Response(
            {'error': f'Type de rapport "{report_type}" non supporté'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    return Response({
        'report_type': report_type,
        'date_from': date_from,
        'date_to': date_to,
        'metrics': metrics,
        'data': report,
        'generated_at': timezone.now()
    })


@extend_schema(
    summary="Statistiques de satisfaction",
    description="Analyse détaillée de la satisfaction client",
    tags=["Analytics", "Satisfaction"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def satisfaction_stats(request):
    """
    Statistiques détaillées de satisfaction client
    GET /api/analytics/satisfaction/
    """
    user = request.user
    
    # Paramètres de filtre
    days = int(request.GET.get('days', 30))
    organization_id = request.GET.get('organization_id')
    service_id = request.GET.get('service_id')
    
    # Date limite
    date_from = timezone.now().date() - timedelta(days=days)
    
    # Filtrer selon permissions
    if user.user_type == 'super_admin':
        queryset = CustomerSatisfaction.objects.all()
    elif user.user_type == 'admin':
        queryset = CustomerSatisfaction.objects.filter(
            organization__in=Organization.objects.filter(id=user.organization.id)
        )
    elif user.user_type == 'staff':
        queryset = CustomerSatisfaction.objects.filter(
            organization=user.organization
        )
    else:
        return Response({'error': 'Accès non autorisé'}, status=403)
    
    # Appliquer filtres
    queryset = queryset.filter(created_at__date__gte=date_from)
    
    if organization_id:
        queryset = queryset.filter(organization_id=organization_id)
    
    if service_id:
        queryset = queryset.filter(service_id=service_id)
    
    # Calculer les statistiques
    total_ratings = queryset.count()
    
    if total_ratings == 0:
        return Response({
            'period_days': days,
            'total_ratings': 0,
            'message': 'Aucune évaluation trouvée pour cette période'
        })
    
    # Statistiques générales
    avg_rating = queryset.aggregate(avg=Avg('rating'))['avg']
    
    # Distribution des notes
    rating_distribution = {}
    for i in range(1, 6):
        count = queryset.filter(rating=i).count()
        percentage = (count / total_ratings) * 100
        rating_distribution[f'rating_{i}'] = {
            'count': count,
            'percentage': round(percentage, 1)
        }
    
    # Notes par critère
    criteria_stats = {
        'wait_time': queryset.exclude(wait_time_rating__isnull=True).aggregate(
            avg=Avg('wait_time_rating'),
            count=Count('wait_time_rating')
        ),
        'service_quality': queryset.exclude(service_quality_rating__isnull=True).aggregate(
            avg=Avg('service_quality_rating'),
            count=Count('service_quality_rating')
        ),
        'staff_friendliness': queryset.exclude(staff_friendliness_rating__isnull=True).aggregate(
            avg=Avg('staff_friendliness_rating'),
            count=Count('staff_friendliness_rating')
        ),
    }
    
    # Top/Bottom services par satisfaction
    service_ratings = queryset.values('service__name', 'organization__name').annotate(
        avg_rating=Avg('rating'),
        total_ratings=Count('rating')
    ).filter(total_ratings__gte=3).order_by('-avg_rating')
    
    best_services = list(service_ratings[:5])
    worst_services = list(service_ratings.order_by('avg_rating')[:5])
    
    # Évolution dans le temps (par semaine)
    weekly_evolution = []
    current_date = date_from
    while current_date <= timezone.now().date():
        week_end = min(current_date + timedelta(days=6), timezone.now().date())
        
        week_ratings = queryset.filter(
            created_at__date__gte=current_date,
            created_at__date__lte=week_end
        )
        
        if week_ratings.exists():
            weekly_evolution.append({
                'week_start': current_date,
                'week_end': week_end,
                'avg_rating': week_ratings.aggregate(avg=Avg('rating'))['avg'],
                'total_ratings': week_ratings.count()
            })
        
        current_date = week_end + timedelta(days=1)
    
    return Response({
        'period_days': days,
        'total_ratings': total_ratings,
        'avg_rating': round(avg_rating, 2),
        'rating_distribution': rating_distribution,
        'criteria_stats': criteria_stats,
        'best_services': best_services,
        'worst_services': worst_services,
        'weekly_evolution': weekly_evolution
    })
