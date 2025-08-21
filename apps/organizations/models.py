# apps/organizations/models.py
"""
Modèles des organisations pour SmartQueue Sénégal
"""

from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
import uuid

class Organization(models.Model):
    """
    Modèle principal pour les organisations/établissements
    """
    
    # Types d'organisations au Sénégal
    ORGANIZATION_TYPES = [
        ('bank', _('Banque')),
        ('hospital', _('Hôpital/Clinique')),
        ('government', _('Administration publique')),
        ('telecom', _('Télécommunication')),
        ('insurance', _('Assurance')),
        ('business', _('Entreprise privée')),
        ('education', _('Établissement éducatif')),
        ('retail', _('Commerce/Retail')),
        ('other', _('Autre')),
    ]
    
    # Plans d'abonnement SmartQueue
    SUBSCRIPTION_PLANS = [
        ('starter', _('Pack Starter')),
        ('business', _('Pack Business')),
        ('enterprise', _('Pack Enterprise')),
        ('custom', _('Pack Sur Mesure')),
    ]
    
    # Statuts de l'organisation
    STATUS_CHOICES = [
        ('active', _('Actif')),
        ('inactive', _('Inactif')),
        ('suspended', _('Suspendu')),
        ('trial', _('Version d\'essai')),
    ]
    
    # Régions du Sénégal
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
    
    # Identifiant unique
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Informations de base
    name = models.CharField(max_length=200, verbose_name=_('Nom de l\'organisation'))
    trade_name = models.CharField(max_length=200, blank=True, verbose_name=_('Nom commercial'))
    type = models.CharField(max_length=20, choices=ORGANIZATION_TYPES, verbose_name=_('Type d\'organisation'))
    description = models.TextField(blank=True, verbose_name=_('Description'))
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, verbose_name=_('Logo'))
    
    # Informations légales
    registration_number = models.CharField(max_length=50, blank=True, verbose_name=_('Numéro d\'immatriculation'))
    
    phone_regex = RegexValidator(
        regex=r'^\+221[0-9]{9}$',
        message=_('Le numéro doit être au format: +221XXXXXXXXX')
    )
    phone_number = models.CharField(validators=[phone_regex], max_length=13, verbose_name=_('Téléphone'))
    email = models.EmailField(verbose_name=_('Email principal'))
    website = models.URLField(blank=True, verbose_name=_('Site web'))
    
    # Adresse
    address = models.TextField(verbose_name=_('Adresse'))
    city = models.CharField(max_length=100, verbose_name=_('Ville'))
    region = models.CharField(max_length=20, choices=SENEGAL_REGIONS, verbose_name=_('Région'))
    
    # Géolocalisation GPS
    latitude = models.DecimalField(
        max_digits=10, decimal_places=8, null=True, blank=True, 
        verbose_name=_('Latitude')
    )
    longitude = models.DecimalField(
        max_digits=11, decimal_places=8, null=True, blank=True, 
        verbose_name=_('Longitude')
    )
    
    # Abonnement SmartQueue
    subscription_plan = models.CharField(
        max_length=20, choices=SUBSCRIPTION_PLANS, default='starter',
        verbose_name=_('Plan d\'abonnement')
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='trial',
        verbose_name=_('Statut')
    )
    subscription_start_date = models.DateTimeField(auto_now_add=True)
    subscription_end_date = models.DateTimeField(null=True, blank=True)
    
    # Limites selon l'abonnement
    max_counters = models.PositiveIntegerField(default=3, verbose_name=_('Max guichets'))
    max_staff_users = models.PositiveIntegerField(default=5, verbose_name=_('Max employés'))
    
    # Configuration
    timezone = models.CharField(max_length=50, default='Africa/Dakar')
    supported_languages = models.JSONField(default=list, blank=True)
    default_language = models.CharField(max_length=5, default='fr')
    notifications_config = models.JSONField(default=dict, blank=True)
    
    # Métadonnées
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True,
        related_name='created_organizations'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Organisation')
        verbose_name_plural = _('Organisations')
        db_table = 'organizations_organization'
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    @property
    def is_trial(self):
        return self.status == 'trial'
    
    @property
    def is_subscription_active(self):
        return self.status == 'active'