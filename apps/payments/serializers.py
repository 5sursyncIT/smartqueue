# apps/payments/serializers.py
"""
Serializers pour les paiements SmartQueue
APIs REST pour Wave Money, Orange Money, Free Money sénégalais
"""

from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from .models import (
    PaymentProvider, Payment, PaymentMethod, PaymentLog, PaymentPlan, SubscriptionInvoice
)


class PaymentProviderSerializer(serializers.ModelSerializer):
    """
    Serializer pour les fournisseurs de paiement (admin seulement)
    
    Usage : GET/POST /api/payment-providers/
    """
    
    provider_type_display = serializers.CharField(
        source='get_provider_type_display',
        read_only=True
    )
    
    currency_display = serializers.CharField(
        source='get_supported_currency_display',
        read_only=True
    )
    
    class Meta:
        model = PaymentProvider
        fields = [
            'id', 'uuid', 'name', 'provider_type', 'provider_type_display',
            'supported_currency', 'currency_display',
            'min_amount', 'max_amount', 'transaction_fee_fixed', 'transaction_fee_percent',
            'is_active', 'is_default', 'priority',
            'created_at', 'updated_at'
        ]
        # Masquer les clés API sensibles
        extra_kwargs = {
            'api_key': {'write_only': True},
            'api_secret': {'write_only': True},
            'api_url': {'write_only': True},
            'merchant_id': {'write_only': True}
        }


class PaymentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer un paiement
    
    Usage : POST /api/payments/
    """
    
    class Meta:
        model = Payment
        fields = [
            'provider', 'organization', 'ticket', 'appointment',
            'payment_type', 'amount', 'payer_phone', 'payer_name',
            'description', 'return_url'
        ]
    
    def validate_amount(self, value):
        """Valider le montant"""
        if value <= Decimal('0'):
            raise serializers.ValidationError("Le montant doit être positif.")
        
        # Montant maximum raisonnable (1 million CFA)
        if value > Decimal('1000000'):
            raise serializers.ValidationError("Montant trop élevé (max 1,000,000 CFA).")
        
        return value
    
    def validate_payer_phone(self, value):
        """Valider le numéro de téléphone"""
        if not value.startswith('+221'):
            raise serializers.ValidationError(
                "Le numéro doit être sénégalais (+221XXXXXXXXX)."
            )
        return value
    
    def validate(self, attrs):
        """Validation globale"""
        provider = attrs.get('provider')
        amount = attrs.get('amount')
        
        if provider and amount:
            # Vérifier les limites du fournisseur
            if not provider.is_amount_valid(amount):
                raise serializers.ValidationError({
                    'amount': f'Montant doit être entre {provider.min_amount} et {provider.max_amount} CFA'
                })
            
            # Calculer les frais
            fees = provider.calculate_fees(amount)
            attrs['fees'] = fees
            attrs['total_amount'] = amount + fees
        
        # Vérifier qu'un objet lié est fourni
        ticket = attrs.get('ticket')
        appointment = attrs.get('appointment')
        
        if not ticket and not appointment:
            raise serializers.ValidationError(
                "Le paiement doit être lié à un ticket ou un rendez-vous."
            )
        
        if ticket and appointment:
            raise serializers.ValidationError(
                "Le paiement ne peut être lié qu'à un seul objet (ticket OU RDV)."
            )
        
        return attrs
    
    def create(self, validated_data):
        """Créer le paiement"""
        # Ajouter le client connecté
        validated_data['customer'] = self.context['request'].user
        
        # Ajouter l'IP de création
        validated_data['created_ip'] = self.context['request'].META.get('REMOTE_ADDR')
        
        # Générer callback URL
        request = self.context['request']
        validated_data['callback_url'] = request.build_absolute_uri('/api/payments/callback/')
        
        return super().create(validated_data)


class PaymentListSerializer(serializers.ModelSerializer):
    """
    Serializer pour lister les paiements
    
    Usage : GET /api/payments/
    """
    
    provider_name = serializers.CharField(
        source='provider.name',
        read_only=True
    )
    
    provider_type = serializers.CharField(
        source='provider.get_provider_type_display',
        read_only=True
    )
    
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    payment_type_display = serializers.CharField(
        source='get_payment_type_display',
        read_only=True
    )
    
    organization_name = serializers.CharField(
        source='organization.trade_name',
        read_only=True
    )
    
    # Propriétés calculées
    is_expired = serializers.BooleanField(read_only=True)
    time_remaining = serializers.SerializerMethodField()
    can_be_cancelled = serializers.SerializerMethodField()
    can_be_refunded = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id', 'uuid', 'payment_number', 'external_reference',
            'provider_name', 'provider_type', 'organization_name',
            'payment_type', 'payment_type_display',
            'amount', 'fees', 'total_amount', 'currency',
            'status', 'status_display',
            'payer_phone', 'payer_name', 'description',
            'is_expired', 'time_remaining', 'can_be_cancelled', 'can_be_refunded',
            'created_at', 'expires_at', 'completed_at'
        ]
    
    def get_time_remaining(self, obj):
        """Temps restant avant expiration"""
        remaining = obj.time_remaining
        if remaining:
            total_seconds = int(remaining.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h{minutes:02d}m"
        return None
    
    def get_can_be_cancelled(self, obj):
        """Peut être annulé"""
        return obj.can_be_cancelled()
    
    def get_can_be_refunded(self, obj):
        """Peut être remboursé"""
        return obj.can_be_refunded()


class PaymentDetailSerializer(PaymentListSerializer):
    """
    Serializer pour les détails d'un paiement
    
    Usage : GET /api/payments/1/
    """
    
    linked_object_info = serializers.SerializerMethodField()
    
    class Meta(PaymentListSerializer.Meta):
        fields = PaymentListSerializer.Meta.fields + [
            'linked_object_info', 'callback_url', 'return_url',
            'error_code', 'error_message', 'metadata',
            'processed_at', 'updated_at'
        ]
    
    def get_linked_object_info(self, obj):
        """Informations sur l'objet lié"""
        if obj.ticket:
            return {
                'type': 'Ticket',
                'id': obj.ticket.id,
                'number': obj.ticket.ticket_number,
                'service': obj.ticket.service.name,
                'status': obj.ticket.get_status_display()
            }
        elif obj.appointment:
            return {
                'type': 'Rendez-vous',
                'id': obj.appointment.id,
                'number': obj.appointment.appointment_number,
                'service': obj.appointment.service.name,
                'date': obj.appointment.scheduled_date,
                'time': obj.appointment.scheduled_time
            }
        return None


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Serializer pour les méthodes de paiement sauvegardées
    
    Usage : GET/POST /api/payment-methods/
    """
    
    provider_name = serializers.CharField(
        source='provider.name',
        read_only=True
    )
    
    provider_type = serializers.CharField(
        source='provider.get_provider_type_display',
        read_only=True
    )
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'provider', 'provider_name', 'provider_type',
            'phone_number', 'holder_name', 'is_default', 'is_verified',
            'created_at', 'last_used_at'
        ]
    
    def validate_phone_number(self, value):
        """Valider le numéro de téléphone"""
        if not value.startswith('+221'):
            raise serializers.ValidationError(
                "Format sénégalais requis: +221XXXXXXXXX"
            )
        return value
    
    def create(self, validated_data):
        """Créer la méthode de paiement"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class InitiatePaymentSerializer(serializers.Serializer):
    """
    Serializer pour initier un paiement
    
    Usage : POST /api/payments/1/initiate/
    """
    
    confirm_phone = serializers.CharField(
        max_length=15,
        help_text="Confirmer le numéro de téléphone"
    )
    
    def validate_confirm_phone(self, value):
        """Valider la confirmation du numéro"""
        payment = self.context.get('payment')
        if payment and value != payment.payer_phone:
            raise serializers.ValidationError(
                "Le numéro ne correspond pas à celui du paiement."
            )
        return value


class PaymentStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques de paiements
    
    Usage : GET /api/payments/stats/
    """
    
    total_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    completed_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    
    total_amount_today = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_amount_week = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_amount_month = serializers.DecimalField(max_digits=15, decimal_places=2)
    
    total_fees_collected = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    success_rate = serializers.FloatField()
    average_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    
    payments_by_provider = serializers.JSONField()
    payments_by_type = serializers.JSONField()
    daily_stats = serializers.ListField()


class PaymentLogSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'historique des paiements
    
    Usage : GET /api/payments/1/logs/
    """
    
    action_display = serializers.CharField(
        source='get_action_display',
        read_only=True
    )
    
    class Meta:
        model = PaymentLog
        fields = [
            'id', 'action', 'action_display',
            'http_status', 'response_time_ms', 'details',
            'created_at'
        ]


class PaymentCallbackSerializer(serializers.Serializer):
    """
    Serializer pour les callbacks des fournisseurs
    
    Usage : POST /api/payments/callback/
    """
    
    payment_number = serializers.CharField(
        max_length=20,
        help_text="Numéro de paiement SmartQueue"
    )
    
    external_reference = serializers.CharField(
        max_length=100,
        help_text="Référence chez le fournisseur"
    )
    
    status = serializers.ChoiceField(
        choices=['completed', 'failed', 'cancelled'],
        help_text="Statut du paiement"
    )
    
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        help_text="Montant confirmé par le fournisseur"
    )
    
    fees = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Frais réels prélevés"
    )
    
    error_code = serializers.CharField(
        max_length=50,
        required=False,
        help_text="Code d'erreur (si échec)"
    )
    
    error_message = serializers.CharField(
        max_length=500,
        required=False,
        help_text="Message d'erreur (si échec)"
    )
    
    metadata = serializers.JSONField(
        required=False,
        help_text="Données supplémentaires du fournisseur"
    )
    
    def validate_payment_number(self, value):
        """Valider que le paiement existe"""
        try:
            Payment.objects.get(payment_number=value)
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Paiement non trouvé.")
        return value


class PaymentPlanSerializer(serializers.ModelSerializer):
    """
    Serializer pour les plans de tarification
    
    Usage : GET /api/payment-plans/
    """
    
    plan_type_display = serializers.CharField(
        source='get_plan_type_display',
        read_only=True
    )
    
    class Meta:
        model = PaymentPlan
        fields = [
            'id', 'name', 'plan_type', 'plan_type_display',
            'monthly_fee', 'annual_fee', 'fee_per_ticket', 'fee_per_sms',
            'max_tickets_per_month', 'max_sms_per_month',
            'has_premium_support', 'has_analytics', 'has_custom_branding',
            'is_active', 'created_at'
        ]


class SubscriptionInvoiceSerializer(serializers.ModelSerializer):
    """
    Serializer pour les factures d'abonnement (B2B).
    """
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = SubscriptionInvoice
        fields = [
            'id', 'uuid', 'invoice_number',
            'organization_name', 'plan_name',
            'amount', 'status', 'status_display',
            'billing_period_start', 'billing_period_end',
            'due_date', 'paid_at', 'created_at'
        ]


class QuickPaymentSerializer(serializers.Serializer):
    """
    Serializer pour les paiements rapides (ticket express)
    
    Usage : POST /api/payments/quick/
    """
    
    organization_id = serializers.IntegerField(
        help_text="ID de l'organisation"
    )
    
    service_id = serializers.IntegerField(
        help_text="ID du service"
    )
    
    provider_id = serializers.IntegerField(
        help_text="ID du fournisseur de paiement"
    )
    
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Montant à payer (CFA)"
    )
    
    payer_phone = serializers.CharField(
        max_length=15,
        help_text="Numéro mobile money (+221XXXXXXXXX)"
    )
    
    payer_name = serializers.CharField(
        max_length=100,
        help_text="Nom du payeur"
    )
    
    payment_type = serializers.ChoiceField(
        choices=Payment.PAYMENT_TYPE_CHOICES,
        default='service_fee'
    )
    
    create_ticket = serializers.BooleanField(
        default=True,
        help_text="Créer automatiquement un ticket après paiement"
    )
    
    def validate_amount(self, value):
        """Valider le montant"""
        if value <= Decimal('0'):
            raise serializers.ValidationError("Le montant doit être positif.")
        
        if value > Decimal('500000'):  # 500k CFA max pour paiement express
            raise serializers.ValidationError("Montant trop élevé pour paiement express.")
        
        return value
    
    def validate_payer_phone(self, value):
        """Valider le numéro"""
        if not value.startswith('+221'):
            raise serializers.ValidationError("Numéro sénégalais requis.")
        return value
    
    def validate(self, attrs):
        """Validation globale"""
        from apps.business.models import Organization, Service
        
        # Vérifier que l'organisation existe
        try:
            organization = Organization.objects.get(id=attrs['organization_id'])
        except Organization.DoesNotExist:
            raise serializers.ValidationError({'organization_id': 'Organisation non trouvée.'})
        
        # Vérifier que le service existe et appartient à l'organisation
        try:
            service = Service.objects.get(
                id=attrs['service_id'],
                organization=organization
            )
        except Service.DoesNotExist:
            raise serializers.ValidationError({
                'service_id': 'Service non trouvé dans cette organisation.'
            })
        
        # Vérifier que le fournisseur existe et est actif
        try:
            provider = PaymentProvider.objects.get(
                id=attrs['provider_id'],
                is_active=True
            )
        except PaymentProvider.DoesNotExist:
            raise serializers.ValidationError({
                'provider_id': 'Fournisseur de paiement non trouvé ou inactif.'
            })
        
        # Vérifier les limites du fournisseur
        amount = attrs['amount']
        if not provider.is_amount_valid(amount):
            raise serializers.ValidationError({
                'amount': f'Montant doit être entre {provider.min_amount} et {provider.max_amount} CFA'
            })
        
        attrs['organization'] = organization
        attrs['service'] = service
        attrs['provider'] = provider
        
        return attrs
