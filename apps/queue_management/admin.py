# apps/queue_management/admin.py
"""
Administration Django pour la gestion des files d'attente et tickets
Interface complète pour agents et superviseurs
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone
from decimal import Decimal

from .models import Queue, Ticket


class TicketInline(admin.TabularInline):
    """Tickets inline dans les files d'attente"""
    model = Ticket
    extra = 0
    readonly_fields = [
        'ticket_number', 'customer', 'status', 'priority',
        'created_at', 'called_at', 'service_started_at', 'queue_position'
    ]
    fields = [
        'ticket_number', 'customer', 'status', 'priority',
        'created_at', 'queue_position'
    ]
    can_delete = False
    max_num = 10  # Limiter affichage pour performance

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Queue)
class QueueAdmin(admin.ModelAdmin):
    """
    Administration des files d'attente
    Interface pour superviseurs et managers
    """

    list_display = [
        'name', 'organization_name', 'service_name', 'queue_type_badge',
        'current_status_badge', 'tickets_count', 'waiting_count',
        'avg_wait_time', 'capacity_info', 'is_active'
    ]

    list_filter = [
        'queue_type', 'current_status', 'is_active',
        'organization', 'service', 'created_at'
    ]

    search_fields = [
        'name', 'organization__name', 'organization__trade_name',
        'service__name', 'description'
    ]

    ordering = ['organization', 'service', 'name']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Informations de base', {
            'fields': ('organization', 'service', 'name', 'description')
        }),
        ('Configuration file', {
            'fields': (
                'queue_type', 'processing_strategy', 'current_status',
                'max_capacity', 'estimated_wait_time_per_person'
            )
        }),
        ('Horaires', {
            'fields': ('opening_time', 'closing_time'),
            'classes': ('collapse',)
        }),
        ('Paramètres avancés', {
            'fields': ('is_active', 'requires_appointment', 'auto_call_next'),
            'classes': ('collapse',)
        }),
        ('Géolocalisation', {
            'fields': ('location_latitude', 'location_longitude'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = ['uuid', 'created_at', 'updated_at']

    inlines = [TicketInline]

    actions = [
        'activate_queues', 'pause_queues', 'close_queues',
        'reset_queue_counters', 'export_queue_report'
    ]

    def organization_name(self, obj):
        """Nom de l'organisation avec lien"""
        if obj.organization:
            url = reverse('admin:business_organization_change', args=[obj.organization.id])
            return format_html('<a href="{}">{}</a>', url, obj.organization.trade_name or obj.organization.name)
        return '-'
    organization_name.short_description = 'Organisation'

    def service_name(self, obj):
        """Nom du service avec lien"""
        if obj.service:
            url = reverse('admin:business_service_change', args=[obj.service.id])
            return format_html('<a href="{}">{}</a>', url, obj.service.name)
        return '-'
    service_name.short_description = 'Service'

    def queue_type_badge(self, obj):
        """Badge coloré du type de file"""
        colors = {
            'normal': '#6c757d',
            'priority': '#fd7e14',
            'vip': '#dc3545',
            'appointment': '#007bff',
            'express': '#28a745'
        }
        color = colors.get(obj.queue_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 10px; font-weight: bold;">{}</span>',
            color, obj.get_queue_type_display()
        )
    queue_type_badge.short_description = 'Type'

    def current_status_badge(self, obj):
        """Badge coloré du statut actuel"""
        colors = {
            'active': '#28a745',
            'paused': '#fd7e14',
            'closed': '#6c757d',
            'maintenance': '#dc3545'
        }
        color = colors.get(obj.current_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 10px; font-weight: bold;">{}</span>',
            color, obj.get_current_status_display()
        )
    current_status_badge.short_description = 'Statut'

    def tickets_count(self, obj):
        """Nombre total de tickets"""
        count = obj.tickets.count()
        return format_html('<strong>{}</strong>', count)
    tickets_count.short_description = 'Total tickets'

    def waiting_count(self, obj):
        """Nombre de tickets en attente"""
        count = obj.tickets.filter(status='waiting').count()
        if count > 0:
            return format_html('<span style="color: orange; font-weight: bold;">{}</span>', count)
        return format_html('<span style="color: green;">0</span>')
    waiting_count.short_description = 'En attente'

    def avg_wait_time(self, obj):
        """Temps d'attente moyen estimé"""
        if hasattr(obj, 'get_estimated_wait_time'):
            minutes = obj.estimated_wait_time_per_person or 15
            waiting = obj.tickets.filter(status='waiting').count()
            total_wait = minutes * waiting
            return f"{total_wait} min"
        return '-'
    avg_wait_time.short_description = 'Temps attente'

    def capacity_info(self, obj):
        """Information sur la capacité"""
        if obj.max_capacity and obj.max_capacity > 0:
            current = obj.tickets.filter(status__in=['waiting', 'called', 'serving']).count()
            percentage = (current / obj.max_capacity) * 100
            if percentage >= 90:
                color = 'red'
            elif percentage >= 70:
                color = 'orange'
            else:
                color = 'green'
            return format_html(
                '<span style="color: {};">{}/{} ({}%)</span>',
                color, current, obj.max_capacity, int(percentage)
            )
        return 'Illimitée'
    capacity_info.short_description = 'Capacité'

    def activate_queues(self, request, queryset):
        """Action : activer files sélectionnées"""
        count = queryset.update(current_status='active')
        self.message_user(request, f'{count} file(s) activée(s).')
    activate_queues.short_description = "Activer les files"

    def pause_queues(self, request, queryset):
        """Action : mettre en pause"""
        count = queryset.update(current_status='paused')
        self.message_user(request, f'{count} file(s) mise(s) en pause.')
    pause_queues.short_description = "Mettre en pause"

    def close_queues(self, request, queryset):
        """Action : fermer files"""
        count = queryset.update(current_status='closed')
        self.message_user(request, f'{count} file(s) fermée(s).')
    close_queues.short_description = "Fermer les files"

    def reset_queue_counters(self, request, queryset):
        """Action : réinitialiser compteurs"""
        count = 0
        for queue in queryset:
            # Remettre à zéro les tickets non servis
            queue.tickets.filter(status__in=['waiting', 'called']).update(status='cancelled')
            count += 1
        self.message_user(request, f'Compteurs réinitialisés pour {count} file(s).')
    reset_queue_counters.short_description = "Réinitialiser compteurs"

    def export_queue_report(self, request, queryset):
        """Action : exporter rapport (placeholder)"""
        count = queryset.count()
        self.message_user(request, f'Rapport généré pour {count} file(s). (Fonctionnalité à implémenter)')
    export_queue_report.short_description = "Exporter rapport"


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    """
    Administration des tickets
    Interface pour agents et superviseurs
    """

    list_display = [
        'ticket_number', 'customer_name', 'queue_name', 'service_name',
        'status_badge', 'priority_badge', 'creation_channel',
        'position_display', 'created_at', 'wait_time_display'
    ]

    list_filter = [
        'status', 'priority', 'creation_channel', 'queue__queue_type',
        'queue__organization', 'created_at'
    ]

    search_fields = [
        'ticket_number', 'customer__first_name', 'customer__last_name',
        'customer__phone_number', 'queue__name', 'service__name',
        'notes'
    ]

    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Informations ticket', {
            'fields': ('ticket_number', 'queue', 'service', 'customer')
        }),
        ('Statut et priorité', {
            'fields': ('status', 'priority', 'creation_channel')
        }),
        ('Détails client', {
            'fields': ('customer_phone', 'customer_name', 'notes'),
            'classes': ('collapse',)
        }),
        ('Géolocalisation client', {
            'fields': ('customer_location_lat', 'customer_location_lng'),
            'classes': ('collapse',)
        }),
        ('Timeline', {
            'fields': (
                'created_at', 'called_at', 'served_at', 'completed_at',
                'expires_at'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('metadata', 'created_ip'),
            'classes': ('collapse',)
        })
    )

    readonly_fields = [
        'uuid', 'ticket_number', 'created_at', 'called_at',
        'service_started_at', 'service_ended_at', 'created_ip'
    ]

    actions = [
        'call_tickets', 'mark_as_served', 'cancel_tickets',
        'mark_as_no_show', 'transfer_to_queue'
    ]

    def customer_name(self, obj):
        """Nom du client avec lien"""
        if obj.customer:
            url = reverse('admin:accounts_user_change', args=[obj.customer.id])
            name = obj.customer.get_full_name() or obj.customer_name
            return format_html('<a href="{}">{}</a>', url, name)
        return obj.customer_name or '-'
    customer_name.short_description = 'Client'

    def queue_name(self, obj):
        """Nom de la file avec lien"""
        if obj.queue:
            url = reverse('admin:queue_management_queue_change', args=[obj.queue.id])
            return format_html('<a href="{}">{}</a>', url, obj.queue.name)
        return '-'
    queue_name.short_description = 'File'

    def service_name(self, obj):
        """Nom du service"""
        return obj.service.name if obj.service else '-'
    service_name.short_description = 'Service'

    def status_badge(self, obj):
        """Badge coloré du statut"""
        colors = {
            'waiting': '#fd7e14',      # Orange
            'called': '#007bff',       # Bleu
            'serving': '#17a2b8',      # Cyan
            'served': '#28a745',       # Vert
            'cancelled': '#6c757d',    # Gris
            'expired': '#dc3545',      # Rouge
            'no_show': '#dc3545',      # Rouge
            'transferred': '#6f42c1'   # Violet
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 10px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Statut'

    def priority_badge(self, obj):
        """Badge de priorité"""
        colors = {
            'low': '#28a745',      # Vert
            'medium': '#fd7e14',   # Orange
            'high': '#dc3545',     # Rouge
            'urgent': '#dc3545'    # Rouge foncé
        }
        color = colors.get(obj.priority, '#28a745')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 1px 4px; '
            'border-radius: 2px; font-size: 9px;">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priorité'

    def position_display(self, obj):
        """Position dans la file"""
        if obj.status == 'waiting':
            try:
                position = obj.queue_position or 0
                if position > 0:
                    return format_html('<strong>#{}</strong>', position)
            except:
                pass
        return '-'
    position_display.short_description = 'Position'

    def wait_time_display(self, obj):
        """Temps d'attente actuel"""
        if obj.status == 'waiting' and obj.created_at:
            delta = timezone.now() - obj.created_at
            minutes = int(delta.total_seconds() / 60)
            if minutes > 60:
                hours = minutes // 60
                mins = minutes % 60
                return f"{hours}h{mins:02d}"
            return f"{minutes}min"
        return '-'
    wait_time_display.short_description = 'Temps attente'

    def call_tickets(self, request, queryset):
        """Action : appeler tickets sélectionnés"""
        count = queryset.filter(status='waiting').update(
            status='called',
            called_at=timezone.now()
        )
        self.message_user(request, f'{count} ticket(s) appelé(s).')
    call_tickets.short_description = "Appeler les tickets"

    def mark_as_served(self, request, queryset):
        """Action : marquer comme servis"""
        count = queryset.filter(status__in=['called', 'serving']).update(
            status='served',
            service_ended_at=timezone.now()
        )
        self.message_user(request, f'{count} ticket(s) marqué(s) comme servis.')
    mark_as_served.short_description = "Marquer comme servis"

    def cancel_tickets(self, request, queryset):
        """Action : annuler tickets"""
        count = queryset.filter(status__in=['waiting', 'called']).update(
            status='cancelled'
        )
        self.message_user(request, f'{count} ticket(s) annulé(s).')
    cancel_tickets.short_description = "Annuler les tickets"

    def mark_as_no_show(self, request, queryset):
        """Action : marquer absent"""
        count = queryset.filter(status='called').update(
            status='no_show'
        )
        self.message_user(request, f'{count} ticket(s) marqué(s) comme absent.')
    mark_as_no_show.short_description = "Marquer comme absent"

    def transfer_to_queue(self, request, queryset):
        """Action : transférer vers autre file (placeholder)"""
        count = queryset.count()
        self.message_user(
            request,
            f'Transfert préparé pour {count} ticket(s). (Sélectionner file de destination)'
        )
    transfer_to_queue.short_description = "Transférer vers autre file"

    def has_delete_permission(self, request, obj=None):
        """Empêcher suppression des tickets servis"""
        if obj and obj.status == 'served':
            return False
        return super().has_delete_permission(request, obj)