# apps/core/models.py
"""
Modèles de base et utilitaires communs SmartQueue
Ces modèles sont utilisés partout dans l'application
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid

User = get_user_model()


class TimestampedModel(models.Model):
    """
    Modèle abstrait avec timestamps automatiques
    Utilisé par tous les autres modèles pour traçabilité
    """
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Créé le'),
        help_text=_('Date de création automatique')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modifié le'),
        help_text=_('Date de dernière modification automatique')
    )
    
    class Meta:
        abstract = True
        ordering = ['-created_at']


class UUIDModel(models.Model):
    """
    Modèle abstrait avec UUID unique
    Pour sécurité et éviter l'exposition des IDs séquentiels
    """
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
        verbose_name=_('Identifiant unique'),
        help_text=_('Identifiant UUID non-modifiable')
    )
    
    class Meta:
        abstract = True


class AuditModel(models.Model):
    """
    Modèle abstrait pour audit trail
    Qui a créé/modifié quand et où
    """
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(class)s_created',
        verbose_name=_('Créé par')
    )
    
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(class)s_modified',
        verbose_name=_('Modifié par')
    )
    
    created_ip = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name=_('IP de création')
    )
    
    modified_ip = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name=_('IP de modification')
    )
    
    class Meta:
        abstract = True


class ActiveModel(models.Model):
    """
    Modèle abstrait avec gestion d'activation
    Évite la suppression réelle (soft delete)
    """
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Actif'),
        help_text=_('Désactiver au lieu de supprimer')
    )
    
    deactivated_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_('Désactivé le')
    )
    
    deactivated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(class)s_deactivated',
        verbose_name=_('Désactivé par')
    )
    
    class Meta:
        abstract = True
    
    def deactivate(self, user=None):
        """Désactiver au lieu de supprimer"""
        self.is_active = False
        self.deactivated_at = timezone.now()
        if user:
            self.deactivated_by = user
        self.save(update_fields=['is_active', 'deactivated_at', 'deactivated_by'])
    
    def reactivate(self):
        """Réactiver l'objet"""
        self.is_active = True
        self.deactivated_at = None
        self.deactivated_by = None
        self.save(update_fields=['is_active', 'deactivated_at', 'deactivated_by'])


class BaseSmartQueueModel(TimestampedModel, UUIDModel, AuditModel, ActiveModel):
    """
    Modèle de base complet SmartQueue
    Combine tous les comportements communs
    """
    
    class Meta:
        abstract = True


class PhoneNumberMixin(models.Model):
    """
    Mixin pour numéros de téléphone sénégalais
    """
    phone_regex = RegexValidator(
        regex=r'^\+221[0-9]{9}$',
        message=_('Format requis: +221XXXXXXXXX')
    )
    
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=13,
        verbose_name=_('Numéro de téléphone'),
        help_text=_('Format: +221XXXXXXXXX')
    )
    
    class Meta:
        abstract = True


class AddressMixin(models.Model):
    """
    Mixin pour adresses sénégalaises
    """
    SENEGAL_REGIONS = [
        ('dakar', _('Dakar')),
        ('thies', _('Thiès')),
        ('saint-louis', _('Saint-Louis')),
        ('diourbel', _('Diourbel')),
        ('louga', _('Louga')),
        ('fatick', _('Fatick')),
        ('kaolack', _('Kaolack')),
        ('kaffrine', _('Kaffrine')),
        ('tambacounda', _('Tambacounda')),
        ('kedougou', _('Kédougou')),
        ('kolda', _('Kolda')),
        ('sedhiou', _('Sédhiou')),
        ('ziguinchor', _('Ziguinchor')),
        ('matam', _('Matam')),
    ]
    
    address = models.TextField(
        verbose_name=_('Adresse'),
        help_text=_('Adresse complète')
    )
    
    city = models.CharField(
        max_length=100,
        verbose_name=_('Ville')
    )
    
    region = models.CharField(
        max_length=20,
        choices=SENEGAL_REGIONS,
        verbose_name=_('Région')
    )
    
    postal_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name=_('Code postal')
    )
    
    class Meta:
        abstract = True


class GPSMixin(models.Model):
    """
    Mixin pour coordonnées GPS
    """
    latitude = models.DecimalField(
        max_digits=10, decimal_places=8,
        null=True, blank=True,
        verbose_name=_('Latitude'),
        help_text=_('Coordonnée GPS latitude')
    )
    
    longitude = models.DecimalField(
        max_digits=11, decimal_places=8,
        null=True, blank=True,
        verbose_name=_('Longitude'),
        help_text=_('Coordonnée GPS longitude')
    )
    
    class Meta:
        abstract = True
    
    @property
    def has_coordinates(self):
        """Vérifie si les coordonnées GPS sont définies"""
        return self.latitude is not None and self.longitude is not None
    
    def distance_to(self, other_object):
        """
        Calcule la distance en km vers un autre objet avec GPS
        Utilise la formule Haversine
        """
        if not (self.has_coordinates and other_object.has_coordinates):
            return None
        
        import math
        
        # Conversion en radians
        lat1, lon1 = math.radians(float(self.latitude)), math.radians(float(self.longitude))
        lat2, lon2 = math.radians(float(other_object.latitude)), math.radians(float(other_object.longitude))
        
        # Différences
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Formule Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Rayon de la Terre en km
        r = 6371
        
        return c * r


class StatusChoicesMixin:
    """
    Mixin avec statuts standards SmartQueue
    """
    STANDARD_STATUS_CHOICES = [
        ('active', _('Actif')),
        ('inactive', _('Inactif')),
        ('pending', _('En attente')),
        ('processing', _('En cours')),
        ('completed', _('Terminé')),
        ('cancelled', _('Annulé')),
        ('failed', _('Échoué')),
        ('expired', _('Expiré')),
    ]


class PriorityChoicesMixin:
    """
    Mixin avec niveaux de priorité standards
    """
    PRIORITY_CHOICES = [
        ('low', _('Basse')),
        ('normal', _('Normale')),
        ('high', _('Haute')),
        ('urgent', _('Urgente')),
        ('vip', _('VIP')),
    ]


class Configuration(BaseSmartQueueModel):
    """
    Configuration globale de SmartQueue
    Une seule instance par installation
    """
    
    # Informations générales
    site_name = models.CharField(
        max_length=100,
        default='SmartQueue Sénégal',
        verbose_name=_('Nom du site')
    )
    
    site_description = models.TextField(
        blank=True,
        verbose_name=_('Description du site')
    )
    
    # Contact
    support_email = models.EmailField(
        default='support@smartqueue.sn',
        verbose_name=_('Email support')
    )
    
    support_phone = models.CharField(
        max_length=13,
        default='+221338000000',
        verbose_name=_('Téléphone support')
    )
    
    # Paramètres par défaut
    default_ticket_expiry_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name=_('Expiration ticket par défaut (min)')
    )
    
    default_appointment_duration_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name=_('Durée RDV par défaut (min)')
    )
    
    # Limites système
    max_tickets_per_user_per_day = models.PositiveIntegerField(
        default=5,
        verbose_name=_('Max tickets/utilisateur/jour')
    )
    
    max_appointments_per_user_per_day = models.PositiveIntegerField(
        default=3,
        verbose_name=_('Max RDV/utilisateur/jour')
    )
    
    # Notifications
    sms_enabled = models.BooleanField(
        default=True,
        verbose_name=_('SMS activés')
    )
    
    push_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Push activés')
    )
    
    email_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Emails activés')
    )
    
    # Maintenance
    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name=_('Mode maintenance'),
        help_text=_('Désactive temporairement l\'application')
    )
    
    maintenance_message = models.TextField(
        blank=True,
        verbose_name=_('Message de maintenance')
    )
    
    class Meta:
        verbose_name = _('Configuration')
        verbose_name_plural = _('Configurations')
    
    def __str__(self):
        return f"Configuration {self.site_name}"
    
    @classmethod
    def get_current(cls):
        """Récupère la configuration actuelle"""
        config, created = cls.objects.get_or_create(
            defaults={'site_name': 'SmartQueue Sénégal'}
        )
        return config


class ActivityLog(TimestampedModel):
    """
    Journal des activités utilisateurs
    Pour audit et debugging
    """
    
    ACTION_TYPES = [
        ('create', _('Création')),
        ('update', _('Modification')),
        ('delete', _('Suppression')),
        ('login', _('Connexion')),
        ('logout', _('Déconnexion')),
        ('view', _('Consultation')),
        ('download', _('Téléchargement')),
        ('upload', _('Upload')),
        ('payment', _('Paiement')),
        ('notification', _('Notification')),
        ('api_call', _('Appel API')),
        ('error', _('Erreur')),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Utilisateur')
    )
    
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPES,
        verbose_name=_('Type d\'action')
    )
    
    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Modèle concerné')
    )
    
    object_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('ID objet')
    )
    
    description = models.TextField(
        verbose_name=_('Description')
    )
    
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name=_('Adresse IP')
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name=_('User Agent')
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Métadonnées'),
        help_text=_('Données supplémentaires JSON')
    )
    
    class Meta:
        verbose_name = _('Journal d\'activité')
        verbose_name_plural = _('Journal des activités')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['model_name', 'object_id']),
        ]
    
    def __str__(self):
        user_str = str(self.user) if self.user else 'Anonyme'
        return f"{user_str} - {self.get_action_type_display()} - {self.created_at}"
    
    @classmethod
    def log_activity(cls, user, action_type, description, model_name=None, 
                    object_id=None, ip_address=None, user_agent=None, **metadata):
        """
        Méthode helper pour logger une activité
        """
        return cls.objects.create(
            user=user,
            action_type=action_type,
            model_name=model_name,
            object_id=str(object_id) if object_id else '',
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )