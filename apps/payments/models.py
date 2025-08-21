# apps/payments/models.py
"""
Modèles pour les paiements SmartQueue
Intégration Wave Money, Orange Money, Free Money sénégalais
"""

import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, RegexValidator
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class PaymentProvider(models.Model):
    """
    Fournisseurs de paiement mobile sénégalais
    
    Configuration des APIs Wave, Orange Money, Free Money, etc.
    """
    
    PROVIDER_TYPES = [
        ('wave', 'Wave Money'),
        ('orange_money', 'Orange Money'),
        ('free_money', 'Free Money'),
        ('wizall', 'Wizall Money'),
        ('wari', 'Wari'),
        ('postefinance', 'Poste Finance'),
        ('bank_transfer', 'Virement bancaire'),
        ('cash', 'Espèces'),
    ]
    
    CURRENCY_CHOICES = [
        ('XOF', 'Franc CFA (XOF)'),
        ('EUR', 'Euro'),
        ('USD', 'Dollar US'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    name = models.CharField(
        max_length=50,
        verbose_name="Nom du fournisseur",
        help_text="Ex: Wave Sénégal, Orange Money"
    )
    
    provider_type = models.CharField(
        max_length=20,
        choices=PROVIDER_TYPES,
        verbose_name="Type de fournisseur"
    )
    
    # Configuration API
    api_url = models.URLField(
        blank=True,
        verbose_name="URL API",
        help_text="Endpoint pour les paiements"
    )
    
    api_key = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Clé API"
    )
    
    api_secret = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Secret API"
    )
    
    merchant_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="ID Marchand",
        help_text="Identifiant marchand fourni par l'opérateur"
    )
    
    # Configuration
    supported_currency = models.CharField(
        max_length=5,
        choices=CURRENCY_CHOICES,
        default='XOF',
        verbose_name="Devise supportée"
    )
    
    min_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant minimum (CFA)",
        help_text="Montant minimum pour une transaction"
    )
    
    max_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('1000000.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant maximum (CFA)",
        help_text="Montant maximum pour une transaction"
    )
    
    transaction_fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Frais fixes (CFA)",
        help_text="Frais fixes par transaction"
    )
    
    transaction_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Frais en pourcentage",
        help_text="Frais en % du montant (ex: 1.5 pour 1.5%)"
    )
    
    # État
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name="Fournisseur par défaut"
    )
    
    priority = models.PositiveIntegerField(
        default=1,
        verbose_name="Priorité",
        help_text="1 = plus haute priorité"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Fournisseur de paiement"
        verbose_name_plural = "Fournisseurs de paiement"
        ordering = ['priority', 'name']
    
    def __str__(self):
        status = "✓" if self.is_active else "✗"
        default = " (Défaut)" if self.is_default else ""
        return f"{status} {self.name}{default}"
    
    def calculate_fees(self, amount):
        """Calculer les frais pour un montant donné"""
        fixed_fee = self.transaction_fee_fixed
        percent_fee = amount * (self.transaction_fee_percent / 100)
        return fixed_fee + percent_fee
    
    def is_amount_valid(self, amount):
        """Vérifier si le montant est dans les limites"""
        return self.min_amount <= amount <= self.max_amount


class Payment(models.Model):
    """
    Paiement effectué par un client
    
    Peut être lié à un ticket (paiement express) ou un RDV (prépaiement)
    """
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours de traitement'),
        ('completed', 'Complété'),
        ('failed', 'Échec'),
        ('cancelled', 'Annulé'),
        ('refunded', 'Remboursé'),
        ('expired', 'Expiré'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('ticket_fee', 'Frais de ticket'),
        ('appointment_fee', 'Frais de RDV'),
        ('service_fee', 'Frais de service'),
        ('penalty_fee', 'Pénalité (no-show)'),
        ('subscription_fee', 'Abonnement premium'),
        ('other', 'Autre'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Identifiants uniques
    payment_number = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name="Numéro de paiement",
        help_text="Généré automatiquement (ex: PAY001)"
    )
    
    external_reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Référence externe",
        help_text="ID de transaction chez le fournisseur"
    )
    
    # Relations
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name="Client"
    )
    
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.PROTECT,
        verbose_name="Fournisseur de paiement"
    )
    
    # Objets liés (optionnels)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        verbose_name="Organisation"
    )
    
    ticket = models.ForeignKey(
        'tickets.Ticket',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='payments',
        verbose_name="Ticket lié"
    )
    
    appointment = models.ForeignKey(
        'appointments.Appointment',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='payments',
        verbose_name="RDV lié"
    )
    
    # Détails du paiement
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='service_fee',
        verbose_name="Type de paiement"
    )
    
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Montant principal (CFA)",
        help_text="Montant hors frais"
    )
    
    fees = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Frais (CFA)",
        help_text="Frais de transaction"
    )
    
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Montant total (CFA)",
        help_text="Montant + frais"
    )
    
    currency = models.CharField(
        max_length=5,
        default='XOF',
        verbose_name="Devise"
    )
    
    # Informations de paiement
    payer_phone = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+221[0-9]{9}$', message="Format: +221XXXXXXXXX")],
        verbose_name="Téléphone payeur",
        help_text="Numéro mobile money"
    )
    
    payer_name = models.CharField(
        max_length=100,
        verbose_name="Nom du payeur"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Motif du paiement"
    )
    
    # État et traçabilité
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    
    # Timeline
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Traité le")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Complété le")
    expires_at = models.DateTimeField(verbose_name="Expire le")
    
    # Informations techniques
    callback_url = models.URLField(
        blank=True,
        verbose_name="URL de callback"
    )
    
    return_url = models.URLField(
        blank=True,
        verbose_name="URL de retour"
    )
    
    metadata = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Métadonnées",
        help_text="Données supplémentaires du fournisseur"
    )
    
    # Erreurs
    error_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Code d'erreur"
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name="Message d'erreur"
    )
    
    # Audit
    created_ip = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name="IP de création"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['payment_number']),
            models.Index(fields=['external_reference']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.payment_number} - {self.customer.get_full_name()} - {self.total_amount} CFA ({self.status})"
    
    def save(self, *args, **kwargs):
        # Générer le numéro de paiement si nouveau
        if not self.payment_number:
            self.payment_number = self._generate_payment_number()
        
        # Calculer le montant total
        if not self.total_amount:
            self.total_amount = self.amount + self.fees
        
        # Définir la date d'expiration (24h par défaut)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        
        super().save(*args, **kwargs)
    
    def _generate_payment_number(self):
        """Générer un numéro de paiement unique"""
        import time
        timestamp = int(time.time())
        return f"PAY{timestamp}"
    
    @property
    def is_expired(self):
        """Vérifier si le paiement a expiré"""
        return timezone.now() > self.expires_at and self.status == 'pending'
    
    @property
    def time_remaining(self):
        """Temps restant avant expiration"""
        if self.is_expired:
            return None
        return self.expires_at - timezone.now()
    
    def can_be_cancelled(self):
        """Vérifier si le paiement peut être annulé"""
        return self.status in ['pending', 'processing']
    
    def can_be_refunded(self):
        """Vérifier si le paiement peut être remboursé"""
        return self.status == 'completed'
    
    def mark_as_completed(self, external_reference=None, metadata=None):
        """Marquer le paiement comme complété"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if external_reference:
            self.external_reference = external_reference
        if metadata:
            self.metadata = metadata
        self.save(update_fields=['status', 'completed_at', 'external_reference', 'metadata'])
    
    def mark_as_failed(self, error_code=None, error_message=None):
        """Marquer le paiement comme échoué"""
        self.status = 'failed'
        if error_code:
            self.error_code = error_code
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['status', 'error_code', 'error_message'])


class PaymentMethod(models.Model):
    """
    Méthodes de paiement enregistrées par un utilisateur
    
    Permet de sauvegarder les numéros mobile money pour les réutiliser
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_methods',
        verbose_name="Utilisateur"
    )
    
    provider = models.ForeignKey(
        PaymentProvider,
        on_delete=models.CASCADE,
        verbose_name="Fournisseur"
    )
    
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+221[0-9]{9}$')],
        verbose_name="Numéro de téléphone"
    )
    
    holder_name = models.CharField(
        max_length=100,
        verbose_name="Nom du titulaire"
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name="Méthode par défaut"
    )
    
    is_verified = models.BooleanField(
        default=False,
        verbose_name="Vérifié",
        help_text="Numéro vérifié par une transaction test"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Méthode de paiement"
        verbose_name_plural = "Méthodes de paiement"
        unique_together = [('user', 'provider', 'phone_number')]
    
    def __str__(self):
        default = " (Défaut)" if self.is_default else ""
        verified = " ✓" if self.is_verified else ""
        return f"{self.provider.name} - {self.phone_number}{verified}{default}"


class PaymentLog(models.Model):
    """
    Journal des événements de paiement
    
    Trace toutes les interactions avec les APIs de paiement
    """
    
    ACTION_CHOICES = [
        ('initiated', 'Initié'),
        ('sent_to_provider', 'Envoyé au fournisseur'),
        ('callback_received', 'Callback reçu'),
        ('completed', 'Complété'),
        ('failed', 'Échec'),
        ('cancelled', 'Annulé'),
        ('refunded', 'Remboursé'),
        ('expired', 'Expiré'),
    ]
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Paiement"
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name="Action"
    )
    
    details = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Détails",
        help_text="Données de la requête/réponse API"
    )
    
    http_status = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Code HTTP"
    )
    
    response_time_ms = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Temps de réponse (ms)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Journal de paiement"
        verbose_name_plural = "Journal des paiements"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.payment.payment_number} - {self.action} - {self.created_at.strftime('%d/%m %H:%M')}"


class PaymentPlan(models.Model):
    """
    Plans de tarification pour les organisations
    
    Définit les frais par service ou par organisation
    """
    
    PLAN_TYPES = [
        ('free', 'Gratuit'),
        ('basic', 'Basique'),
        ('premium', 'Premium'),
        ('enterprise', 'Entreprise'),
        ('custom', 'Personnalisé'),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name="Nom du plan"
    )
    
    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPES,
        verbose_name="Type de plan"
    )
    
    # Frais par service
    ticket_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Frais par ticket (CFA)"
    )
    
    appointment_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Frais par RDV (CFA)"
    )
    
    no_show_penalty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Pénalité no-show (CFA)"
    )
    
    # Limites
    max_tickets_per_month = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Max tickets/mois",
        help_text="null = illimité"
    )
    
    max_appointments_per_month = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Max RDV/mois"
    )
    
    # Fonctionnalités
    has_premium_support = models.BooleanField(
        default=False,
        verbose_name="Support premium"
    )
    
    has_analytics = models.BooleanField(
        default=False,
        verbose_name="Analytics avancées"
    )
    
    has_custom_branding = models.BooleanField(
        default=False,
        verbose_name="Personnalisation de marque"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Actif"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Plan de tarification"
        verbose_name_plural = "Plans de tarification"
    
    def __str__(self):
        return f"{self.name} ({self.get_plan_type_display()})"