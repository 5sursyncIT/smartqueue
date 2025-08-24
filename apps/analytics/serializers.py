# apps/analytics/serializers.py
"""
Serializers pour les analytics SmartQueue Sénégal
APIs pour métriques et tableaux de bord
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .models import (
    OrganizationMetrics, ServiceMetrics, QueueMetrics, 
    CustomerSatisfaction, DashboardWidget
)


class OrganizationMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les métriques d'organisation
    
    Usage : GET /api/analytics/organization-metrics/
    """
    
    organization_name = serializers.CharField(
        source='organization.name', 
        read_only=True
    )
    
    success_rate = serializers.ReadOnlyField()
    cancellation_rate = serializers.ReadOnlyField()
    no_show_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = OrganizationMetrics
        fields = [
            'id', 'uuid', 'organization', 'organization_name', 'date',
            # Tickets
            'tickets_issued', 'tickets_served', 'tickets_cancelled', 
            'tickets_expired', 'tickets_no_show',
            # Rendez-vous
            'appointments_created', 'appointments_completed', 
            'appointments_cancelled', 'appointments_no_show',
            # Temps
            'avg_wait_time', 'max_wait_time', 'avg_service_time',
            # Satisfaction
            'total_ratings', 'avg_rating',
            # Affluence
            'peak_hour_start', 'peak_hour_end', 'max_concurrent_customers',
            # Revenus
            'total_revenue',
            # Propriétés calculées
            'success_rate', 'cancellation_rate', 'no_show_rate',
            # Métadonnées
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class ServiceMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les métriques de service
    """
    
    service_name = serializers.CharField(
        source='service.name', 
        read_only=True
    )
    
    organization_name = serializers.CharField(
        source='organization.name', 
        read_only=True
    )
    
    avg_wait_time = serializers.ReadOnlyField()
    avg_service_time = serializers.ReadOnlyField()
    avg_rating = serializers.ReadOnlyField()
    
    class Meta:
        model = ServiceMetrics
        fields = [
            'id', 'uuid', 'service', 'service_name', 
            'organization', 'organization_name', 'date',
            # Métriques de base
            'tickets_issued', 'tickets_served', 'tickets_cancelled',
            # Temps
            'total_wait_time', 'total_service_time',
            'avg_wait_time', 'avg_service_time',
            # Revenus
            'revenue',
            # Satisfaction
            'total_ratings', 'total_rating_score', 'avg_rating',
            # Métadonnées
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class QueueMetricsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les métriques de files d'attente
    """
    
    queue_name = serializers.CharField(
        source='queue.name', 
        read_only=True
    )
    
    service_name = serializers.CharField(
        source='queue.service.name', 
        read_only=True
    )
    
    organization_name = serializers.CharField(
        source='queue.organization.name', 
        read_only=True
    )
    
    class Meta:
        model = QueueMetrics
        fields = [
            'id', 'queue', 'queue_name', 'service_name', 
            'organization_name', 'timestamp',
            # Métriques instantanées
            'waiting_customers', 'current_wait_time',
            'tickets_issued_hour', 'tickets_served_hour',
            # État
            'queue_status',
            # Métadonnées
            'created_at'
        ]
        read_only_fields = ['created_at']


class CustomerSatisfactionSerializer(serializers.ModelSerializer):
    """
    Serializer pour les évaluations de satisfaction
    """
    
    customer_name = serializers.CharField(
        source='customer.get_full_name', 
        read_only=True
    )
    
    organization_name = serializers.CharField(
        source='organization.name', 
        read_only=True
    )
    
    service_name = serializers.CharField(
        source='service.name', 
        read_only=True
    )
    
    ticket_number = serializers.CharField(
        source='ticket.ticket_number', 
        read_only=True
    )
    
    class Meta:
        model = CustomerSatisfaction
        fields = [
            'id', 'uuid', 'customer', 'customer_name',
            'organization', 'organization_name',
            'service', 'service_name',
            'ticket', 'ticket_number', 'appointment',
            # Évaluation principale
            'rating', 'comment',
            # Critères détaillés
            'wait_time_rating', 'service_quality_rating', 
            'staff_friendliness_rating',
            # Métadonnées
            'created_at'
        ]
        read_only_fields = ['uuid', 'customer', 'created_at']
        extra_kwargs = {
            'rating': {'help_text': 'Note de 1 à 5'},
            'comment': {'required': False}
        }
    
    def validate_rating(self, value):
        """Valider que la note est entre 1 et 5"""
        if not (1 <= value <= 5):
            raise serializers.ValidationError(
                "La note doit être entre 1 et 5"
            )
        return value


class CustomerSatisfactionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer une évaluation de satisfaction
    """
    
    class Meta:
        model = CustomerSatisfaction
        fields = [
            'organization', 'service', 'ticket', 'appointment',
            'rating', 'comment',
            'wait_time_rating', 'service_quality_rating', 
            'staff_friendliness_rating'
        ]
        extra_kwargs = {
            'rating': {'required': True, 'help_text': 'Note de 1 à 5'},
            'comment': {'required': False, 'allow_blank': True},
            'organization': {'required': True},
            'service': {'required': True}
        }
    
    def validate(self, attrs):
        """Valider qu'au moins un objet (ticket ou RDV) est fourni"""
        ticket = attrs.get('ticket')
        appointment = attrs.get('appointment')
        
        if not ticket and not appointment:
            raise serializers.ValidationError(
                "Vous devez spécifier soit un ticket soit un rendez-vous"
            )
        
        if ticket and appointment:
            raise serializers.ValidationError(
                "Vous ne pouvez pas évaluer un ticket ET un rendez-vous simultanément"
            )
        
        return attrs
    
    def validate_rating(self, value):
        """Valider la note principale"""
        if not (1 <= value <= 5):
            raise serializers.ValidationError(
                "La note doit être entre 1 et 5"
            )
        return value
    
    def validate_wait_time_rating(self, value):
        """Valider la note temps d'attente"""
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError(
                "La note temps d'attente doit être entre 1 et 5"
            )
        return value
    
    def validate_service_quality_rating(self, value):
        """Valider la note qualité service"""
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError(
                "La note qualité service doit être entre 1 et 5"
            )
        return value
    
    def validate_staff_friendliness_rating(self, value):
        """Valider la note amabilité personnel"""
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError(
                "La note amabilité personnel doit être entre 1 et 5"
            )
        return value


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """
    Serializer pour les widgets de dashboard
    """
    
    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'user', 'title', 'widget_type',
            # Disposition
            'position_x', 'position_y', 'width', 'height',
            # Configuration
            'data_source', 'filters', 'display_options',
            # État
            'is_visible',
            # Métadonnées
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at', 'updated_at']
        extra_kwargs = {
            'filters': {'default': dict},
            'display_options': {'default': dict}
        }


class KPICardSerializer(serializers.Serializer):
    """
    Serializer pour les cartes KPI du dashboard
    """
    
    title = serializers.CharField()
    value = serializers.DecimalField(max_digits=15, decimal_places=2)
    unit = serializers.CharField(required=False)
    change = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        required=False
    )
    change_percent = serializers.DecimalField(
        max_digits=5, 
        decimal_places=1, 
        required=False
    )
    trend = serializers.ChoiceField(
        choices=['up', 'down', 'stable'],
        required=False
    )
    color = serializers.ChoiceField(
        choices=['success', 'warning', 'danger', 'info', 'primary'],
        required=False,
        default='primary'
    )
    icon = serializers.CharField(required=False)


class DashboardDataSerializer(serializers.Serializer):
    """
    Serializer pour les données du dashboard principal
    """
    
    date = serializers.DateField()
    organizations_count = serializers.IntegerField()
    
    # KPIs principaux
    tickets_today = serializers.DictField()
    tickets_evolution = serializers.DictField()
    appointments_today = serializers.DictField()
    avg_wait_time = serializers.DecimalField(max_digits=8, decimal_places=1)
    avg_satisfaction = serializers.DecimalField(max_digits=3, decimal_places=1)
    active_queues = serializers.IntegerField()
    daily_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    # Tendances
    week_trends = serializers.DictField()
    top_services = serializers.ListField()
    peak_hours = serializers.DictField()


class RealtimeMetricsSerializer(serializers.Serializer):
    """
    Serializer pour les métriques temps réel
    """
    
    timestamp = serializers.DateTimeField()
    
    summary = serializers.DictField()
    queues = serializers.ListField(
        child=serializers.DictField()
    )


class CustomReportSerializer(serializers.Serializer):
    """
    Serializer pour les rapports personnalisés
    """
    
    type = serializers.ChoiceField(
        choices=['organization', 'service', 'queue'],
        default='organization'
    )
    
    date_from = serializers.DateField(
        help_text='Date de début (YYYY-MM-DD)'
    )
    
    date_to = serializers.DateField(
        help_text='Date de fin (YYYY-MM-DD)'
    )
    
    organization_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text='IDs des organisations à inclure'
    )
    
    service_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list,
        help_text='IDs des services à inclure'
    )
    
    metrics = serializers.ListField(
        child=serializers.CharField(),
        default=['tickets_issued', 'tickets_served', 'avg_wait_time'],
        help_text='Métriques à inclure dans le rapport'
    )
    
    def validate(self, attrs):
        """Validation des dates"""
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')
        
        if date_from and date_to:
            if date_from > date_to:
                raise serializers.ValidationError(
                    "La date de début doit être antérieure à la date de fin"
                )
            
            # Limite à 1 an maximum
            if (date_to - date_from).days > 365:
                raise serializers.ValidationError(
                    "La période ne peut pas dépasser 1 an"
                )
        
        return attrs


class SatisfactionStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques de satisfaction
    """
    
    period_days = serializers.IntegerField()
    total_ratings = serializers.IntegerField()
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    
    rating_distribution = serializers.DictField()
    criteria_stats = serializers.DictField()
    best_services = serializers.ListField()
    worst_services = serializers.ListField()
    weekly_evolution = serializers.ListField()