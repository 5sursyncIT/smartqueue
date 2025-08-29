# apps/business/models/service.py
"""
Modèles des services pour SmartQueue Sénégal (dans app business unifiée)
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
import uuid

class ServiceCategory(models.Model):
    """
    Catégories de services pour organiser l'offre
    
    Exemples :
    - Banque : "Comptes", "Crédits", "Change", "Transferts"
    - Hôpital : "Consultations", "Analyses", "Radiologie", "Urgences"
    - Administration : "État civil", "Documents d'identité", "Permis"
    """
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Nom de la catégorie'),
        help_text=_('Ex: Comptes, Consultations, État civil')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description détaillée de la catégorie')
    )
    
    # Icône pour l'interface utilisateur
    icon = models.CharField(
        max_length=50,
        blank=True,
        verbose_name=_('Icône'),
        help_text=_('Nom de l\'icône (ex: credit-card, user, etc.)')
    )
    
    # Couleur de la catégorie (format HEX)
    color = models.CharField(
        max_length=7,
        default='#007bff',
        verbose_name=_('Couleur'),
        help_text=_('Couleur en format HEX (#RRGGBB)')
    )
    
    # Ordre d'affichage
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Ordre d\'affichage')
    )
    
    is_active = models.BooleanField(default=True, verbose_name=_('Actif'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Catégorie de service')
        verbose_name_plural = _('Catégories de services')
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class Service(models.Model):
    """
    Service offert par une organisation
    
    Exemples concrets :
    - "Ouverture compte épargne" (BHS)
    - "Consultation cardiologie" (Hôpital Principal)
    - "Demande passeport" (Préfecture)
    """
    
    # Niveaux de priorité pour les services
    PRIORITY_LEVELS = [
        ('low', _('Normale')),      # Service standard
        ('medium', _('Moyenne')),   # Un peu plus urgent
        ('high', _('Élevée')),      # Prioritaire
        ('urgent', _('Urgente')),   # Traitement immédiat
    ]
    
    # Statuts des services
    STATUS_CHOICES = [
        ('active', _('Actif')),         # Service disponible
        ('inactive', _('Inactif')),     # Temporairement indisponible
        ('maintenance', _('Maintenance')), # En maintenance
        ('seasonal', _('Saisonnier')),  # Disponible certaines périodes
    ]
    
    # Identifiant unique
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Organisation qui offre ce service
    organization = models.ForeignKey(
        'business.Organization',
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name=_('Organisation')
    )
    
    # Catégorie du service
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='services',
        verbose_name=_('Catégorie')
    )
    
    # Informations de base
    name = models.CharField(
        max_length=200,
        verbose_name=_('Nom du service'),
        help_text=_('Ex: Ouverture compte épargne, Consultation générale')
    )
    
    code = models.CharField(
        max_length=20,
        verbose_name=_('Code service'),
        help_text=_('Code unique (ex: OUVCPT, CONSGEN, DEMPASS)')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description détaillée du service')
    )
    
    # Instructions pour le client
    instructions = models.TextField(
        blank=True,
        verbose_name=_('Instructions client'),
        help_text=_('Instructions à afficher au client avant la prise de ticket')
    )
    
    # Configuration du service
    default_priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='low',
        verbose_name=_('Priorité par défaut')
    )
    
    # Temps estimé de traitement (en minutes)
    estimated_duration = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(180)],
        verbose_name=_('Durée estimée (min)'),
        help_text=_('Temps moyen de traitement en minutes')
    )
    
    # Temps maximum d'attente acceptable (en minutes)
    max_wait_time = models.PositiveIntegerField(
        default=60,
        validators=[MinValueValidator(5), MaxValueValidator(480)],
        verbose_name=_('Attente max (min)'),
        help_text=_('Temps d\'attente maximum acceptable')
    )
    
    # Coût du service (optionnel, en FCFA)
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_('Coût (FCFA)'),
        help_text=_('Coût du service en FCFA (optionnel)')
    )
    
    # Configuration rendez-vous
    allows_appointments = models.BooleanField(
        default=True,
        verbose_name=_('Accepte les RDV'),
        help_text=_('Les clients peuvent-ils prendre rendez-vous ?')
    )
    
    requires_appointment = models.BooleanField(
        default=False,
        verbose_name=_('RDV obligatoire'),
        help_text=_('Le service nécessite-t-il obligatoirement un RDV ?')
    )
    
    # Délai minimum pour prendre RDV (en heures)
    min_appointment_notice = models.PositiveIntegerField(
        default=2,
        verbose_name=_('Délai min RDV (h)'),
        help_text=_('Nombre d\'heures minimum à l\'avance pour un RDV')
    )
    
    # Délai maximum pour prendre RDV (en jours)
    max_appointment_advance = models.PositiveIntegerField(
        default=30,
        verbose_name=_('Délai max RDV (j)'),
        help_text=_('Nombre de jours maximum à l\'avance pour un RDV')
    )
    
    # Documents requis (JSON)
    required_documents = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Documents obligatoires'),
        help_text=_('Liste des documents requis: ["CNI", "Justificatif domicile"]')
    )
    
    # Documents optionnels (JSON)
    optional_documents = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Documents optionnels'),
        help_text=_('Liste des documents optionnels')
    )
    
    # Horaires spécifiques du service (JSON)
    service_hours = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Horaires du service'),
        help_text=_('Horaires spécifiques par jour: {"monday": {"start": "08:00", "end": "17:00"}}')
    )
    
    # Configuration notifications
    sms_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Notifications SMS'),
        help_text=_('Envoyer des SMS pour ce service ?')
    )
    
    push_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Notifications push'),
        help_text=_('Envoyer des notifications push ?')
    )
    
    # Template de message SMS personnalisé
    sms_template = models.TextField(
        blank=True,
        verbose_name=_('Template SMS'),
        help_text=_('Template personnalisé: "Bonjour {name}, votre ticket {ticket_number}..."')
    )
    
    # Statut et visibilité
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name=_('Statut')
    )
    
    # Ordre d'affichage dans la liste
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Ordre d\'affichage')
    )
    
    # Service visible par les clients
    is_public = models.BooleanField(
        default=True,
        verbose_name=_('Visible publiquement'),
        help_text=_('Les clients peuvent-ils voir ce service ?')
    )
    
    # Service nécessitant une authentification
    requires_authentication = models.BooleanField(
        default=False,
        verbose_name=_('Authentification requise'),
        help_text=_('L\'utilisateur doit-il être connecté ?')
    )
    
    # Statistiques
    total_tickets_issued = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total tickets émis'),
        help_text=_('Nombre total de tickets pris pour ce service')
    )
    
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=0.0,
        verbose_name=_('Note moyenne'),
        help_text=_('Note moyenne donnée par les clients (sur 5)')
    )
    
    total_ratings = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Nombre d\'évaluations'),
        help_text=_('Nombre total d\'évaluations reçues')
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Service')
        verbose_name_plural = _('Services')
        unique_together = ['organization', 'code']
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['category', 'is_public']),
            models.Index(fields=['requires_appointment']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.name}"
    
    @property
    def is_available(self):
        """Vérifie si le service est disponible"""
        return self.status == 'active' and self.is_public
    
    @property
    def average_wait_time(self):
        """Calcule le temps d'attente moyen basé sur les tickets récents"""
        # Pour l'instant, on retourne la durée estimée
        # Plus tard, on calculera avec les vraies données
        return self.estimated_duration
