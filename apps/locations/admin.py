# apps/locations/admin.py
"""
Administration pour géolocalisation intelligente SmartQueue
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Region, Commune, UserLocation, TravelTimeEstimate,
    TrafficCondition, WeatherCondition
)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    """Administration des régions"""
    
    list_display = [
        'name', 'code', 'center_coordinates', 'coverage_radius_km',
        'communes_count', 'created_at'
    ]
    
    list_filter = ['created_at']
    search_fields = ['name', 'code']
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'code')
        }),
        ('Géolocalisation', {
            'fields': ('center_latitude', 'center_longitude', 'coverage_radius_km')
        }),
        ('Métadonnées', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def center_coordinates(self, obj):
        return f"{obj.center_latitude}, {obj.center_longitude}"
    center_coordinates.short_description = "Coordonnées centre"
    
    def communes_count(self, obj):
        count = obj.communes.count()
        return format_html(
            '<a href="/admin/locations/commune/?region__id__exact={}">{} communes</a>',
            obj.id, count
        )
    communes_count.short_description = "Communes"


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    """Administration des communes"""
    
    list_display = [
        'name', 'region', 'locality_type', 'coordinates',
        'population', 'traffic_factor', 'created_at'
    ]
    
    list_filter = [
        'region', 'locality_type', 'traffic_factor', 'created_at'
    ]
    
    search_fields = ['name', 'region__name']
    
    readonly_fields = ['uuid', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'region', 'locality_type', 'population')
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude')
        }),
        ('Circulation', {
            'fields': ('traffic_factor',)
        }),
        ('Métadonnées', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def coordinates(self, obj):
        return f"{obj.latitude}, {obj.longitude}"
    coordinates.short_description = "Coordonnées"


@admin.register(UserLocation)
class UserLocationAdmin(admin.ModelAdmin):
    """Administration localisations utilisateurs"""
    
    list_display = [
        'user_email', 'nearest_commune', 'transport_mode',
        'location_sharing_enabled', 'coordinates', 'last_updated_display'
    ]
    
    list_filter = [
        'location_sharing_enabled', 'transport_mode', 
        'nearest_commune__region', 'last_updated'
    ]
    
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'nearest_commune__name'
    ]
    
    readonly_fields = ['user', 'last_updated']
    
    date_hierarchy = 'last_updated'
    ordering = ['-last_updated']
    
    fieldsets = (
        ('Utilisateur', {
            'fields': ('user',)
        }),
        ('Localisation', {
            'fields': (
                'latitude', 'longitude', 'accuracy_meters',
                'nearest_commune', 'last_updated'
            )
        }),
        ('Paramètres', {
            'fields': ('transport_mode', 'location_sharing_enabled')
        })
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Email utilisateur"
    user_email.admin_order_field = 'user__email'
    
    def coordinates(self, obj):
        return f"{obj.latitude}, {obj.longitude}"
    coordinates.short_description = "GPS"
    
    def last_updated_display(self, obj):
        time_diff = timezone.now() - obj.last_updated
        minutes = time_diff.total_seconds() / 60
        
        if minutes < 60:
            return format_html(
                '<span style="color: green;">Il y a {}min</span>',
                int(minutes)
            )
        elif minutes < 1440:  # 24h
            return format_html(
                '<span style="color: orange;">Il y a {}h</span>',
                int(minutes / 60)
            )
        else:
            return format_html(
                '<span style="color: red;">Il y a {}j</span>',
                int(minutes / 1440)
            )
    last_updated_display.short_description = "Dernière MAJ"
    
    def has_add_permission(self, request):
        return False  # Pas de création manuelle


@admin.register(TravelTimeEstimate)
class TravelTimeEstimateAdmin(admin.ModelAdmin):
    """Administration estimations temps de trajet"""
    
    list_display = [
        'user_email', 'route_display', 'travel_time_display',
        'confidence_score', 'calculation_source', 'created_at'
    ]
    
    list_filter = [
        'transport_mode', 'calculation_source', 'confidence_score',
        'origin_commune__region', 'created_at'
    ]
    
    search_fields = [
        'user__email', 'organization__name',
        'origin_commune__name', 'destination_commune__name'
    ]
    
    readonly_fields = [
        'user', 'organization', 'created_at', 'updated_at'
    ]
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Trajet', {
            'fields': (
                'user', 'organization', 
                'origin_commune', 'destination_commune'
            )
        }),
        ('Calculs', {
            'fields': (
                'estimated_travel_minutes', 'distance_km', 'transport_mode',
                'traffic_factor_applied', 'weather_factor_applied', 'time_of_day_factor',
                'safety_margin_minutes', 'confidence_score', 'calculation_source'
            )
        }),
        ('Horaires', {
            'fields': (
                'recommended_departure_time', 'estimated_arrival_time'
            )
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = "Utilisateur"
    user_email.admin_order_field = 'user__email'
    
    def route_display(self, obj):
        return f"{obj.origin_commune.name} → {obj.organization.name}"
    route_display.short_description = "Trajet"
    
    def travel_time_display(self, obj):
        confidence_color = "green" if obj.confidence_score >= 80 else "orange" if obj.confidence_score >= 60 else "red"
        return format_html(
            '<strong>{}min</strong> <span style="color: {};">({}%)</span>',
            obj.estimated_travel_minutes, confidence_color, obj.confidence_score
        )
    travel_time_display.short_description = "Temps (confiance)"


@admin.register(TrafficCondition)
class TrafficConditionAdmin(admin.ModelAdmin):
    """Administration conditions de circulation"""
    
    list_display = [
        'route_display', 'status_display', 'travel_time_minutes',
        'delay_factor_display', 'data_source', 'reliability_score', 'last_updated'
    ]
    
    list_filter = [
        'status', 'data_source', 'reliability_score',
        'source_commune__region', 'last_updated'
    ]
    
    search_fields = [
        'source_commune__name', 'destination_commune__name'
    ]
    
    date_hierarchy = 'last_updated'
    ordering = ['-last_updated']
    
    fieldsets = (
        ('Route', {
            'fields': ('source_commune', 'destination_commune')
        }),
        ('Conditions', {
            'fields': (
                'status', 'travel_time_minutes', 'distance_km',
                'delay_factor'
            )
        }),
        ('Source', {
            'fields': ('data_source', 'reliability_score', 'last_updated')
        })
    )
    
    def route_display(self, obj):
        return f"{obj.source_commune.name} → {obj.destination_commune.name}"
    route_display.short_description = "Route"
    
    def status_display(self, obj):
        status_colors = {
            'fluide': 'green',
            'normal': 'blue', 
            'dense': 'orange',
            'embouteille': 'red',
            'bloque': 'darkred'
        }
        color = status_colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_display.short_description = "État"
    
    def delay_factor_display(self, obj):
        color = "green" if obj.delay_factor <= 1.2 else "orange" if obj.delay_factor <= 2.0 else "red"
        return format_html(
            '<span style="color: {};">×{:.1f}</span>',
            color, obj.delay_factor
        )
    delay_factor_display.short_description = "Facteur retard"


@admin.register(WeatherCondition)
class WeatherConditionAdmin(admin.ModelAdmin):
    """Administration conditions météo"""
    
    list_display = [
        'region', 'condition_display', 'temperature_celsius',
        'travel_impact_factor', 'precipitation_mm', 'last_updated'
    ]
    
    list_filter = [
        'condition', 'travel_impact_factor', 'last_updated'
    ]
    
    date_hierarchy = 'last_updated'
    ordering = ['-last_updated']
    
    fieldsets = (
        ('Localisation', {
            'fields': ('region',)
        }),
        ('Conditions', {
            'fields': (
                'condition', 'temperature_celsius', 
                'precipitation_mm', 'visibility_km'
            )
        }),
        ('Impact trajets', {
            'fields': ('travel_impact_factor',)
        }),
        ('Mise à jour', {
            'fields': ('last_updated',)
        })
    )
    
    def condition_display(self, obj):
        condition_colors = {
            'sunny': 'gold',
            'cloudy': 'gray',
            'rainy': 'blue',
            'stormy': 'darkblue',
            'foggy': 'lightgray',
            'windy': 'lightblue'
        }
        color = condition_colors.get(obj.condition, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_condition_display()
        )
    condition_display.short_description = "Condition"
