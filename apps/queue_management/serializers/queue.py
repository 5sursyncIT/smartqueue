# apps/queues/serializers.py
"""
Serializers pour les files d'attente SmartQueue
Convertissent les modèles Python en JSON pour l'API REST
"""

from rest_framework import serializers
from ..models import Queue

class QueueCreateSerializer(serializers.ModelSerializer):
    """
    Serializer SIMPLE pour la CRÉATION de queues
    """
    
    class Meta:
        model = Queue
        fields = [
            'organization', 'service', 'name', 'queue_type', 'current_status'
        ]

class QueueListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la LISTE des files d'attente
    
    Usage : GET /api/queues/
    Affiche les infos essentielles (pas tous les détails)
    """
    
    # Champs calculés
    organization_name = serializers.CharField(
        source='organization.name', 
        read_only=True,
        help_text="Nom de l'organisation"
    )
    
    service_name = serializers.CharField(
        source='service.name', 
        read_only=True,
        help_text="Nom du service"
    )
    
    queue_type_display = serializers.CharField(
        source='get_queue_type_display', 
        read_only=True,
        help_text="Type de file lisible (ex: 'Normale' au lieu de 'normal')"
    )
    
    status_display = serializers.CharField(
        source='get_current_status_display', 
        read_only=True,
        help_text="Statut lisible (ex: 'Active' au lieu de 'active')"
    )
    
    processing_strategy_display = serializers.CharField(
        source='get_processing_strategy_display', 
        read_only=True,
        help_text="Stratégie lisible"
    )
    
    estimated_wait_time = serializers.ReadOnlyField(
        help_text="Temps d'attente estimé en minutes"
    )
    
    is_open = serializers.ReadOnlyField(
        help_text="La file est-elle ouverte ?"
    )
    
    class Meta:
        model = Queue
        fields = [
            # Identifiants
            'id', 'uuid', 'name',
            
            # Relations
            'organization_name', 'service_name',
            
            # Configuration de base
            'queue_type', 'queue_type_display', 'processing_strategy',
            'processing_strategy_display', 'max_capacity',
            
            # Statut
            'current_status', 'status_display', 'is_open',
            
            # Statistiques en temps réel
            'last_ticket_number', 'current_ticket_number', 
            'waiting_tickets_count', 'estimated_wait_time',
            
            # Statistiques du jour
            'daily_tickets_issued', 'daily_tickets_served',
            'daily_average_wait_time',
            
            # Configuration
            'max_wait_time', 'ticket_expiry_time',
            'notifications_enabled', 'is_active',
            
            # Métadonnées
            'created_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'organization_name', 'service_name',
            'queue_type_display', 'status_display', 'processing_strategy_display',
            'estimated_wait_time', 'is_open', 'last_ticket_number',
            'current_ticket_number', 'waiting_tickets_count',
            'daily_tickets_issued', 'daily_tickets_served',
            'daily_average_wait_time', 'created_at'
        ]


class QueueDetailSerializer(QueueListSerializer):
    """
    Serializer pour les DÉTAILS d'une file d'attente
    
    Usage : GET /api/queues/1/
    Affiche TOUTES les informations (version complète)
    """
    
    # Informations de l'organisation
    organization = serializers.SerializerMethodField(
        help_text="Détails de l'organisation"
    )
    
    # Informations du service
    service = serializers.SerializerMethodField(
        help_text="Détails du service"
    )
    
    # Tickets actifs
    active_tickets = serializers.SerializerMethodField(
        help_text="Liste des tickets en attente"
    )
    
    class Meta(QueueListSerializer.Meta):
        # Hérite de tous les champs de QueueListSerializer
        # + ajoute les champs détaillés
        fields = QueueListSerializer.Meta.fields + [
            # Configuration complète
            'description', 'opening_hours', 'notify_before_turns',
            
            # Relations complètes
            'organization', 'service',
            
            # Données temps réel
            'active_tickets',
            
            # Métadonnées complètes
            'stats_date', 'updated_at'
        ]
    
    def get_organization(self, obj):
        """
        Retourne les détails de l'organisation
        """
        if obj.organization:
            return {
                'id': obj.organization.id,
                'name': obj.organization.name,
                'type': obj.organization.type,
                'city': obj.organization.city,
                'region': obj.organization.region
            }
        return None
    
    def get_service(self, obj):
        """
        Retourne les détails du service
        """
        if obj.service:
            return {
                'id': obj.service.id,
                'name': obj.service.name,
                'code': obj.service.code,
                'estimated_duration': obj.service.estimated_duration,
                'allows_appointments': obj.service.allows_appointments
            }
        return None
    
    def get_active_tickets(self, obj):
        """
        Retourne les tickets en attente (les 10 prochains)
        """
        tickets = obj.tickets.filter(status='waiting').order_by('created_at')[:10]
        return [
            {
                'id': ticket.id,
                'number': ticket.number,
                'created_at': ticket.created_at,
                'priority': ticket.priority
            }
            for ticket in tickets
        ]


class QueueCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour CRÉER une nouvelle file d'attente
    
    Usage : POST /api/queues/
    Validation stricte + champs obligatoires
    """
    
    class Meta:
        model = Queue
        fields = [
            # Champs obligatoires pour création
            'service', 'organization', 'name', 'queue_type',
            
            # Champs optionnels
            'description', 'processing_strategy', 'max_capacity',
            'max_wait_time', 'ticket_expiry_time', 'opening_hours',
            'notifications_enabled', 'notify_before_turns'
        ]
    
    def validate_name(self, value):
        """
        Validation personnalisée du nom
        """
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Le nom doit contenir au moins 3 caractères."
            )
        return value.strip()
    
    def validate_max_capacity(self, value):
        """
        Validation de la capacité maximum
        """
        if value < 0:
            raise serializers.ValidationError(
                "La capacité ne peut pas être négative."
            )
        if value > 1000:
            raise serializers.ValidationError(
                "La capacité ne peut pas dépasser 1000 tickets."
            )
        return value
    
    def validate(self, attrs):
        """
        Validation globale (plusieurs champs ensemble)
        """
        service = attrs.get('service')
        organization = attrs.get('organization')
        queue_type = attrs.get('queue_type')
        
        # Vérifier que le service appartient à l'organisation
        if service and organization and service.organization != organization:
            raise serializers.ValidationError({
                'service': 'Le service sélectionné n\'appartient pas à cette organisation.'
            })
        
        # Vérifier unicité : une seule file par type pour un service
        if Queue.objects.filter(
            service=service,
            organization=organization,
            queue_type=queue_type
        ).exists():
            raise serializers.ValidationError({
                'queue_type': f'Une file de type "{queue_type}" existe déjà pour ce service.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """
        Logique de création personnalisée
        """
        # Générer un nom automatique si pas fourni
        if not validated_data.get('name'):
            service = validated_data['service']
            queue_type = validated_data['queue_type']
            validated_data['name'] = f"{service.name} - {queue_type.title()}"
        
        return super().create(validated_data)


class QueueUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour MODIFIER une file d'attente existante
    
    Usage : PUT/PATCH /api/queues/1/
    Certains champs ne peuvent pas être modifiés
    """
    
    class Meta:
        model = Queue
        fields = [
            # Modifiables
            'name', 'description', 'processing_strategy',
            'max_capacity', 'max_wait_time', 'ticket_expiry_time',
            'opening_hours', 'current_status', 'notifications_enabled',
            'notify_before_turns', 'is_active'
        ]
        
        # Champs NON modifiables une fois créés
        read_only_fields = [
            'service', 'organization', 'queue_type',
            'last_ticket_number', 'current_ticket_number',
            'waiting_tickets_count', 'stats_date',
            'daily_tickets_issued', 'daily_tickets_served',
            'daily_average_wait_time'
        ]


class QueueStatsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les STATISTIQUES d'une file d'attente
    
    Usage : GET /api/queues/1/stats/
    Uniquement les données statistiques et temps réel
    """
    
    # Statistiques calculées
    success_rate = serializers.SerializerMethodField()
    efficiency_score = serializers.SerializerMethodField()
    peak_hours = serializers.SerializerMethodField()
    
    class Meta:
        model = Queue
        fields = [
            'id', 'name', 'current_status',
            
            # Temps réel
            'last_ticket_number', 'current_ticket_number',
            'waiting_tickets_count', 'estimated_wait_time',
            
            # Statistiques du jour
            'daily_tickets_issued', 'daily_tickets_served',
            'daily_average_wait_time', 'stats_date',
            
            # Métriques calculées
            'success_rate', 'efficiency_score', 'peak_hours'
        ]
    
    def get_success_rate(self, obj):
        """Taux de succès (tickets servis / tickets émis) en pourcentage"""
        if obj.daily_tickets_issued > 0:
            return round((obj.daily_tickets_served / obj.daily_tickets_issued) * 100, 1)
        return 0.0
    
    def get_efficiency_score(self, obj):
        """Score d'efficacité basé sur temps d'attente vs temps prévu"""
        if obj.daily_average_wait_time > 0 and obj.service.estimated_duration > 0:
            expected_wait = obj.service.estimated_duration
            actual_wait = obj.daily_average_wait_time
            
            # Plus le temps réel est proche du temps prévu, meilleur est le score
            if actual_wait <= expected_wait:
                return 100.0
            else:
                # Pénalité si on dépasse
                return max(0.0, 100.0 - ((actual_wait - expected_wait) / expected_wait * 50))
        return 0.0
    
    def get_peak_hours(self, obj):
        """Heures de pointe (à implémenter avec vraies données)"""
        # Pour l'instant, on retourne un exemple
        return [
            {"hour": "09:00", "tickets": 15},
            {"hour": "14:00", "tickets": 12},
            {"hour": "16:00", "tickets": 10}
        ]


class QueueActionSerializer(serializers.Serializer):
    """
    Serializer pour les actions sur les files d'attente
    
    Usage : POST /api/queues/1/call_next/
    """
    
    action = serializers.ChoiceField(
        choices=[
            ('call_next', 'Appeler suivant'),
            ('skip_ticket', 'Passer ticket'),
            ('pause', 'Mettre en pause'),
            ('resume', 'Reprendre'),
            ('reset_daily', 'Reset journalier')
        ],
        help_text="Action à effectuer"
    )
    
    ticket_id = serializers.IntegerField(
        required=False,
        help_text="ID du ticket (pour skip_ticket)"
    )
    
    reason = serializers.CharField(
        max_length=200,
        required=False,
        help_text="Raison de l'action (optionnel)"
    )