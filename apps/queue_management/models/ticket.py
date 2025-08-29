# ==============================================
# apps/queue_management/models/ticket.py - Tickets virtuels (app unifiée)
# ==============================================

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
import uuid

class Ticket(models.Model):
    """
    Ticket virtuel pour une file d'attente
    
    Exemple concret :
    - Ticket "A012" pris par Aminata Diop
    - Pour le service "Ouverture compte" chez BHS Dakar
    - À 14h30, expire à 15h00
    """
    
    # Statuts des tickets
    STATUS_CHOICES = [
        ('waiting', _('En attente')),       # Client attend dans la file
        ('called', _('Appelé')),           # Numéro appelé, client doit venir
        ('serving', _('En cours de service')), # Client en train d'être servi
        ('served', _('Servi')),            # Service terminé avec succès
        ('cancelled', _('Annulé')),        # Annulé par le client
        ('expired', _('Expiré')),          # Ticket a expiré
        ('no_show', _('Absent')),          # Client ne s'est pas présenté
        ('transferred', _('Transféré')),   # Transféré vers autre file
    ]
    
    # Canaux de création du ticket
    CREATION_CHANNELS = [
        ('mobile', _('Application mobile')),   # SmartQueue mobile app
        ('web', _('Site web')),               # Site web SmartQueue
        ('sms', _('SMS')),                    # Via SMS (téléphones basiques)
        ('kiosk', _('Borne tactile')),        # Borne dans l'établissement
        ('counter', _('Au guichet')),         # Créé par l'agent
        ('phone', _('Téléphone')),            # Par appel téléphonique
    ]
    
    # Priorités
    PRIORITY_LEVELS = [
        ('low', _('Normale')),      # Client standard
        ('medium', _('Moyenne')),   # Un peu prioritaire
        ('high', _('Élevée')),      # Personne âgée, handicapée
        ('urgent', _('Urgente')),   # Urgence médicale, etc.
    ]
    
    # Identifiant unique
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Numéro de ticket lisible (A001, B012, etc.)
    ticket_number = models.CharField(
        max_length=20,
        verbose_name=_('Numéro de ticket'),
        help_text=_('Numéro affiché au client (ex: A001, B012)')
    )
    
    # File d'attente associée
    queue = models.ForeignKey(
        'queue_management.Queue',
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_('File d\'attente')
    )
    
    # Service demandé
    service = models.ForeignKey(
        'business.Service',
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_('Service')
    )
    
    # Client qui a pris le ticket
    customer = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='tickets',
        verbose_name=_('Client')
    )
    
    # Configuration du ticket
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_LEVELS,
        default='low',
        verbose_name=_('Priorité')
    )
    
    creation_channel = models.CharField(
        max_length=20,
        choices=CREATION_CHANNELS,
        default='mobile',
        verbose_name=_('Canal de création')
    )
    
    # Notes du client
    customer_notes = models.TextField(
        blank=True,
        max_length=500,
        verbose_name=_('Notes du client'),
        help_text=_('Notes ou demandes spéciales du client')
    )
    
    # Documents apportés (JSON)
    documents_brought = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Documents apportés'),
        help_text=_('Liste des documents que le client a apportés')
    )
    
    # Statut et traitement
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='waiting',
        verbose_name=_('Statut')
    )
    
    # Position dans la file d'attente
    queue_position = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Position dans la file')
    )
    
    # Agent qui traite le ticket
    serving_agent = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='served_tickets',
        verbose_name=_('Agent'),
        help_text=_('Agent qui sert ce client')
    )
    
    # Timestamps importants
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Créé le')
    )
    
    called_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Appelé le')
    )
    
    service_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Service commencé le')
    )
    
    service_ended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Service terminé le')
    )
    
    expires_at = models.DateTimeField(
        verbose_name=_('Expire le'),
        help_text=_('Date/heure d\'expiration du ticket')
    )
    
    # Métriques calculées
    wait_time_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Temps d\'attente (min)')
    )
    
    service_time_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Temps de service (min)')
    )
    
    call_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Nombre d\'appels'),
        help_text=_('Nombre de fois que ce ticket a été appelé')
    )
    
    # Notifications envoyées (JSON)
    notifications_sent = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Notifications envoyées')
    )
    
    # IP de création (pour sécurité)
    created_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('Adresse IP de création')
    )
    
    # Dernière mise à jour
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Ticket')
        verbose_name_plural = _('Tickets')
        db_table = 'tickets_ticket'
        unique_together = ['queue', 'ticket_number']
        indexes = [
            models.Index(fields=['queue', 'status']),
            models.Index(fields=['customer', 'created_at']),
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['priority', 'created_at']
    
    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.service.name}"
    
    def save(self, *args, **kwargs):
        """Surcharge pour générer le numéro de ticket et la date d'expiration"""
        if not self.ticket_number:
            # Générer le numéro de ticket (A001, A002, etc.)
            self.ticket_number = self.generate_ticket_number()
        
        if not self.expires_at:
            # Définir la date d'expiration
            self.expires_at = timezone.now() + timedelta(
                minutes=self.queue.ticket_expiry_time
            )
        
        super().save(*args, **kwargs)
    
    def generate_ticket_number(self):
        """Génère un numéro de ticket unique"""
        # Format: A001, A002, etc. (A = première lettre du service)
        service_letter = self.service.code[:1].upper() if self.service.code else 'T'
        number = self.queue.get_next_ticket_number()
        return f"{service_letter}{number:03d}"
    
    @property
    def is_expired(self):
        """Vérifie si le ticket est expiré"""
        return timezone.now() > self.expires_at and self.status == 'waiting'
    
    @property
    def estimated_call_time(self):
        """Estime l'heure d'appel du ticket"""
        if self.status != 'waiting':
            return None
        
        # Calcul basé sur la position et le temps de service moyen
        minutes_to_wait = (self.queue_position - 1) * self.service.estimated_duration
        return timezone.now() + timedelta(minutes=minutes_to_wait)
