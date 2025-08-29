# ==============================================
# apps/queue_management/models/queue.py - Files d'attente (app unifiée)
# ==============================================

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
import uuid

class Queue(models.Model):
    """
    File d'attente pour un service spécifique dans une succursale
    
    Exemple concret :
    - BHS Dakar a une file pour "Ouverture comptes"
    - Hôpital Principal a une file pour "Consultation cardiologie"
    - Préfecture Thiès a une file pour "Demande CNI"
    """
    
    # Types de files d'attente
    QUEUE_TYPES = [
        ('normal', _('Normale')),       # File standard
        ('priority', _('Prioritaire')), # Pour personnes âgées, handicapées
        ('vip', _('VIP')),             # Clients premium
        ('appointment', _('Rendez-vous')), # Uniquement sur RDV
        ('express', _('Express')),      # Service rapide
    ]
    
    # Statuts des files d'attente
    STATUS_CHOICES = [
        ('active', _('Active')),        # File ouverte, clients peuvent prendre tickets
        ('paused', _('En pause')),      # Temporairement fermée (pause déjeuner)
        ('closed', _('Fermée')),        # Fermée (fin de journée, weekend)
        ('maintenance', _('Maintenance')), # En maintenance technique
    ]
    
    # Stratégies de traitement
    PROCESSING_STRATEGIES = [
        ('fifo', _('Premier arrivé, premier servi')),    # Standard
        ('priority', _('Par priorité')),                 # Urgents d'abord
        ('appointment_first', _('RDV en premier')),      # RDV avant tickets normaux
        ('mixed', _('Mixte')),                          # Combinaison
    ]
    
    # Identifiant unique
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Service pour lequel cette file existe
    service = models.ForeignKey(
        'business.Service',
        on_delete=models.CASCADE,
        related_name='queues',
        verbose_name=_('Service'),
        help_text=_('Service traité par cette file')
    )
    
    # Organisation (pour simplifier les requêtes)
    organization = models.ForeignKey(
        'business.Organization',
        on_delete=models.CASCADE,
        related_name='queues',
        verbose_name=_('Organisation')
    )
    
    # Nom de la file d'attente
    name = models.CharField(
        max_length=100,
        verbose_name=_('Nom de la file'),
        help_text=_('Ex: BHS Dakar - Ouverture comptes')
    )
    
    # Type de file
    queue_type = models.CharField(
        max_length=20,
        choices=QUEUE_TYPES,
        default='normal',
        verbose_name=_('Type de file')
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    
    # Configuration de la file
    processing_strategy = models.CharField(
        max_length=20,
        choices=PROCESSING_STRATEGIES,
        default='fifo',
        verbose_name=_('Stratégie de traitement')
    )
    
    # Capacité maximum de la file (0 = illimitée)
    max_capacity = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Capacité maximum'),
        help_text=_('0 pour capacité illimitée')
    )
    
    # Temps maximum d'attente (en minutes)
    max_wait_time = models.PositiveIntegerField(
        default=120,
        validators=[MinValueValidator(5)],
        verbose_name=_('Temps d\'attente max (min)')
    )
    
    # Délai d'expiration d'un ticket (en minutes)
    ticket_expiry_time = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(5)],
        verbose_name=_('Expiration ticket (min)'),
        help_text=_('Temps après lequel un ticket expire')
    )
    
    # Horaires d'ouverture de la file (JSON)
    opening_hours = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Horaires d\'ouverture'),
        help_text=_('Horaires par jour: {"monday": {"start": "08:00", "end": "17:00"}}')
    )
    
    # Statut actuel
    current_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='closed',
        verbose_name=_('Statut actuel')
    )
    
    # Compteurs de tickets
    last_ticket_number = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Dernier numéro de ticket'),
        help_text=_('Dernier numéro émis aujourd\'hui')
    )
    
    current_ticket_number = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Numéro de ticket actuel'),
        help_text=_('Numéro actuellement appelé')
    )
    
    waiting_tickets_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tickets en attente')
    )
    
    # Statistiques du jour
    stats_date = models.DateField(
        default=timezone.now,
        verbose_name=_('Date des statistiques')
    )
    
    daily_tickets_issued = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tickets émis aujourd\'hui')
    )
    
    daily_tickets_served = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tickets servis aujourd\'hui')
    )
    
    daily_average_wait_time = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Temps d\'attente moyen (min)')
    )
    
    # Configuration notifications
    notifications_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Notifications activées')
    )
    
    notify_before_turns = models.PositiveIntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_('Notifier X tours avant')
    )
    
    # Métadonnées
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('File d\'attente')
        verbose_name_plural = _('Files d\'attente')
        db_table = 'queues_queue'
        unique_together = ['service', 'organization', 'queue_type']
        indexes = [
            models.Index(fields=['organization', 'current_status']),
            models.Index(fields=['service', 'is_active']),
            models.Index(fields=['stats_date']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.service.name} ({self.get_queue_type_display()})"
    
    @property
    def is_open(self):
        """Vérifie si la file est ouverte"""
        return self.current_status == 'active' and self.is_active
    
    @property
    def estimated_wait_time(self):
        """Calcule le temps d'attente estimé pour un nouveau ticket"""
        if self.waiting_tickets_count == 0:
            return 0
        
        # Calcul simple : nombre de tickets × temps moyen du service
        return self.waiting_tickets_count * self.service.estimated_duration
    
    def get_next_ticket_number(self):
        """Génère le prochain numéro de ticket"""
        self.last_ticket_number += 1
        self.save(update_fields=['last_ticket_number'])
        return self.last_ticket_number


