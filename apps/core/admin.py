# apps/core/admin.py
"""
Admin pour l'application core SmartQueue
Configuration système et logs d'activité
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Configuration, ActivityLog


@admin.register(Configuration)
class ConfigurationAdmin(admin.ModelAdmin):
    """Admin pour Configuration système"""
    
    list_display = [
        'site_name', 'maintenance_mode', 'sms_enabled', 
        'email_enabled', 'push_enabled', 'created_at'
    ]
    
    list_filter = [
        'maintenance_mode', 'sms_enabled', 'email_enabled', 'push_enabled',
        'created_at'
    ]
    
    search_fields = ['site_name', 'site_description', 'support_email']
    
    readonly_fields = [
        'uuid', 'created_at', 'updated_at', 
        'created_by', 'modified_by'
    ]
    
    fieldsets = (
        ('Informations générales', {
            'fields': (
                'site_name', 'site_description',
                'support_email', 'support_phone'
            )
        }),
        ('Paramètres par défaut', {
            'fields': (
                'default_ticket_expiry_minutes',
                'default_appointment_duration_minutes',
                'max_tickets_per_user_per_day',
                'max_appointments_per_user_per_day'
            )
        }),
        ('Notifications', {
            'fields': (
                'sms_enabled', 'push_enabled', 'email_enabled'
            )
        }),
        ('Maintenance', {
            'fields': (
                'maintenance_mode', 'maintenance_message'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': (
                'uuid', 'created_at', 'updated_at',
                'created_by', 'modified_by'
            ),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        """Empêcher création de nouvelle config si une existe"""
        return not Configuration.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Empêcher suppression de la configuration"""
        return False


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    """Admin pour logs d'activité"""
    
    list_display = [
        'created_at', 'user_display', 'action_type', 
        'model_name', 'description_short', 'ip_address'
    ]
    
    list_filter = [
        'action_type', 'model_name', 'created_at'
    ]
    
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'description', 'ip_address', 'object_id'
    ]
    
    readonly_fields = [
        'user', 'action_type', 'model_name', 'object_id',
        'description', 'ip_address', 'user_agent', 'metadata',
        'created_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    # Pagination
    list_per_page = 50
    list_max_show_all = 200
    
    fieldsets = (
        ('Activité', {
            'fields': (
                'user', 'action_type', 'description'
            )
        }),
        ('Objet concerné', {
            'fields': (
                'model_name', 'object_id'
            )
        }),
        ('Contexte technique', {
            'fields': (
                'ip_address', 'user_agent', 'metadata'
            ),
            'classes': ('collapse',)
        }),
        ('Horodatage', {
            'fields': (
                'created_at',
            )
        })
    )
    
    def user_display(self, obj):
        """Affichage utilisateur avec lien"""
        if obj.user:
            return format_html(
                '<a href="/admin/accounts/user/{}/change/">{}</a>',
                obj.user.id,
                obj.user.email
            )
        return "Anonyme"
    user_display.short_description = "Utilisateur"
    user_display.admin_order_field = 'user__email'
    
    def description_short(self, obj):
        """Description tronquée"""
        if len(obj.description) > 50:
            return obj.description[:47] + "..."
        return obj.description
    description_short.short_description = "Description"
    
    def has_add_permission(self, request):
        """Empêcher ajout manuel de logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Empêcher modification des logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permettre suppression des anciens logs seulement"""
        if obj and request.user.is_superuser:
            # Permettre suppression des logs > 1 an
            one_year_ago = timezone.now() - timezone.timedelta(days=365)
            return obj.created_at < one_year_ago
        return False


# Customisation de l'admin site
admin.site.site_header = "Administration SmartQueue"
admin.site.site_title = "SmartQueue Admin"
admin.site.index_title = "Gestion SmartQueue Sénégal"
