# apps/tickets/serializers.py
"""
Serializers pour les tickets SmartQueue
Convertissent les modèles Python en JSON pour l'API REST
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from ..models import Ticket

class TicketCreateSerializer(serializers.ModelSerializer):
    """
    Serializer SIMPLE pour la CRÉATION de tickets
    """
    
    def create(self, validated_data):
        # Générer automatiquement les champs manquants
        import uuid
        validated_data['ticket_number'] = f"T{str(uuid.uuid4())[:8].upper()}"
        validated_data['expires_at'] = timezone.now() + timedelta(hours=2)
        return super().create(validated_data)
    
    class Meta:
        model = Ticket
        fields = [
            'queue', 'service', 'customer', 'priority'
        ]

class TicketListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la LISTE des tickets
    
    Usage : GET /api/tickets/
    Affiche les infos essentielles (pas tous les détails)
    """
    
    # Champs calculés
    queue_name = serializers.CharField(
        source='queue.name', 
        read_only=True,
        help_text="Nom de la file d'attente"
    )
    
    service_name = serializers.CharField(
        source='service.name', 
        read_only=True,
        help_text="Nom du service"
    )
    
    organization_name = serializers.CharField(
        source='queue.organization.name', 
        read_only=True,
        help_text="Nom de l'organisation"
    )
    
    customer_name = serializers.CharField(
        source='customer.get_full_name', 
        read_only=True,
        help_text="Nom complet du client"
    )
    
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True,
        help_text="Statut lisible (ex: 'En attente' au lieu de 'waiting')"
    )
    
    priority_display = serializers.CharField(
        source='get_priority_display', 
        read_only=True,
        help_text="Priorité lisible"
    )
    
    channel_display = serializers.CharField(
        source='get_creation_channel_display', 
        read_only=True,
        help_text="Canal de création lisible"
    )
    
    is_expired = serializers.ReadOnlyField(
        help_text="Le ticket est-il expiré ?"
    )
    
    estimated_call_time = serializers.ReadOnlyField(
        help_text="Heure estimée d'appel"
    )
    
    # Temps d'attente formaté
    wait_time_formatted = serializers.SerializerMethodField(
        help_text="Temps d'attente formaté (ex: '25 min')"
    )
    
    class Meta:
        model = Ticket
        fields = [
            # Identifiants
            'id', 'uuid', 'ticket_number',
            
            # Relations
            'queue_name', 'service_name', 'organization_name', 'customer_name',
            
            # Configuration
            'priority', 'priority_display', 'creation_channel', 'channel_display',
            
            # Statut
            'status', 'status_display', 'queue_position', 'is_expired',
            
            # Temps
            'created_at', 'expires_at', 'estimated_call_time',
            'wait_time_minutes', 'wait_time_formatted',
            
            # Métadonnées
            'call_count'
        ]
        read_only_fields = [
            'id', 'uuid', 'queue_name', 'service_name', 'organization_name',
            'customer_name', 'status_display', 'priority_display', 'channel_display',
            'is_expired', 'estimated_call_time', 'wait_time_formatted',
            'wait_time_minutes', 'call_count'
        ]
    
    def get_wait_time_formatted(self, obj):
        """Formate le temps d'attente de manière lisible"""
        if obj.wait_time_minutes == 0:
            return "Pas encore appelé"
        elif obj.wait_time_minutes < 60:
            return f"{obj.wait_time_minutes} min"
        else:
            hours = obj.wait_time_minutes // 60
            minutes = obj.wait_time_minutes % 60
            if minutes == 0:
                return f"{hours}h"
            else:
                return f"{hours}h{minutes:02d}"


class TicketDetailSerializer(TicketListSerializer):
    """
    Serializer pour les DÉTAILS d'un ticket
    
    Usage : GET /api/tickets/1/
    Affiche TOUTES les informations (version complète)
    """
    
    # Informations de la file d'attente
    queue = serializers.SerializerMethodField(
        help_text="Détails de la file d'attente"
    )
    
    # Informations du service
    service = serializers.SerializerMethodField(
        help_text="Détails du service"
    )
    
    # Informations du client
    customer = serializers.SerializerMethodField(
        help_text="Informations du client"
    )
    
    # Agent qui sert
    serving_agent_name = serializers.CharField(
        source='serving_agent.get_full_name', 
        read_only=True,
        help_text="Nom de l'agent qui sert"
    )
    
    # Historique des temps
    timeline = serializers.SerializerMethodField(
        help_text="Chronologie des événements"
    )
    
    class Meta(TicketListSerializer.Meta):
        # Hérite de tous les champs de TicketListSerializer
        # + ajoute les champs détaillés
        fields = TicketListSerializer.Meta.fields + [
            # Configuration complète
            'customer_notes', 'documents_brought',
            
            # Timestamps détaillés
            'called_at', 'service_started_at', 'service_ended_at',
            'service_time_minutes',
            
            # Agents
            'serving_agent_name',
            
            # Relations complètes
            'queue', 'service', 'customer',
            
            # Historique
            'timeline', 'notifications_sent',
            
            # Métadonnées complètes
            'created_ip', 'updated_at'
        ]
    
    def get_queue(self, obj):
        """Retourne les détails de la file d'attente"""
        if obj.queue:
            return {
                'id': obj.queue.id,
                'name': obj.queue.name,
                'type': obj.queue.queue_type,
                'current_status': obj.queue.current_status,
                'waiting_count': obj.queue.waiting_tickets_count,
                'estimated_wait_time': obj.queue.estimated_wait_time
            }
        return None
    
    def get_service(self, obj):
        """Retourne les détails du service"""
        if obj.service:
            return {
                'id': obj.service.id,
                'name': obj.service.name,
                'code': obj.service.code,
                'estimated_duration': obj.service.estimated_duration,
                'cost': str(obj.service.cost) if obj.service.cost else None
            }
        return None
    
    def get_customer(self, obj):
        """Retourne les informations du client (anonymisées si besoin)"""
        if obj.customer:
            return {
                'id': obj.customer.id,
                'full_name': obj.customer.get_full_name(),
                'phone_number': obj.customer.phone_number[-4:].rjust(len(obj.customer.phone_number), '*'),  # Masque sauf 4 derniers
                'preferred_language': obj.customer.preferred_language
            }
        return None
    
    def get_timeline(self, obj):
        """Retourne la chronologie des événements du ticket"""
        timeline = []
        
        timeline.append({
            'event': 'Ticket créé',
            'timestamp': obj.created_at,
            'description': f'Via {obj.get_creation_channel_display()}'
        })
        
        if obj.called_at:
            timeline.append({
                'event': 'Ticket appelé',
                'timestamp': obj.called_at,
                'description': f'Appelé {obj.call_count} fois'
            })
        
        if obj.service_started_at:
            timeline.append({
                'event': 'Service commencé',
                'timestamp': obj.service_started_at,
                'description': f'Par {obj.serving_agent.get_full_name() if obj.serving_agent else "Agent inconnu"}'
            })
        
        if obj.service_ended_at:
            timeline.append({
                'event': 'Service terminé',
                'timestamp': obj.service_ended_at,
                'description': f'Durée: {obj.service_time_minutes} min'
            })
        
        return timeline


class TicketCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour CRÉER un nouveau ticket (prise de ticket)
    
    Usage : POST /api/tickets/
    Validation stricte + génération automatique du numéro
    """
    
    # Champs optionnels pour la création
    phone_number = serializers.CharField(
        max_length=15,
        required=False,
        help_text="Numéro de téléphone du client (si pas connecté)"
    )
    
    customer_name = serializers.CharField(
        max_length=100,
        required=False,
        help_text="Nom du client (si pas connecté)"
    )
    
    class Meta:
        model = Ticket
        fields = [
            # Obligatoires
            'queue', 'service',
            
            # Optionnels
            'customer', 'phone_number', 'customer_name',
            'priority', 'creation_channel', 'customer_notes',
            'documents_brought'
        ]
        extra_kwargs = {
            'customer': {'required': False, 'allow_null': True}
        }
    
    def validate(self, attrs):
        """
        Validation globale
        """
        queue = attrs.get('queue')
        service = attrs.get('service')
        customer = attrs.get('customer')
        phone_number = attrs.get('phone_number')
        customer_name = attrs.get('customer_name')
        
        # Vérifier que le service correspond à la file
        if queue and service and queue.service != service:
            raise serializers.ValidationError({
                'service': 'Ce service ne correspond pas à la file d\'attente sélectionnée.'
            })
        
        # Vérifier que la file est ouverte
        if queue and queue.current_status != 'active':
            raise serializers.ValidationError({
                'queue': f'La file d\'attente est {queue.get_current_status_display().lower()}.'
            })
        
        # Vérifier la capacité de la file
        if queue and queue.max_capacity > 0:
            if queue.waiting_tickets_count >= queue.max_capacity:
                raise serializers.ValidationError({
                    'queue': 'La file d\'attente est pleine.'
                })
        
        # Si pas d'utilisateur connecté, il faut téléphone ET nom
        if not customer and not (phone_number and customer_name):
            raise serializers.ValidationError({
                'customer': 'Il faut soit être connecté, soit fournir nom et téléphone.'
            })
        
        # Validation du numéro sénégalais
        if phone_number:
            import re
            if not re.match(r'^\+221[0-9]{9}$', phone_number):
                raise serializers.ValidationError({
                    'phone_number': 'Le numéro doit être au format +221XXXXXXXXX'
                })
        
        return attrs
    
    def create(self, validated_data):
        """
        Logique de création personnalisée
        """
        queue = validated_data['queue']
        service = validated_data['service']
        customer = validated_data.get('customer')
        phone_number = validated_data.get('phone_number')
        customer_name = validated_data.get('customer_name')
        
        # Créer ou récupérer le client si pas connecté
        if not customer and phone_number and customer_name:
            from apps.accounts.models import User
            import uuid
            customer, created = User.objects.get_or_create(
                phone_number=phone_number,
                defaults={
                    'username': f"customer_{uuid.uuid4().hex[:8]}",
                    'first_name': customer_name.split()[0],
                    'last_name': ' '.join(customer_name.split()[1:]) if len(customer_name.split()) > 1 else '',
                    'user_type': 'customer',
                    'is_active': True
                }
            )
        
        # Créer le ticket
        ticket = Ticket.objects.create(
            queue=queue,
            service=service,
            customer=customer,
            priority=validated_data.get('priority', 'low'),
            creation_channel=validated_data.get('creation_channel', 'mobile'),
            customer_notes=validated_data.get('customer_notes', ''),
            documents_brought=validated_data.get('documents_brought', []),
            queue_position=queue.waiting_tickets_count + 1,
            created_ip=self.context.get('request').META.get('REMOTE_ADDR') if self.context.get('request') else None
        )
        
        # Mettre à jour les compteurs de la file
        queue.waiting_tickets_count += 1
        queue.daily_tickets_issued += 1
        queue.save()
        
        return ticket


class TicketUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour MODIFIER un ticket existant
    
    Usage : PUT/PATCH /api/tickets/1/
    Seulement certains champs modifiables
    """
    
    class Meta:
        model = Ticket
        fields = [
            # Modifiables par le client
            'customer_notes', 'documents_brought',
            
            # Modifiables par l'agent
            'serving_agent', 'status'
        ]
        
        # Champs NON modifiables une fois créés
        read_only_fields = [
            'queue', 'service', 'customer', 'ticket_number',
            'priority', 'creation_channel', 'queue_position',
            'wait_time_minutes', 'service_time_minutes',
            'call_count', 'expires_at'
        ]
    
    def update(self, instance, validated_data):
        """
        Logique de mise à jour avec calculs automatiques
        """
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        # Calculer les temps automatiquement lors des changements de statut
        now = timezone.now()
        
        if old_status != 'called' and new_status == 'called':
            instance.called_at = now
            instance.call_count += 1
        
        elif old_status != 'serving' and new_status == 'serving':
            instance.service_started_at = now
            if instance.called_at:
                instance.wait_time_minutes = int((now - instance.created_at).total_seconds() / 60)
        
        elif old_status != 'served' and new_status == 'served':
            instance.service_ended_at = now
            if instance.service_started_at:
                instance.service_time_minutes = int((now - instance.service_started_at).total_seconds() / 60)
            
            # Mettre à jour les statistiques de la file
            instance.queue.daily_tickets_served += 1
            instance.queue.waiting_tickets_count = max(0, instance.queue.waiting_tickets_count - 1)
            instance.queue.save()
        
        return super().update(instance, validated_data)


class TicketActionSerializer(serializers.Serializer):
    """
    Serializer pour les actions sur les tickets
    
    Usage : POST /api/tickets/1/cancel/
    """
    
    action = serializers.ChoiceField(
        choices=[
            ('cancel', 'Annuler'),
            ('transfer', 'Transférer'),
            ('extend', 'Prolonger'),
            ('call_again', 'Rappeler')
        ],
        help_text="Action à effectuer"
    )
    
    target_queue_id = serializers.IntegerField(
        required=False,
        help_text="ID de la file cible (pour transfer)"
    )
    
    reason = serializers.CharField(
        max_length=200,
        required=False,
        help_text="Raison de l'action"
    )
    
    extend_minutes = serializers.IntegerField(
        required=False,
        min_value=5,
        max_value=60,
        help_text="Minutes d'extension (pour extend)"
    )


class TicketStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques des tickets
    
    Usage : GET /api/tickets/stats/
    """
    
    total_tickets = serializers.IntegerField()
    waiting_tickets = serializers.IntegerField()
    served_tickets = serializers.IntegerField()
    cancelled_tickets = serializers.IntegerField()
    expired_tickets = serializers.IntegerField()
    
    average_wait_time = serializers.FloatField()
    average_service_time = serializers.FloatField()
    
    success_rate = serializers.FloatField(help_text="Pourcentage de tickets servis avec succès")
    
    today_stats = serializers.DictField()
    weekly_stats = serializers.DictField()