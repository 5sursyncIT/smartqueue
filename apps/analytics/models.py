# apps/analytics/models.py
"""
Modèles pour les analytics SmartQueue Sénégal
Métriques, KPIs et statistiques pour organisations
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Avg, Sum, Count, Max, Min
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

User = get_user_model()


class OrganizationMetrics(models.Model):
    """
    Métriques quotidiennes par organisation
    
    Agrège les stats de tous les services/files d'une organisation
    """
    
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Relations
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='metrics',
        verbose_name=_('Organisation')
    )
    
    # Date des métriques
    date = models.DateField(
        verbose_name=_('Date'),
        help_text=_('Date de ces statistiques')
    )
    
    # Métriques tickets
    tickets_issued = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tickets émis'),
        help_text=_('Nombre total de tickets pris ce jour')
    )
    
    tickets_served = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tickets servis'),
        help_text=_('Nombre de tickets traités avec succès')
    )
    
    tickets_cancelled = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tickets annulés'),
        help_text=_('Tickets annulés par clients')
    )
    
    tickets_expired = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tickets expirés'),
        help_text=_('Tickets expirés sans service')
    )
    
    tickets_no_show = models.PositiveIntegerField(
        default=0,
        verbose_name=_('No-show'),
        help_text=_('Clients ne s\'étant pas présentés')
    )
    
    # Métriques rendez-vous
    appointments_created = models.PositiveIntegerField(
        default=0,
        verbose_name=_('RDV créés')
    )
    
    appointments_completed = models.PositiveIntegerField(
        default=0,
        verbose_name=_('RDV terminés')
    )
    
    appointments_cancelled = models.PositiveIntegerField(
        default=0,
        verbose_name=_('RDV annulés')
    )
    
    appointments_no_show = models.PositiveIntegerField(
        default=0,
        verbose_name=_('RDV no-show')
    )
    
    # Métriques temps (en minutes)
    avg_wait_time = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Temps attente moyen (min)')
    )
    
    max_wait_time = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Temps attente max (min)')
    )
    
    avg_service_time = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Temps service moyen (min)')
    )
    
    # Métriques satisfaction
    total_ratings = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Nombre d\'évaluations')
    )
    
    avg_rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        default=Decimal('0.0'),
        verbose_name=_('Note moyenne'),
        help_text=_('Note moyenne sur 5')
    )
    
    # Métriques affluence
    peak_hour_start = models.TimeField(
        null=True, blank=True,
        verbose_name=_('Début heure de pointe')
    )
    
    peak_hour_end = models.TimeField(
        null=True, blank=True,
        verbose_name=_('Fin heure de pointe')
    )
    
    max_concurrent_customers = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Max clients simultanés')
    )
    
    # Métriques revenus (optionnel)
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Revenus totaux (CFA)')
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Métriques organisation')
        verbose_name_plural = _('Métriques organisations')
        unique_together = ['organization', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['organization', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.organization.name} - {self.date}"
    
    @property
    def success_rate(self):
        """Taux de succès des tickets"""
        if self.tickets_issued == 0:
            return 0
        return (self.tickets_served / self.tickets_issued) * 100
    
    @property
    def cancellation_rate(self):
        """Taux d'annulation"""
        if self.tickets_issued == 0:
            return 0
        return (self.tickets_cancelled / self.tickets_issued) * 100
    
    @property
    def no_show_rate(self):
        """Taux de no-show"""
        total_expected = self.tickets_issued + self.appointments_created
        total_no_show = self.tickets_no_show + self.appointments_no_show
        
        if total_expected == 0:
            return 0
        return (total_no_show / total_expected) * 100


class ServiceMetrics(models.Model):
    """
    Métriques quotidiennes par service
    
    Détail des performances de chaque service
    """
    
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Relations
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='metrics',
        verbose_name=_('Service')
    )
    
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='service_metrics',
        verbose_name=_('Organisation')
    )
    
    # Date des métriques
    date = models.DateField(verbose_name=_('Date'))
    
    # Métriques de base
    tickets_issued = models.PositiveIntegerField(default=0)
    tickets_served = models.PositiveIntegerField(default=0)
    tickets_cancelled = models.PositiveIntegerField(default=0)
    
    # Temps
    total_wait_time = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Temps attente total (min)')
    )
    
    total_service_time = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Temps service total (min)')
    )
    
    # Revenus
    revenue = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Revenus (CFA)')
    )
    
    # Satisfaction
    total_ratings = models.PositiveIntegerField(default=0)
    total_rating_score = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Métriques service')
        verbose_name_plural = _('Métriques services')
        unique_together = ['service', 'date']
        ordering = ['-date', 'service__name']
    
    def __str__(self):
        return f"{self.service.name} - {self.date}"
    
    @property
    def avg_wait_time(self):
        """Temps d'attente moyen"""
        if self.tickets_served == 0:
            return 0
        return self.total_wait_time / self.tickets_served
    
    @property
    def avg_service_time(self):
        """Temps de service moyen"""
        if self.tickets_served == 0:
            return 0
        return self.total_service_time / self.tickets_served
    
    @property
    def avg_rating(self):
        """Note moyenne"""
        if self.total_ratings == 0:
            return 0
        return self.total_rating_score / self.total_ratings


class QueueMetrics(models.Model):
    """
    Métriques horaires par file d'attente
    
    Suivi détaillé de l'affluence par heure
    """
    
    id = models.BigAutoField(primary_key=True)
    
    # Relations
    queue = models.ForeignKey(
        'queues.Queue',
        on_delete=models.CASCADE,
        related_name='metrics',
        verbose_name=_('File d\'attente')
    )
    
    # Timestamp précis
    timestamp = models.DateTimeField(
        verbose_name=_('Horodatage'),
        help_text=_('Heure précise de cette mesure')
    )
    
    # Métriques instantanées
    waiting_customers = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Clients en attente')
    )
    
    current_wait_time = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Temps attente actuel (min)')
    )
    
    tickets_issued_hour = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tickets émis cette heure')
    )
    
    tickets_served_hour = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Tickets servis cette heure')
    )
    
    # État de la file
    queue_status = models.CharField(
        max_length=20,
        verbose_name=_('Statut de la file')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Métriques file')
        verbose_name_plural = _('Métriques files')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['queue', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.queue.name} - {self.timestamp}"


class CustomerSatisfaction(models.Model):
    """
    Évaluations de satisfaction client
    """
    
    RATING_CHOICES = [
        (1, _('Très insatisfait')),
        (2, _('Insatisfait')),
        (3, _('Neutre')),
        (4, _('Satisfait')),
        (5, _('Très satisfait')),
    ]
    
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Relations
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='satisfaction_ratings',
        verbose_name=_('Client')
    )
    
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='satisfaction_ratings',
        verbose_name=_('Organisation')
    )
    
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='satisfaction_ratings',
        verbose_name=_('Service')
    )
    
    # Objet évalué (ticket ou RDV)
    ticket = models.ForeignKey(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='ratings',
        verbose_name=_('Ticket')
    )
    
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='ratings',
        verbose_name=_('Rendez-vous')
    )
    
    # Évaluation
    rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        verbose_name=_('Note'),
        help_text=_('Note de 1 à 5')
    )
    
    comment = models.TextField(
        blank=True,
        verbose_name=_('Commentaire'),
        help_text=_('Commentaire optionnel du client')
    )
    
    # Critères spécifiques
    wait_time_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        null=True, blank=True,
        verbose_name=_('Note temps d\'attente')
    )
    
    service_quality_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        null=True, blank=True,
        verbose_name=_('Note qualité service')
    )
    
    staff_friendliness_rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        null=True, blank=True,
        verbose_name=_('Note amabilité personnel')
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Satisfaction client')
        verbose_name_plural = _('Satisfactions clients')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['service', 'rating']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.service.name} - {self.rating}/5"


class DashboardWidget(models.Model):
    """
    Configuration des widgets pour dashboard personnalisé
    """
    
    WIDGET_TYPES = [
        ('kpi_card', _('Carte KPI')),
        ('line_chart', _('Graphique linéaire')),
        ('bar_chart', _('Graphique barres')),
        ('pie_chart', _('Graphique camembert')),
        ('table', _('Tableau')),
        ('map', _('Carte géographique')),
    ]
    
    id = models.BigAutoField(primary_key=True)
    
    # Configuration
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='dashboard_widgets',
        verbose_name=_('Utilisateur')
    )
    
    title = models.CharField(
        max_length=100,
        verbose_name=_('Titre du widget')
    )
    
    widget_type = models.CharField(
        max_length=20,
        choices=WIDGET_TYPES,
        verbose_name=_('Type de widget')
    )
    
    # Disposition
    position_x = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Position X')
    )
    
    position_y = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Position Y')
    )
    
    width = models.PositiveIntegerField(
        default=6,
        verbose_name=_('Largeur (colonnes)')
    )
    
    height = models.PositiveIntegerField(
        default=4,
        verbose_name=_('Hauteur (lignes)')
    )
    
    # Configuration données
    data_source = models.CharField(
        max_length=50,
        verbose_name=_('Source de données')
    )
    
    filters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Filtres')
    )
    
    display_options = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Options d\'affichage')
    )
    
    # État
    is_visible = models.BooleanField(
        default=True,
        verbose_name=_('Visible')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Widget dashboard')
        verbose_name_plural = _('Widgets dashboard')
        ordering = ['position_y', 'position_x']
    
    def __str__(self):
        return f"{self.title} ({self.user.username})"
