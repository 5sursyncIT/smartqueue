# apps/core/serializers.py
"""
Serializers pour l'application core SmartQueue
Configuration, logs, utilitaires
"""

from rest_framework import serializers
from .models import Configuration, ActivityLog


class ConfigurationSerializer(serializers.ModelSerializer):
    """Serializer pour Configuration (admin seulement)"""
    
    class Meta:
        model = Configuration
        fields = [
            'id', 'uuid', 'site_name', 'site_description',
            'support_email', 'support_phone',
            'default_ticket_expiry_minutes', 'default_appointment_duration_minutes',
            'max_tickets_per_user_per_day', 'max_appointments_per_user_per_day',
            'sms_enabled', 'push_enabled', 'email_enabled',
            'maintenance_mode', 'maintenance_message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uuid', 'created_at', 'updated_at']


class PublicConfigurationSerializer(serializers.ModelSerializer):
    """Serializer pour configuration publique (sans données sensibles)"""
    
    class Meta:
        model = Configuration
        fields = [
            'site_name', 'site_description', 'support_email', 'support_phone',
            'default_ticket_expiry_minutes', 'default_appointment_duration_minutes',
            'max_tickets_per_user_per_day', 'max_appointments_per_user_per_day',
            'sms_enabled', 'push_enabled', 'email_enabled'
        ]


class ActivityLogSerializer(serializers.ModelSerializer):
    """Serializer pour logs d'activité"""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_name = serializers.SerializerMethodField()
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    
    class Meta:
        model = ActivityLog
        fields = [
            'id', 'user', 'user_email', 'user_name',
            'action_type', 'action_type_display',
            'model_name', 'object_id', 'description',
            'ip_address', 'user_agent', 'metadata',
            'created_at'
        ]
        read_only_fields = fields  # Tous en lecture seule
    
    def get_user_name(self, obj):
        """Nom complet de l'utilisateur"""
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return "Anonyme"


class SystemStatusSerializer(serializers.Serializer):
    """Serializer pour status système"""
    
    timestamp = serializers.DateTimeField()
    status = serializers.CharField()
    version = serializers.CharField()
    
    # Checks détaillés
    database_status = serializers.CharField()
    cache_status = serializers.CharField()
    maintenance_status = serializers.CharField()
    
    # Stats système
    cpu_percent = serializers.FloatField(required=False)
    memory_percent = serializers.FloatField(required=False)
    disk_percent = serializers.FloatField(required=False)
    
    # Stats métier
    total_users = serializers.IntegerField(required=False)
    tickets_today = serializers.IntegerField(required=False)
    recent_logins_24h = serializers.IntegerField(required=False)


class PhoneValidationSerializer(serializers.Serializer):
    """Serializer pour validation téléphone"""
    
    phone = serializers.CharField(max_length=20, required=True)
    
    def validate_phone(self, value):
        """Validation basique du format"""
        if not value or len(value) < 8:
            raise serializers.ValidationError("Numéro trop court")
        return value


class PhoneValidationResponseSerializer(serializers.Serializer):
    """Serializer pour réponse validation téléphone"""
    
    original = serializers.CharField()
    normalized = serializers.CharField(allow_null=True)
    is_valid = serializers.BooleanField()
    format_required = serializers.CharField()


class SenegalRegionSerializer(serializers.Serializer):
    """Serializer pour régions du Sénégal"""
    
    code = serializers.CharField()
    name = serializers.CharField()


class MaintenanceModeSerializer(serializers.Serializer):
    """Serializer pour gestion mode maintenance"""
    
    maintenance_mode = serializers.BooleanField()
    maintenance_message = serializers.CharField(allow_blank=True, required=False)
    
    def validate_maintenance_message(self, value):
        """Validation message de maintenance"""
        if value and len(value) > 500:
            raise serializers.ValidationError("Message trop long (max 500 caractères)")
        return value