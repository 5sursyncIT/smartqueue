# apps/notifications/serializers.py
"""
Serializers pour les notifications SmartQueue
APIs REST pour SMS, Push, Email sénégalais
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    NotificationTemplate, Notification, NotificationPreference,
    SMSProvider, NotificationLog
)


class NotificationTemplateListSerializer(serializers.ModelSerializer):
    """
    Serializer pour lister les templates de notification
    
    Usage : GET /api/notification-templates/
    """
    
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    
    category_display = serializers.CharField(
        source='get_category_display',
        read_only=True
    )
    
    created_by_name = serializers.CharField(
        source='created_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'uuid', 'name',
            'category', 'category_display',
            'notification_type', 'notification_type_display',
            'is_active', 'send_immediately', 'delay_minutes',
            'created_by_name', 'created_at', 'updated_at'
        ]


class NotificationTemplateDetailSerializer(NotificationTemplateListSerializer):
    """
    Serializer pour les détails d'un template
    
    Usage : GET /api/notification-templates/1/
    """
    
    class Meta(NotificationTemplateListSerializer.Meta):
        fields = NotificationTemplateListSerializer.Meta.fields + [
            'subject_fr', 'subject_wo',
            'message_fr', 'message_wo'
        ]


class NotificationTemplateCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer un template de notification
    
    Usage : POST /api/notification-templates/
    """
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'category', 'notification_type',
            'subject_fr', 'subject_wo',
            'message_fr', 'message_wo',
            'is_active', 'send_immediately', 'delay_minutes'
        ]
    
    def validate_message_fr(self, value):
        """Valider que le message français n'est pas vide"""
        if not value.strip():
            raise serializers.ValidationError(
                "Le message en français est obligatoire."
            )
        return value
    
    def validate(self, attrs):
        """Validation globale"""
        # Vérifier que le template n'existe pas déjà
        category = attrs.get('category')
        notification_type = attrs.get('notification_type')
        
        if NotificationTemplate.objects.filter(
            category=category,
            notification_type=notification_type
        ).exists():
            raise serializers.ValidationError(
                f"Un template {notification_type} pour {category} existe déjà."
            )
        
        return attrs
    
    def create(self, validated_data):
        """Créer le template"""
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Serializer pour lister les notifications d'un utilisateur
    
    Usage : GET /api/notifications/
    """
    
    template_name = serializers.CharField(
        source='template.name',
        read_only=True
    )
    
    template_category = serializers.CharField(
        source='template.get_category_display',
        read_only=True
    )
    
    template_type = serializers.CharField(
        source='template.get_notification_type_display',
        read_only=True
    )
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )
    
    # Propriétés calculées
    is_overdue = serializers.BooleanField(read_only=True)
    can_retry = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'uuid', 
            'template_name', 'template_category', 'template_type',
            'subject', 'message',
            'status', 'status_display',
            'priority', 'priority_display',
            'scheduled_at', 'sent_at', 'delivered_at', 'read_at',
            'attempt_count', 'max_attempts',
            'is_overdue', 'can_retry',
            'created_at'
        ]


class NotificationDetailSerializer(NotificationListSerializer):
    """
    Serializer pour les détails d'une notification
    
    Usage : GET /api/notifications/1/
    """
    
    recipient_name = serializers.CharField(
        source='recipient.get_full_name',
        read_only=True
    )
    
    content_object_info = serializers.SerializerMethodField()
    
    class Meta(NotificationListSerializer.Meta):
        fields = NotificationListSerializer.Meta.fields + [
            'recipient_name', 'content_object_info',
            'phone_number', 'email_address',
            'last_error', 'response_received', 'response_text', 'response_at',
            'updated_at'
        ]
    
    def get_content_object_info(self, obj):
        """Informations sur l'objet lié (Ticket, Appointment, etc.)"""
        if not obj.content_object:
            return None
        
        content_obj = obj.content_object
        
        # Informations spécifiques selon le type d'objet
        if hasattr(content_obj, 'ticket_number'):
            # C'est un Ticket
            return {
                'type': 'Ticket',
                'id': content_obj.id,
                'number': content_obj.ticket_number,
                'status': content_obj.get_status_display(),
                'organization': content_obj.organization.trade_name
            }
        elif hasattr(content_obj, 'appointment_number'):
            # C'est un Appointment
            return {
                'type': 'Rendez-vous',
                'id': content_obj.id,
                'number': content_obj.appointment_number,
                'date': content_obj.scheduled_date,
                'time': content_obj.scheduled_time,
                'organization': content_obj.organization.trade_name
            }
        else:
            # Objet générique
            return {
                'type': obj.content_type.name,
                'id': content_obj.id,
                'name': str(content_obj)
            }


class SendNotificationSerializer(serializers.Serializer):
    """
    Serializer pour envoyer une notification manuelle
    
    Usage : POST /api/notifications/send/
    """
    
    template_id = serializers.IntegerField(
        help_text="ID du template à utiliser"
    )
    
    recipient_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="Liste des IDs des destinataires"
    )
    
    content_type_id = serializers.IntegerField(
        required=False,
        help_text="ID du ContentType de l'objet lié (optionnel)"
    )
    
    object_id = serializers.IntegerField(
        required=False,
        help_text="ID de l'objet lié (optionnel)"
    )
    
    custom_variables = serializers.JSONField(
        required=False,
        help_text="Variables personnalisées pour le template"
    )
    
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default='normal'
    )
    
    schedule_for = serializers.DateTimeField(
        required=False,
        help_text="Programmer l'envoi (optionnel, sinon immédiat)"
    )
    
    def validate_template_id(self, value):
        """Valider que le template existe et est actif"""
        try:
            template = NotificationTemplate.objects.get(id=value, is_active=True)
        except NotificationTemplate.DoesNotExist:
            raise serializers.ValidationError("Template non trouvé ou inactif.")
        return value
    
    def validate_recipient_ids(self, value):
        """Valider que tous les destinataires existent"""
        from apps.accounts.models import User
        
        if not value:
            raise serializers.ValidationError("Au moins un destinataire requis.")
        
        existing_count = User.objects.filter(id__in=value).count()
        if existing_count != len(value):
            raise serializers.ValidationError("Certains destinataires n'existent pas.")
        
        return value
    
    def validate_schedule_for(self, value):
        """Valider que la date est dans le futur"""
        if value and value <= timezone.now():
            raise serializers.ValidationError(
                "La date de programmation doit être dans le futur."
            )
        return value


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer pour les préférences de notification
    
    Usage : GET/PUT /api/notification-preferences/
    """
    
    user_name = serializers.CharField(
        source='user.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = NotificationPreference
        fields = [
            'user_name', 'prefer_sms', 'prefer_email', 'prefer_push', 'prefer_web',
            'language', 'notify_ticket_called', 'notify_position_update',
            'notify_queue_full', 'notify_appointment_confirmed',
            'notify_appointment_reminder', 'appointment_reminder_hours',
            'quiet_hours_start', 'quiet_hours_end', 'emergency_phone',
            'updated_at'
        ]
    
    def validate_emergency_phone(self, value):
        """Valider le format du téléphone d'urgence"""
        if value and not value.startswith('+221'):
            raise serializers.ValidationError(
                "Le numéro d'urgence doit commencer par +221."
            )
        return value
    
    def validate(self, attrs):
        """Validation des heures silencieuses"""
        start = attrs.get('quiet_hours_start')
        end = attrs.get('quiet_hours_end')
        
        if start and end and start == end:
            raise serializers.ValidationError(
                "Les heures de début et fin ne peuvent être identiques."
            )
        
        return attrs


class SMSProviderSerializer(serializers.ModelSerializer):
    """
    Serializer pour les fournisseurs SMS (admin seulement)
    
    Usage : GET/POST /api/sms-providers/
    """
    
    provider_type_display = serializers.CharField(
        source='get_provider_type_display',
        read_only=True
    )
    
    class Meta:
        model = SMSProvider
        fields = [
            'id', 'name', 'provider_type', 'provider_type_display',
            'sender_name', 'rate_limit_per_minute', 'cost_per_sms',
            'is_active', 'is_primary', 'priority',
            'created_at', 'updated_at'
        ]
        # Masquer les clés API sensibles en lecture
        extra_kwargs = {
            'api_key': {'write_only': True},
            'api_secret': {'write_only': True},
            'api_url': {'write_only': True}
        }


class NotificationStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques de notifications
    
    Usage : GET /api/notifications/stats/
    """
    
    total_notifications = serializers.IntegerField()
    pending_notifications = serializers.IntegerField()
    sent_notifications = serializers.IntegerField()
    delivered_notifications = serializers.IntegerField()
    failed_notifications = serializers.IntegerField()
    
    today_notifications = serializers.IntegerField()
    weekly_notifications = serializers.IntegerField()
    monthly_notifications = serializers.IntegerField()
    
    success_rate = serializers.FloatField()
    delivery_rate = serializers.FloatField()
    average_delivery_time = serializers.FloatField()  # En minutes
    
    notifications_by_type = serializers.JSONField()
    notifications_by_category = serializers.JSONField()
    weekly_stats = serializers.ListField()
    
    # Coûts (CFA)
    total_cost_today = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cost_month = serializers.DecimalField(max_digits=10, decimal_places=2)


class NotificationLogSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'historique des notifications
    
    Usage : GET /api/notifications/1/logs/
    """
    
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )
    
    provider_name = serializers.CharField(
        source='provider_used.name',
        read_only=True
    )
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'action', 'action_display',
            'provider_name', 'cost', 'details',
            'created_at'
        ]


class BulkNotificationSerializer(serializers.Serializer):
    """
    Serializer pour envoyer des notifications en masse
    
    Usage : POST /api/notifications/bulk/
    """
    
    template_id = serializers.IntegerField()
    
    # Filtres pour sélectionner les destinataires
    user_type = serializers.ChoiceField(
        choices=[
            ('customer', 'Clients'),
            ('staff', 'Personnel'),
            ('admin', 'Administrateurs'),
            ('all', 'Tous')
        ],
        default='customer'
    )
    
    organization_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Filtrer par organisations (optionnel)"
    )
    
    service_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Filtrer par services (optionnel)"
    )
    
    has_active_ticket = serializers.BooleanField(
        required=False,
        help_text="Seulement les utilisateurs avec ticket actif"
    )
    
    has_upcoming_appointment = serializers.BooleanField(
        required=False,
        help_text="Seulement les utilisateurs avec RDV à venir"
    )
    
    custom_variables = serializers.JSONField(
        required=False,
        help_text="Variables globales pour tous les messages"
    )
    
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default='normal'
    )
    
    schedule_for = serializers.DateTimeField(
        required=False
    )
    
    dry_run = serializers.BooleanField(
        default=False,
        help_text="Teste sans envoyer (retourne nombre de destinataires)"
    )