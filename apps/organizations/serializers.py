# apps/organizations/serializers.py
"""
Serializers pour les organisations SmartQueue
Convertissent les modèles Python en JSON pour l'API REST
"""

from rest_framework import serializers
from .models import Organization

class OrganizationListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la LISTE des organisations
    
    Usage : GET /api/organizations/
    Affiche les infos de base (pas tous les détails)
    """
    
    # Champs calculés (read-only)
    type_display = serializers.CharField(
        source='get_type_display', 
        read_only=True,
        help_text="Nom lisible du type (ex: 'Banque' au lieu de 'bank')"
    )
    
    subscription_plan_display = serializers.CharField(
        source='get_subscription_plan_display', 
        read_only=True,
        help_text="Nom lisible du plan (ex: 'Pack Starter')"
    )
    
    # Coordonnées GPS lisibles
    latitude = serializers.DecimalField(
        max_digits=10, decimal_places=8, 
        read_only=True,
        help_text="Latitude GPS (ex: 14.6928 pour Dakar)"
    )
    longitude = serializers.DecimalField(
        max_digits=11, decimal_places=8, 
        read_only=True,
        help_text="Longitude GPS (ex: -17.4441 pour Dakar)"
    )
    
    class Meta:
        model = Organization
        fields = [
            # Identifiants
            'id', 'uuid', 
            
            # Informations de base
            'name', 'trade_name', 'type', 'type_display',
            'description', 'logo',
            
            # Contact
            'phone_number', 'email', 'website',
            
            # Localisation
            'city', 'region', 'latitude', 'longitude',
            
            # Abonnement SmartQueue
            'subscription_plan', 'subscription_plan_display',
            'status', 'is_active',
            
            # Métadonnées
            'created_at'
        ]
        read_only_fields = [
            'id', 'uuid', 'created_at', 'type_display', 
            'subscription_plan_display'
        ]


class OrganizationDetailSerializer(OrganizationListSerializer):
    """
    Serializer pour les DÉTAILS d'une organisation
    
    Usage : GET /api/organizations/1/
    Affiche TOUTES les informations (version complète)
    """
    
    # Statistiques calculées
    total_services = serializers.SerializerMethodField(
        help_text="Nombre total de services offerts"
    )
    
    class Meta(OrganizationListSerializer.Meta):
        # Hérite de tous les champs de OrganizationListSerializer
        # + ajoute les champs détaillés
        fields = OrganizationListSerializer.Meta.fields + [
            # Informations légales complètes
            'registration_number', 'address',
            
            # Configuration avancée
            'timezone', 'supported_languages', 'default_language',
            'notifications_config',
            
            # Limites abonnement
            'max_counters', 'max_staff_users',
            
            # Dates abonnement
            'subscription_start_date', 'subscription_end_date',
            
            # Statistiques
            'total_services',
            
            # Métadonnées complètes
            'created_by', 'updated_at'
        ]
    
    def get_total_services(self, obj):
        """
        Calcule le nombre total de services offerts par cette organisation
        """
        return obj.services.filter(is_public=True, status='active').count()


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour CRÉER une nouvelle organisation
    
    Usage : POST /api/organizations/
    Validation stricte + champs obligatoires
    """
    
    # Validation personnalisée pour le nom
    name = serializers.CharField(
        max_length=200,
        help_text="Nom officiel de l'organisation (ex: Banque de l'Habitat du Sénégal)"
    )
    
    # Validation spécifique pour numéros sénégalais
    phone_number = serializers.RegexField(
        regex=r'^\+221[0-9]{9}$',
        error_messages={'invalid': "Le numéro doit être au format: +221XXXXXXXXX"}
    )
    
    class Meta:
        model = Organization
        fields = [
            # Champs obligatoires pour création
            'name', 'type', 'phone_number', 'email',
            'address', 'city', 'region',
            
            # Champs optionnels
            'trade_name', 'description', 'logo', 'website',
            'registration_number', 'latitude', 'longitude',
            'subscription_plan'
        ]
    
    def validate_name(self, value):
        """
        Validation personnalisée du nom de l'organisation
        """
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Le nom doit contenir au moins 3 caractères."
            )
        
        # Vérifier unicité (pas de doublons)
        if Organization.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError(
                "Une organisation avec ce nom existe déjà."
            )
        
        return value.strip()
    
    def validate_email(self, value):
        """
        Validation de l'email
        """
        # Vérifier unicité de l'email
        if Organization.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Cette adresse email est déjà utilisée par une autre organisation."
            )
        
        return value.lower()
    
    def validate(self, attrs):
        """
        Validation globale (plusieurs champs ensemble)
        """
        # Vérifier cohérence région/ville
        region = attrs.get('region')
        city = attrs.get('city', '').lower()
        
        # Règles spécifiques Sénégal
        if region == 'dakar' and 'dakar' not in city:
            raise serializers.ValidationError({
                'city': 'Pour la région Dakar, la ville doit contenir "Dakar"'
            })
        
        return attrs
    
    def create(self, validated_data):
        """
        Logique de création personnalisée
        """
        # Associer le créateur (super admin qui crée)
        request = self.context.get('request')
        if request and request.user:
            validated_data['created_by'] = request.user
        
        # Définir langues supportées par défaut selon la région
        if not validated_data.get('supported_languages'):
            validated_data['supported_languages'] = ['fr', 'wo']  # Français + Wolof par défaut
        
        return super().create(validated_data)


class OrganizationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour MODIFIER une organisation existante
    
    Usage : PUT/PATCH /api/organizations/1/
    Certains champs ne peuvent pas être modifiés
    """
    
    class Meta:
        model = Organization
        fields = [
            # Modifiables
            'trade_name', 'description', 'logo', 'website',
            'phone_number', 'email', 'address', 'city',
            'latitude', 'longitude', 'timezone',
            'supported_languages', 'default_language',
            'notifications_config'
        ]
        
        # Champs NON modifiables une fois créés
        read_only_fields = [
            'name', 'type', 'region', 'registration_number',
            'subscription_plan', 'status', 'created_by'
        ]
    
    def validate_phone_number(self, value):
        """
        Validation du téléphone pour modification
        """
        # Vérifier format sénégalais
        import re
        if not re.match(r'^\+221[0-9]{9}$', value):
            raise serializers.ValidationError(
                "Le numéro doit être au format: +221XXXXXXXXX"
            )
        
        # Vérifier unicité (exclure l'organisation actuelle)
        organization_id = self.instance.id if self.instance else None
        if Organization.objects.filter(phone_number=value).exclude(id=organization_id).exists():
            raise serializers.ValidationError(
                "Ce numéro de téléphone est déjà utilisé."
            )
        
        return value


class OrganizationStatsSerializer(serializers.ModelSerializer):
    """
    Serializer pour les STATISTIQUES d'une organisation
    
    Usage : GET /api/organizations/1/stats/
    Uniquement les données statistiques
    """
    
    # Statistiques calculées
    total_services = serializers.SerializerMethodField()
    total_active_queues = serializers.SerializerMethodField()
    today_tickets_count = serializers.SerializerMethodField()
    current_waiting_customers = serializers.SerializerMethodField()
    
    class Meta:
        model = Organization
        fields = [
            'id', 'name',
            'total_services', 'total_active_queues',
            'today_tickets_count', 'current_waiting_customers'
        ]
    
    def get_total_services(self, obj):
        """Nombre total de services actifs"""
        return obj.services.filter(status='active').count()
    
    def get_total_active_queues(self, obj):
        """Nombre de files d'attente ouvertes"""
        return obj.queues.filter(current_status='active').count()
    
    def get_today_tickets_count(self, obj):
        """Nombre de tickets émis aujourd'hui"""
        from django.utils import timezone
        today = timezone.now().date()
        return sum(
            queue.daily_tickets_issued 
            for queue in obj.queues.filter(stats_date=today)
        )
    
    def get_current_waiting_customers(self, obj):
        """Nombre total de clients en attente actuellement"""
        return sum(
            queue.waiting_tickets_count 
            for queue in obj.queues.filter(current_status='active')
        )