# apps/appointments/models.py
"""
Modèles pour les rendez-vous SmartQueue Sénégal
Gestion des RDV pour banques, hôpitaux, administrations
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
import uuid


class AppointmentSlot(models.Model):
    """
    Créneaux horaires disponibles pour les rendez-vous
    
    Permet aux organisations de définir leurs disponibilités
    (ex: BHS - consultations conseiller de 9h à 17h)
    """
    
    # Identification
    uuid = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    
    # Relations
    organization = models.ForeignKey(
        'business.Organization',
        on_delete=models.CASCADE,
        related_name='appointment_slots',
        verbose_name=_('Organisation')
    )
    
    service = models.ForeignKey(
        'business.Service',
        on_delete=models.CASCADE,
        related_name='appointment_slots',
        verbose_name=_('Service')
    )
    
    # Informations du créneau
    day_of_week = models.IntegerField(
        choices=[
            (0, _('Lundi')),
            (1, _('Mardi')), 
            (2, _('Mercredi')),
            (3, _('Jeudi')),
            (4, _('Vendredi')),
            (5, _('Samedi')),
            (6, _('Dimanche')),
        ],
        verbose_name=_('Jour de la semaine'),
        help_text=_('0=Lundi, 6=Dimanche')
    )
    
    start_time = models.TimeField(
        verbose_name=_('Heure de début'),
        help_text=_('Format: 09:00')
    )
    
    end_time = models.TimeField(
        verbose_name=_('Heure de fin'),
        help_text=_('Format: 17:00')
    )
    
    slot_duration = models.IntegerField(
        default=30,
        validators=[MinValueValidator(15), MaxValueValidator(120)],
        verbose_name=_('Durée du créneau (minutes)'),
        help_text=_('Durée en minutes (15-120 min)')
    )
    
    max_appointments = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_('Nombre max de RDV par créneau'),
        help_text=_('Combien de personnes maximum par créneau')
    )
    
    # Configuration
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Actif')
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Créneau de RDV')
        verbose_name_plural = _('Créneaux de RDV')
        ordering = ['day_of_week', 'start_time']
        
        # Un service ne peut avoir qu'un seul créneau par jour/heure
        unique_together = ['organization', 'service', 'day_of_week', 'start_time']
    
    def __str__(self):
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        return f"{self.organization.trade_name} - {self.service.name} - {days[self.day_of_week]} {self.start_time}"
    
    def get_available_slots_for_date(self, date):
        """
        Retourne les créneaux disponibles pour une date donnée
        """
        if date.weekday() != self.day_of_week:
            return []
        
        slots = []
        current_time = datetime.combine(date, self.start_time)
        end_time = datetime.combine(date, self.end_time)
        
        while current_time < end_time:
            slot_end = current_time + timedelta(minutes=self.slot_duration)
            
            # Compter les RDV existants pour ce créneau
            existing_count = Appointment.objects.filter(
                appointment_slot=self,
                scheduled_date=date,
                scheduled_time=current_time.time(),
                status__in=['confirmed', 'checked_in']
            ).count()
            
            if existing_count < self.max_appointments:
                slots.append({
                    'time': current_time.time(),
                    'available_spots': self.max_appointments - existing_count,
                    'total_spots': self.max_appointments
                })
            
            current_time = slot_end
        
        return slots


class Appointment(models.Model):
    """
    Rendez-vous pris par les clients
    
    Exemple d'usage au Sénégal :
    - RDV conseiller bancaire BHS
    - RDV consultation cardiologie
    - RDV services administratifs
    """
    
    STATUS_CHOICES = [
        ('pending', _('En attente de confirmation')),
        ('confirmed', _('Confirmé')),
        ('cancelled', _('Annulé')),
        ('rescheduled', _('Reporté')),
        ('checked_in', _('Arrivé')),
        ('in_progress', _('En cours')),
        ('completed', _('Terminé')),
        ('no_show', _('Absent')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Normale')),
        ('medium', _('Importante')),
        ('high', _('Urgente')),
    ]
    
    # Identification
    uuid = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True
    )
    
    appointment_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name=_('Numéro de RDV'),
        help_text=_('Généré automatiquement (ex: RDV001)')
    )
    
    # Relations principales
    customer = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'customer'},
        related_name='appointments',
        verbose_name=_('Client')
    )
    
    appointment_slot = models.ForeignKey(
        AppointmentSlot,
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name=_('Créneau')
    )
    
    # Raccourcis (dénormalisés pour performance)
    organization = models.ForeignKey(
        'business.Organization',
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name=_('Organisation')
    )
    
    service = models.ForeignKey(
        'business.Service',
        on_delete=models.CASCADE,
        related_name='appointments',
        verbose_name=_('Service')
    )
    
    # Planification
    scheduled_date = models.DateField(
        verbose_name=_('Date du RDV'),
        help_text=_('Date prévue du rendez-vous')
    )
    
    scheduled_time = models.TimeField(
        verbose_name=_('Heure du RDV'),
        help_text=_('Heure prévue du rendez-vous')
    )
    
    # Statut et priorité
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Statut')
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='low',
        verbose_name=_('Priorité')
    )
    
    # Informations client
    customer_notes = models.TextField(
        blank=True,
        verbose_name=_('Notes du client'),
        help_text=_('Raison du RDV, besoins spéciaux, etc.')
    )
    
    customer_phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name=_('Téléphone de contact'),
        help_text=_('Au cas où différent du compte')
    )
    
    # Gestion par l'organisation
    assigned_staff = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'user_type__in': ['staff', 'admin']},
        related_name='assigned_appointments',
        verbose_name=_('Personnel assigné')
    )
    
    staff_notes = models.TextField(
        blank=True,
        verbose_name=_('Notes internes'),
        help_text=_('Notes pour le personnel')
    )
    
    # Timestamps des événements
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Créé le')
    )
    
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Confirmé le')
    )
    
    checked_in_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Arrivée le')
    )
    
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Commencé le')
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Terminé le')
    )
    
    # Notifications et rappels
    reminder_sent = models.BooleanField(
        default=False,
        verbose_name=_('Rappel envoyé')
    )
    
    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Rappel envoyé le')
    )
    
    confirmation_sent = models.BooleanField(
        default=False,
        verbose_name=_('Confirmation envoyée')
    )
    
    # Métadonnées
    created_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP de création')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modifié le')
    )
    
    class Meta:
        verbose_name = _('Rendez-vous')
        verbose_name_plural = _('Rendez-vous')
        ordering = ['-scheduled_date', '-scheduled_time']
        
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['organization', 'scheduled_date']),
            models.Index(fields=['service', 'scheduled_date']),
            models.Index(fields=['status', 'scheduled_date']),
        ]
    
    def __str__(self):
        return f"RDV {self.appointment_number} - {self.customer.get_full_name()} - {self.scheduled_date} {self.scheduled_time}"
    
    def save(self, *args, **kwargs):
        # Générer le numéro de RDV automatiquement
        if not self.appointment_number:
            self.appointment_number = self.generate_appointment_number()
        
        # Remplir les champs dénormalisés
        if self.appointment_slot:
            self.organization = self.appointment_slot.organization
            self.service = self.appointment_slot.service
        
        super().save(*args, **kwargs)
    
    def generate_appointment_number(self):
        """Générer un numéro de RDV unique"""
        from django.db import transaction
        
        with transaction.atomic():
            # Compter les RDV d'aujourd'hui
            today_count = Appointment.objects.filter(
                created_at__date=timezone.now().date()
            ).count() + 1
            
            # Format: RDV + date courte + numéro séquentiel
            date_str = timezone.now().strftime('%m%d')
            return f"RDV{date_str}{today_count:03d}"
    
    @property
    def is_upcoming(self):
        """Le RDV est-il à venir ?"""
        return self.scheduled_date >= timezone.now().date() and self.status in ['pending', 'confirmed']
    
    @property
    def is_today(self):
        """Le RDV est-il aujourd'hui ?"""
        return self.scheduled_date == timezone.now().date()
    
    @property
    def time_until_appointment(self):
        """Temps restant jusqu'au RDV"""
        if not self.is_upcoming:
            return None
        
        appointment_datetime = timezone.make_aware(
            datetime.combine(self.scheduled_date, self.scheduled_time)
        )
        
        return appointment_datetime - timezone.now()
    
    @property
    def can_be_cancelled(self):
        """Le RDV peut-il être annulé ?"""
        if self.status not in ['pending', 'confirmed']:
            return False
        
        # Ne peut pas être annulé si moins de 2 heures avant
        time_until = self.time_until_appointment
        if time_until and time_until.total_seconds() < 2 * 3600:  # 2 heures
            return False
        
        return True
    
    @property
    def can_be_rescheduled(self):
        """Le RDV peut-il être reporté ?"""
        return self.can_be_cancelled  # Même logique
    
    def confirm(self):
        """Confirmer le rendez-vous"""
        if self.status == 'pending':
            self.status = 'confirmed'
            self.confirmed_at = timezone.now()
            self.save()
            return True
        return False
    
    def cancel(self, reason=""):
        """Annuler le rendez-vous"""
        if self.can_be_cancelled:
            self.status = 'cancelled'
            if reason:
                self.staff_notes += f"\nAnnulé: {reason}"
            self.save()
            return True
        return False
    
    def check_in(self):
        """Marquer le client comme arrivé"""
        if self.status == 'confirmed' and self.is_today:
            self.status = 'checked_in'
            self.checked_in_at = timezone.now()
            self.save()
            return True
        return False
    
    def start_service(self):
        """Commencer le service"""
        if self.status == 'checked_in':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.save()
            return True
        return False
    
    def complete(self):
        """Terminer le service"""
        if self.status == 'in_progress':
            self.status = 'completed'
            self.completed_at = timezone.now()
            self.save()
            return True
        return False


class AppointmentHistory(models.Model):
    """
    Historique des modifications des rendez-vous
    Pour traçabilité et audit
    """
    
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name=_('Rendez-vous')
    )
    
    action = models.CharField(
        max_length=50,
        verbose_name=_('Action'),
        help_text=_('created, confirmed, cancelled, rescheduled, etc.')
    )
    
    old_value = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Ancienne valeur')
    )
    
    new_value = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Nouvelle valeur')
    )
    
    performed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        verbose_name=_('Effectué par')
    )
    
    reason = models.TextField(
        blank=True,
        verbose_name=_('Raison')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Date')
    )
    
    class Meta:
        verbose_name = _('Historique RDV')
        verbose_name_plural = _('Historique RDV')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.appointment.appointment_number} - {self.action} - {self.created_at}"