# apps/payments/admin.py
"""
Administration Django pour les paiements SmartQueue
Gestion complète des providers, paiements, plans et factures
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from decimal import Decimal

from .models import (
    PaymentProvider, Payment, PaymentMethod, PaymentLog,
    PaymentPlan, SubscriptionInvoice
)


@admin.register(PaymentProvider)
class PaymentProviderAdmin(admin.ModelAdmin):
    """
    Administration des fournisseurs de paiement (Wave, Orange Money, etc.)
    """
    list_display = [
        'status_icon', 'name', 'provider_type', 'supported_currency',
        'min_amount', 'max_amount', 'is_default', 'priority', 'is_active'
    ]
    list_filter = ['provider_type', 'is_active', 'is_default', 'supported_currency']
    search_fields = ['name', 'provider_type']
    ordering = ['priority', 'name']

    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'provider_type', 'supported_currency', 'is_active', 'is_default', 'priority')
        }),
        ('Configuration API', {
            'fields': ('api_url', 'api_key', 'api_secret', 'merchant_id'),
            'classes': ('collapse',),
            'description': 'Informations sensibles - Ne pas partager'
        }),
        ('Limites et frais', {
            'fields': ('min_amount', 'max_amount', 'transaction_fee_fixed', 'transaction_fee_percent')
        }),
    )

    readonly_fields = ['uuid', 'created_at', 'updated_at']

    def status_icon(self, obj):
        """Icône de statut du provider"""
        if obj.is_active:
            color = 'green' if obj.is_default else 'orange'
            icon = '✓' if obj.is_default else '●'
            return format_html(
                '<span style="color: {};">{}</span>',
                color, icon
            )
        return format_html('<span style="color: red;">✗</span>')

    status_icon.short_description = 'Statut'

    def save_model(self, request, obj, form, change):
        """Assurer qu'un seul provider par défaut"""
        if obj.is_default:
            PaymentProvider.objects.filter(
                provider_type=obj.provider_type,
                is_default=True
            ).exclude(id=obj.id).update(is_default=False)
        super().save_model(request, obj, form, change)


class PaymentLogInline(admin.TabularInline):
    """Logs inline pour les paiements"""
    model = PaymentLog
    extra = 0
    readonly_fields = ['action', 'details', 'http_status', 'response_time_ms', 'created_at']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Administration des paiements B2C (clients → organisations)
    """
    list_display = [
        'payment_number', 'customer_name', 'organization_name',
        'total_amount', 'currency', 'status_badge', 'provider_name',
        'created_at', 'expires_at'
    ]
    list_filter = [
        'status', 'provider__provider_type', 'payment_type',
        'currency', 'created_at', 'organization'
    ]
    search_fields = [
        'payment_number', 'external_reference', 'customer__phone',
        'customer__first_name', 'customer__last_name', 'payer_phone'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Paiement', {
            'fields': ('payment_number', 'external_reference', 'status', 'provider', 'organization')
        }),
        ('Client', {
            'fields': ('customer', 'payer_phone', 'payer_name')
        }),
        ('Montants', {
            'fields': ('amount', 'fees', 'total_amount', 'currency')
        }),
        ('Objet lié', {
            'fields': ('payment_type', 'ticket', 'appointment', 'invoice', 'description')
        }),
        ('Timeline', {
            'fields': ('created_at', 'processed_at', 'completed_at', 'expires_at'),
            'classes': ('collapse',)
        }),
        ('Technique', {
            'fields': ('callback_url', 'return_url', 'metadata', 'error_code', 'error_message', 'created_ip'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = [
        'uuid', 'payment_number', 'created_at', 'processed_at',
        'completed_at', 'updated_at', 'created_ip'
    ]

    inlines = [PaymentLogInline]

    def customer_name(self, obj):
        """Nom du client"""
        return obj.customer.get_full_name() or obj.payer_name
    customer_name.short_description = 'Client'

    def organization_name(self, obj):
        """Nom de l'organisation"""
        return obj.organization.trade_name
    organization_name.short_description = 'Organisation'

    def provider_name(self, obj):
        """Nom du provider"""
        return obj.provider.name
    provider_name.short_description = 'Provider'

    def status_badge(self, obj):
        """Badge coloré du statut"""
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
            'refunded': 'purple',
            'expired': 'darkred'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'

    def has_delete_permission(self, request, obj=None):
        """Empêcher suppression des paiements complétés"""
        if obj and obj.status == 'completed':
            return False
        return super().has_delete_permission(request, obj)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """
    Administration des méthodes de paiement sauvegardées
    """
    list_display = [
        'user_name', 'provider_name', 'phone_number',
        'is_default', 'is_verified', 'last_used_at'
    ]
    list_filter = ['provider', 'is_default', 'is_verified']
    search_fields = ['user__phone', 'user__first_name', 'user__last_name', 'phone_number']

    def user_name(self, obj):
        return obj.user.get_full_name()
    user_name.short_description = 'Utilisateur'

    def provider_name(self, obj):
        return obj.provider.name
    provider_name.short_description = 'Provider'


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    """
    Administration des logs de paiement (lecture seule)
    """
    list_display = [
        'payment_number', 'action_badge', 'http_status',
        'response_time_ms', 'created_at'
    ]
    list_filter = ['action', 'http_status', 'created_at']
    search_fields = ['payment__payment_number', 'payment__external_reference']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    readonly_fields = ['payment', 'action', 'details', 'http_status', 'response_time_ms', 'created_at']

    def payment_number(self, obj):
        """Numéro de paiement avec lien"""
        url = reverse('admin:payments_payment_change', args=[obj.payment.id])
        return format_html('<a href="{}">{}</a>', url, obj.payment.payment_number)
    payment_number.short_description = 'Paiement'

    def action_badge(self, obj):
        """Badge coloré de l'action"""
        colors = {
            'initiated': 'blue',
            'sent_to_provider': 'orange',
            'callback_received': 'purple',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.action, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = 'Action'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    """
    Administration des plans de tarification B2B
    """
    list_display = [
        'name', 'plan_type', 'monthly_fee', 'annual_fee',
        'fee_per_ticket', 'fee_per_sms', 'is_active'
    ]
    list_filter = ['plan_type', 'is_active', 'has_premium_support', 'has_analytics']
    search_fields = ['name']

    fieldsets = (
        ('Plan', {
            'fields': ('name', 'plan_type', 'is_active')
        }),
        ('Tarification', {
            'fields': ('monthly_fee', 'annual_fee', 'fee_per_ticket', 'fee_per_sms')
        }),
        ('Limites', {
            'fields': ('max_tickets_per_month', 'max_sms_per_month')
        }),
        ('Fonctionnalités', {
            'fields': ('has_premium_support', 'has_analytics', 'has_custom_branding')
        })
    )


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    """
    Administration des factures d'abonnement B2B
    """
    list_display = [
        'invoice_number', 'organization_name', 'plan_name',
        'amount', 'status_badge', 'due_date', 'paid_at'
    ]
    list_filter = ['status', 'plan', 'due_date', 'created_at']
    search_fields = ['invoice_number', 'organization__name', 'organization__trade_name']
    date_hierarchy = 'due_date'
    ordering = ['-due_date']

    fieldsets = (
        ('Facture', {
            'fields': ('invoice_number', 'organization', 'plan', 'amount', 'status')
        }),
        ('Période', {
            'fields': ('billing_period_start', 'billing_period_end', 'due_date')
        }),
        ('Paiement', {
            'fields': ('paid_at', 'last_reminder_sent_at')
        })
    )

    readonly_fields = ['uuid', 'invoice_number', 'created_at', 'updated_at']

    def organization_name(self, obj):
        return obj.organization.trade_name
    organization_name.short_description = 'Organisation'

    def plan_name(self, obj):
        return obj.plan.name
    plan_name.short_description = 'Plan'

    def status_badge(self, obj):
        """Badge coloré du statut"""
        colors = {
            'due': 'orange',
            'paid': 'green',
            'overdue': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'

    def has_delete_permission(self, request, obj=None):
        """Empêcher suppression des factures payées"""
        if obj and obj.status == 'paid':
            return False
        return super().has_delete_permission(request, obj)
