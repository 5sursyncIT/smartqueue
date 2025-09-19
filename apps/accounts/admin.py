# apps/accounts/admin.py
"""
Administration Django pour les utilisateurs SmartQueue
Interface complète pour gestion utilisateurs par type
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone

from .models import User


@admin.register(User)
class SmartQueueUserAdmin(UserAdmin):
    """
    Administration des utilisateurs SmartQueue
    Interface adaptée pour contexte sénégalais
    """

    # Affichage liste
    list_display = [
        'phone_number', 'get_full_name', 'user_type_badge',
        'preferred_language', 'phone_verified_icon', 'is_active_icon',
        'last_login', 'date_joined'
    ]

    list_filter = [
        'user_type', 'is_active', 'is_staff', 'is_superuser',
        'preferred_language', 'is_phone_verified', 'date_joined'
    ]

    search_fields = [
        'phone_number', 'first_name', 'last_name', 'email',
        'username', 'city'
    ]

    ordering = ['-date_joined']
    date_hierarchy = 'date_joined'

    # Configuration fieldsets
    fieldsets = (
        ('Informations de base', {
            'fields': ('username', 'password')
        }),
        ('Informations personnelles', {
            'fields': (
                'first_name', 'last_name', 'email', 'phone_number',
                'date_of_birth', 'gender', 'avatar'
            )
        }),
        ('Type et rôle', {
            'fields': ('user_type', 'preferred_language')
        }),
        ('Localisation', {
            'fields': ('city', 'address'),
            'classes': ('collapse',)
        }),
        ('Vérifications', {
            'fields': (
                'is_phone_verified', 'verification_code',
                'verification_code_expires'
            ),
            'classes': ('collapse',)
        }),
        ('Notifications', {
            'fields': (
                'push_notifications_enabled', 'sms_notifications_enabled',
                'email_notifications_enabled'
            ),
            'classes': ('collapse',)
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser',
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        ('Dates importantes', {
            'fields': ('last_login', 'date_joined', 'last_mobile_login'),
            'classes': ('collapse',)
        }),
    )

    # Configuration création utilisateur
    add_fieldsets = (
        ('Informations obligatoires', {
            'classes': ('wide',),
            'fields': (
                'username', 'phone_number', 'first_name', 'last_name',
                'user_type', 'password1', 'password2'
            ),
        }),
        ('Informations optionnelles', {
            'classes': ('wide', 'collapse'),
            'fields': ('email', 'preferred_language', 'city'),
        }),
    )

    readonly_fields = [
        'uuid', 'date_joined', 'last_login', 'last_mobile_login',
        'verification_code_expires'
    ]

    # Actions personnalisées
    actions = ['verify_phone', 'send_welcome_sms', 'reset_password_action']

    def user_type_badge(self, obj):
        """Badge coloré du type d'utilisateur"""
        colors = {
            'customer': '#28a745',     # Vert
            'staff': '#007bff',        # Bleu
            'admin': '#fd7e14',        # Orange
            'super_admin': '#dc3545'   # Rouge
        }
        color = colors.get(obj.user_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_user_type_display()
        )
    user_type_badge.short_description = 'Type'
    user_type_badge.admin_order_field = 'user_type'

    def phone_verified_icon(self, obj):
        """Icône vérification téléphone"""
        if obj.is_phone_verified:
            return format_html(
                '<span style="color: green; font-size: 16px;" title="Téléphone vérifié">✓</span>'
            )
        else:
            return format_html(
                '<span style="color: orange; font-size: 16px;" title="Téléphone non vérifié">⚠</span>'
            )
    phone_verified_icon.short_description = 'Tel'

    def is_active_icon(self, obj):
        """Icône statut actif"""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-size: 16px;" title="Utilisateur actif">●</span>'
            )
        else:
            return format_html(
                '<span style="color: red; font-size: 16px;" title="Utilisateur inactif">●</span>'
            )
    is_active_icon.short_description = 'Actif'

    def verify_phone(self, request, queryset):
        """Action : marquer téléphones comme vérifiés"""
        count = queryset.update(is_phone_verified=True)
        self.message_user(
            request,
            f'{count} utilisateur(s) marqué(s) comme téléphone vérifié.'
        )
    verify_phone.short_description = "Marquer téléphones comme vérifiés"

    def send_welcome_sms(self, request, queryset):
        """Action : envoyer SMS de bienvenue"""
        from apps.notifications.tasks import send_sms_notification

        count = 0
        for user in queryset:
            if user.phone_number and user.sms_notifications_enabled:
                message = f"Bienvenue sur SmartQueue {user.first_name} ! Votre compte est maintenant actif."
                # send_sms_notification.delay(
                #     phone=user.phone_number,
                #     message=message,
                #     notification_type='welcome'
                # )
                count += 1

        self.message_user(
            request,
            f'SMS de bienvenue envoyé à {count} utilisateur(s).'
        )
    send_welcome_sms.short_description = "Envoyer SMS de bienvenue"

    def reset_password_action(self, request, queryset):
        """Action : réinitialiser mots de passe"""
        count = 0
        for user in queryset:
            # Générer nouveau mot de passe temporaire
            import secrets
            import string
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
            user.set_password(temp_password)
            user.save()

            # Envoyer par SMS si possible
            if user.phone_number and user.sms_notifications_enabled:
                message = f"SmartQueue: Votre nouveau mot de passe temporaire est: {temp_password}"
                # send_sms_notification.delay(
                #     phone=user.phone_number,
                #     message=message,
                #     notification_type='password_reset'
                # )
            count += 1

        self.message_user(
            request,
            f'Mot de passe réinitialisé pour {count} utilisateur(s). SMS envoyés.'
        )
    reset_password_action.short_description = "Réinitialiser mots de passe"

    def get_queryset(self, request):
        """Optimiser requêtes avec select_related"""
        return super().get_queryset(request).select_related()

    def has_delete_permission(self, request, obj=None):
        """Empêcher suppression des super admins"""
        if obj and obj.user_type == 'super_admin':
            return False
        return super().has_delete_permission(request, obj)


# Configuration du site admin
admin.site.site_header = "SmartQueue - Administration"
admin.site.site_title = "SmartQueue Admin"
admin.site.index_title = "Gestion SmartQueue Sénégal"
