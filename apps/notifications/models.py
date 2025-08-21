# apps/notifications/models.py
"""
Modèles pour les notifications SmartQueue
Gestion SMS, Push, Email pour tickets et RDV sénégalais
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.validators import RegexValidator
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class NotificationTemplate(models.Model):
    """
    Templates de notifications (SMS, Email, Push)
    
    Exemples :
    - "Votre ticket #{ticket_number} est appelé. Présentez-vous au guichet {window_number}"
    - "RDV confirmé le {date} à {time} chez {organization}. ID: {appointment_number}"
    - "File d'attente {queue_name}: {waiting_count} personnes devant vous"
    """
    
    TYPE_CHOICES = [
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('push', 'Notification Push'),
        ('web', 'Notification Web')
    ]
    
    CATEGORY_CHOICES = [
        # Tickets
        ('ticket_created', 'Ticket créé'),
        ('ticket_called', 'Ticket appelé'),
        ('ticket_completed', 'Service terminé'),
        ('ticket_cancelled', 'Ticket annulé'),
        ('queue_position_update', 'Position mise à jour'),
        
        # Rendez-vous
        ('appointment_created', 'RDV créé'),
        ('appointment_confirmed', 'RDV confirmé'),
        ('appointment_reminder', 'Rappel RDV'),
        ('appointment_cancelled', 'RDV annulé'),
        ('appointment_rescheduled', 'RDV reporté'),
        
        # File d'attente
        ('queue_opened', 'File ouverte'),
        ('queue_closed', 'File fermée'),
        ('queue_full', 'File complète'),
        
        # Système
        ('account_created', 'Compte créé'),
        ('password_reset', 'Reset mot de passe'),
        ('system_maintenance', 'Maintenance système'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    name = models.CharField(
        max_length=100,
        verbose_name="Nom du template",
        help_text="Ex: SMS Ticket Appelé"
    )
    
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        verbose_name="Catégorie",
        help_text="Type d'événement notifié"
    )
    
    notification_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name="Type de notification"
    )
    
    # Contenu multilingue (Français/Wolof)
    subject_fr = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Sujet (Français)",
        help_text="Pour emails uniquement"
    )
    
    subject_wo = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Sujet (Wolof)",
        help_text="Pour emails uniquement"
    )
    
    message_fr = models.TextField(
        verbose_name="Message (Français)",
        help_text="Variables: {ticket_number}, {organization}, {queue_name}, {position}, etc."
    )
    
    message_wo = models.TextField(
        blank=True,
        verbose_name="Message (Wolof)",
        help_text="Traduction wolof du message"
    )
    
    # Configuration
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
    send_immediately = models.BooleanField(
        default=True,
        verbose_name="Envoyer immédiatement",
        help_text="Si False, sera programmé"
    )
    
    delay_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name="Délai (minutes)",
        help_text="Délai avant envoi (pour rappels)"
    )
    
    # Métadonnées
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Créé par"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Template de notification"
        verbose_name_plural = "Templates de notifications"
        unique_together = [('category', 'notification_type')]
        ordering = ['category', 'notification_type']
    
    def __str__(self):
        return f"{self.name} ({self.get_notification_type_display()})"
    
    def get_message(self, language='fr'):
        """Retourne le message dans la langue demandée"""
        if language == 'wo' and self.message_wo:
            return self.message_wo
        return self.message_fr
    
    def get_subject(self, language='fr'):
        """Retourne le sujet dans la langue demandée"""
        if language == 'wo' and self.subject_wo:
            return self.subject_wo
        return self.subject_fr or ""


class Notification(models.Model):
    """
    Instance de notification envoyée à un utilisateur
    
    Chaque notification créée correspond à un envoi réel
    (SMS, email, push) vers un utilisateur spécifique
    """
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('queued', 'En file d\'attente'),
        ('sending', 'En cours d\'envoi'),
        ('sent', 'Envoyé'),
        ('delivered', 'Livré'),
        ('read', 'Lu'),
        ('failed', 'Échec'),
        ('cancelled', 'Annulé'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('normal', 'Normale'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Destinataire
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_notifications',
        verbose_name="Destinataire"
    )
    
    # Template utilisé
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        verbose_name="Template"
    )
    
    # Objet lié (Ticket, Appointment, Queue, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="Type d'objet"
    )
    object_id = models.PositiveIntegerField(verbose_name="ID de l'objet")
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Contenu personnalisé (après template processing)
    subject = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Sujet final"
    )
    
    message = models.TextField(
        verbose_name="Message final",
        help_text="Message après remplacement des variables"
    )
    
    # Destination finale
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(regex=r'^\+221[0-9]{9}$', message="Format: +221XXXXXXXXX")],
        verbose_name="Numéro SMS",
        help_text="Pour notifications SMS"
    )
    
    email_address = models.EmailField(
        blank=True,
        verbose_name="Email",
        help_text="Pour notifications email"
    )
    
    push_token = models.TextField(
        blank=True,
        verbose_name="Token Push",
        help_text="Token FCM pour notifications push"
    )
    
    # État et traçabilité
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name="Priorité"
    )
    
    # Timing
    scheduled_at = models.DateTimeField(
        verbose_name="Programmé pour",
        help_text="Quand envoyer la notification"
    )
    
    sent_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Envoyé le"
    )
    
    delivered_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Livré le"
    )
    
    read_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Lu le"
    )
    
    # Retries et erreurs
    attempt_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Tentatives"
    )
    
    max_attempts = models.PositiveIntegerField(
        default=3,
        verbose_name="Max tentatives"
    )
    
    last_error = models.TextField(
        blank=True,
        verbose_name="Dernière erreur"
    )
    
    # Réponses (pour SMS bidirectionnels)
    response_received = models.BooleanField(
        default=False,
        verbose_name="Réponse reçue"
    )
    
    response_text = models.TextField(
        blank=True,
        verbose_name="Texte de réponse"
    )
    
    response_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Réponse reçue le"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['template', 'status']),
            models.Index(fields=['scheduled_at', 'status']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.template.name} → {self.recipient.get_full_name()} ({self.status})"
    
    @property
    def is_overdue(self):
        """Notification en retard si pas envoyée après l'heure prévue + 30 min"""
        if self.status in ['sent', 'delivered', 'failed', 'cancelled']:
            return False
        
        return timezone.now() > self.scheduled_at + timedelta(minutes=30)
    
    @property
    def can_retry(self):
        """Peut réessayer si pas au maximum des tentatives"""
        return (
            self.status == 'failed' and 
            self.attempt_count < self.max_attempts
        )
    
    def mark_as_sent(self):
        """Marquer comme envoyé"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_delivered(self):
        """Marquer comme livré (callback opérateur SMS)"""
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_read(self):
        """Marquer comme lu (push notifications)"""
        self.status = 'read'
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at'])
    
    def mark_as_failed(self, error_message):
        """Marquer comme échoué avec message d'erreur"""
        self.status = 'failed'
        self.last_error = error_message
        self.attempt_count += 1
        self.save(update_fields=['status', 'last_error', 'attempt_count'])


class NotificationPreference(models.Model):
    """
    Préférences de notification par utilisateur
    
    Permet aux clients de choisir comment ils veulent être notifiés
    (SMS, email, push) et pour quels événements
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name="Utilisateur"
    )
    
    # Canaux préférés
    prefer_sms = models.BooleanField(
        default=True,
        verbose_name="SMS activés",
        help_text="Recevoir des SMS"
    )
    
    prefer_email = models.BooleanField(
        default=True,
        verbose_name="Emails activés",
        help_text="Recevoir des emails"
    )
    
    prefer_push = models.BooleanField(
        default=True,
        verbose_name="Notifications push activées"
    )
    
    prefer_web = models.BooleanField(
        default=True,
        verbose_name="Notifications web activées"
    )
    
    # Langue préférée
    language = models.CharField(
        max_length=5,
        choices=[('fr', 'Français'), ('wo', 'Wolof')],
        default='fr',
        verbose_name="Langue préférée"
    )
    
    # Notifications spécifiques (tickets)
    notify_ticket_called = models.BooleanField(
        default=True,
        verbose_name="Ticket appelé"
    )
    
    notify_position_update = models.BooleanField(
        default=False,
        verbose_name="Mise à jour position",
        help_text="Notifications fréquentes, peut déranger"
    )
    
    notify_queue_full = models.BooleanField(
        default=True,
        verbose_name="File complète"
    )
    
    # Notifications RDV
    notify_appointment_confirmed = models.BooleanField(
        default=True,
        verbose_name="RDV confirmé"
    )
    
    notify_appointment_reminder = models.BooleanField(
        default=True,
        verbose_name="Rappel RDV"
    )
    
    appointment_reminder_hours = models.PositiveIntegerField(
        default=24,
        verbose_name="Rappel RDV (heures avant)",
        help_text="Nombre d'heures avant le RDV pour le rappel"
    )
    
    # Horaires de réception
    quiet_hours_start = models.TimeField(
        default="22:00",
        verbose_name="Début heures silencieuses",
        help_text="Ne pas déranger après cette heure"
    )
    
    quiet_hours_end = models.TimeField(
        default="07:00",
        verbose_name="Fin heures silencieuses",
        help_text="Ne pas déranger avant cette heure"
    )
    
    # Contacts alternatifs
    emergency_phone = models.CharField(
        max_length=15,
        blank=True,
        validators=[RegexValidator(regex=r'^\+221[0-9]{9}$')],
        verbose_name="Téléphone urgence",
        help_text="Pour notifications urgentes si principal inaccessible"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notifications"
    
    def __str__(self):
        channels = []
        if self.prefer_sms:
            channels.append("SMS")
        if self.prefer_email:
            channels.append("Email")
        if self.prefer_push:
            channels.append("Push")
        
        return f"{self.user.get_full_name()} - {', '.join(channels) if channels else 'Aucun'}"
    
    def should_send_at_time(self, target_time):
        """Vérifier si on peut envoyer une notification à cette heure"""
        time_only = target_time.time()
        
        # Si heures silencieuses traversent minuit (ex: 22h-7h)
        if self.quiet_hours_start > self.quiet_hours_end:
            return not (time_only >= self.quiet_hours_start or time_only <= self.quiet_hours_end)
        else:
            return not (self.quiet_hours_start <= time_only <= self.quiet_hours_end)


class SMSProvider(models.Model):
    """
    Configuration des fournisseurs SMS sénégalais
    
    Supports : Orange SMS API, Free SMS, autres opérateurs locaux
    """
    
    name = models.CharField(
        max_length=50,
        verbose_name="Nom du fournisseur",
        help_text="Ex: Orange Sénégal, Free Senegal"
    )
    
    provider_type = models.CharField(
        max_length=20,
        choices=[
            ('orange', 'Orange SMS API'),
            ('free', 'Free SMS'),
            ('expresso', 'Expresso'),
            ('generic', 'Générique HTTP'),
        ],
        verbose_name="Type"
    )
    
    # Configuration API
    api_url = models.URLField(
        verbose_name="URL API",
        help_text="Endpoint pour envoyer SMS"
    )
    
    api_key = models.CharField(
        max_length=200,
        verbose_name="Clé API"
    )
    
    api_secret = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Secret API"
    )
    
    sender_name = models.CharField(
        max_length=11,
        verbose_name="Nom expéditeur",
        help_text="11 caractères max, ex: SmartQueue"
    )
    
    # Limitations
    rate_limit_per_minute = models.PositiveIntegerField(
        default=60,
        verbose_name="Limite par minute"
    )
    
    cost_per_sms = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=25.00,
        verbose_name="Coût par SMS (CFA)",
        help_text="Pour suivi des coûts"
    )
    
    # État
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
    is_primary = models.BooleanField(
        default=False,
        verbose_name="Fournisseur principal"
    )
    
    priority = models.PositiveIntegerField(
        default=1,
        verbose_name="Priorité",
        help_text="1 = plus haute priorité"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Fournisseur SMS"
        verbose_name_plural = "Fournisseurs SMS"
        ordering = ['priority', 'name']
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        primary = " (Principal)" if self.is_primary else ""
        return f"{status} {self.name}{primary}"


class NotificationLog(models.Model):
    """
    Journal des envois de notifications pour audit
    
    Conserve l'historique de tous les envois pour analytics,
    facturation, debugging, conformité RGPD
    """
    
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Notification"
    )
    
    action = models.CharField(
        max_length=20,
        choices=[
            ('created', 'Créée'),
            ('queued', 'Mise en file'),
            ('sent', 'Envoyée'),
            ('delivered', 'Livrée'),
            ('failed', 'Échec'),
            ('retry', 'Nouvel essai'),
            ('cancelled', 'Annulée'),
        ],
        verbose_name="Action"
    )
    
    details = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Détails",
        help_text="Métadonnées techniques (provider response, error codes, etc.)"
    )
    
    provider_used = models.ForeignKey(
        SMSProvider,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Fournisseur utilisé"
    )
    
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True, blank=True,
        verbose_name="Coût (CFA)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Journal de notification"
        verbose_name_plural = "Journal des notifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification} - {self.action} - {self.created_at.strftime('%d/%m %H:%M')}"