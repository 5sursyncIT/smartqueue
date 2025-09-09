# apps/services/serializers.py
"""
Serializers pour les services SmartQueue
Convertissent les modèles Python en JSON pour l'API REST
"""

from rest_framework import serializers
from ..models import Service, ServiceCategory

class ServiceCategorySerializer(serializers.ModelSerializer):
    """
    Serializer pour les catégories de services
    
    Usage : GET /api/service-categories/
    """
    
    class Meta:
        model = ServiceCategory
        fields = [
            'id', 'name', 'description', 'icon', 'color',
            'display_order', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ServiceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer MINIMAL pour la CRÉATION de services - RETOURNE L'ID
    """
    
    def to_representation(self, instance):
        print(f"🔍 DEBUG SERIALIZER: to_representation appelé avec instance.id={instance.id}")
        data = super().to_representation(instance)
        print(f"🔍 DEBUG SERIALIZER: data avant retour={data}")
        return data
    
    class Meta:
        model = Service
        fields = ['id', 'name', 'code', 'organization']  # Champs essentiels + code obligatoire


class ServiceSimpleListSerializer(serializers.ModelSerializer):
    """
    Serializer ULTRA SIMPLE pour debug - JUSTE ID et nom
    """
    
    class Meta:
        model = Service
        fields = ['id', 'name']

class ServiceListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la LISTE des services
    
    Usage : GET /api/services/
    Affiche les infos essentielles (pas tous les détails)
    """
    
    # Champs calculés
    organization_name = serializers.CharField(
        source='organization.name', 
        read_only=True,
        help_text="Nom de l'organisation qui offre ce service"
    )
    
    category_name = serializers.CharField(
        source='category.name', 
        read_only=True,
        help_text="Nom de la catégorie du service"
    )
    
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True,
        help_text="Statut lisible (ex: 'Actif' au lieu de 'active')"
    )
    
    priority_display = serializers.CharField(
        source='get_default_priority_display', 
        read_only=True,
        help_text="Priorité lisible (ex: 'Normale' au lieu de 'low')"
    )
    
    class Meta:
        model = Service
        fields = [
            # Identifiants
            'id', 'uuid', 'code',
            
            # Informations de base
            'name', 'description', 'organization_name', 'category_name',
            
            # Configuration
            'estimated_duration', 'cost', 'default_priority', 'priority_display',
            'status', 'status_display', 'is_public',
            
            # RDV
            'allows_appointments', 'requires_appointment',
            
            # Statistiques
            'total_tickets_issued', 'average_rating', 'total_ratings',
            
            # Métadonnées
            'created_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'organization_name', 'category_name',
            'status_display', 'priority_display', 'total_tickets_issued',
            'average_rating', 'total_ratings', 'created_at'
        ]


class ServiceDetailSerializer(ServiceListSerializer):
    """
    Serializer pour les DÉTAILS d'un service
    
    Usage : GET /api/services/1/
    Affiche TOUTES les informations (version complète)
    """
    
    # Informations de l'organisation
    organization = serializers.SerializerMethodField(
        help_text="Détails de l'organisation"
    )
    
    # Informations de la catégorie
    category = serializers.SerializerMethodField(
        help_text="Détails de la catégorie"
    )
    
    class Meta(ServiceListSerializer.Meta):
        # Hérite de tous les champs de ServiceListSerializer
        # + ajoute les champs détaillés
        fields = ServiceListSerializer.Meta.fields + [
            # Configuration complète
            'instructions', 'max_wait_time',
            
            # RDV détaillé
            'min_appointment_notice', 'max_appointment_advance',
            
            # Documents
            'required_documents', 'optional_documents',
            
            # Horaires et notifications
            'service_hours', 'sms_notifications', 'push_notifications',
            'sms_template',
            
            # Visibilité
            'requires_authentication', 'display_order',
            
            # Relations complètes
            'organization', 'category',
            
            # Métadonnées complètes
            'updated_at'
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
    
    def get_category(self, obj):
        """
        Retourne les détails de la catégorie
        """
        if obj.category:
            return {
                'id': obj.category.id,
                'name': obj.category.name,
                'icon': obj.category.icon,
                'color': obj.category.color
            }
        return None




class ServiceUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour MODIFIER un service existant
    
    Usage : PUT/PATCH /api/services/1/
    Certains champs ne peuvent pas être modifiés
    """
    
    class Meta:
        model = Service
        fields = [
            # Modifiables
            'name', 'description', 'instructions', 'category',
            'estimated_duration', 'max_wait_time', 'cost',
            'default_priority', 'allows_appointments', 'requires_appointment',
            'min_appointment_notice', 'max_appointment_advance',
            'required_documents', 'optional_documents', 'service_hours',
            'sms_notifications', 'push_notifications', 'sms_template',
            'status', 'is_public', 'requires_authentication', 'display_order'
        ]
        
        # Champs NON modifiables une fois créés
        read_only_fields = [
            'organization', 'code', 'total_tickets_issued',
            'average_rating', 'total_ratings'
        ]
    
    def validate_estimated_duration(self, value):
        """
        Validation de la durée estimée pour modification
        """
        if value < 1 or value > 180:
            raise serializers.ValidationError(
                "La durée estimée doit être entre 1 et 180 minutes."
            )
        return value


class ServiceStatsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les STATISTIQUES d'un service
    
    Usage : GET /api/services/1/stats/
    Uniquement les données statistiques
    """
    
    # Statistiques calculées
    current_wait_time = serializers.SerializerMethodField()
    tickets_today = serializers.SerializerMethodField()
    tickets_this_week = serializers.SerializerMethodField()
    active_queues_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Service
        fields = [
            'id', 'name', 'organization_name',
            'total_tickets_issued', 'average_rating', 'total_ratings',
            'current_wait_time', 'tickets_today', 'tickets_this_week',
            'active_queues_count'
        ]
    
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    
    def get_current_wait_time(self, obj):
        """Temps d'attente actuel estimé"""
        # Pour l'instant, on utilise la durée estimée
        # Plus tard, on calculera avec les vraies données des files
        return obj.estimated_duration
    
    def get_tickets_today(self, obj):
        """Nombre de tickets pris aujourd'hui pour ce service"""
        # À implémenter avec les vraies données plus tard
        return 0
    
    def get_tickets_this_week(self, obj):
        """Nombre de tickets pris cette semaine"""
        # À implémenter avec les vraies données plus tard
        return 0
    
    def get_active_queues_count(self, obj):
        """Nombre de files d'attente actives pour ce service"""
        return obj.queues.filter(current_status='active').count()