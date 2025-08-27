# apps/locations/serializers.py
"""
Serializers pour géolocalisation intelligente SmartQueue
"""

from rest_framework import serializers
from django.utils import timezone
from .models import (
    Region, Commune, UserLocation, TravelTimeEstimate, 
    TrafficCondition, WeatherCondition
)


class RegionSerializer(serializers.ModelSerializer):
    """Serializer pour régions du Sénégal"""
    
    class Meta:
        model = Region
        fields = [
            'id', 'code', 'name', 
            'center_latitude', 'center_longitude', 'coverage_radius_km',
            'created_at', 'updated_at'
        ]


class CommuneSerializer(serializers.ModelSerializer):
    """Serializer pour communes/quartiers"""
    
    region_name = serializers.CharField(source='region.name', read_only=True)
    region_code = serializers.CharField(source='region.code', read_only=True)
    
    class Meta:
        model = Commune
        fields = [
            'id', 'name', 'locality_type', 
            'latitude', 'longitude', 'population', 'traffic_factor',
            'region', 'region_name', 'region_code',
            'created_at', 'updated_at'
        ]


class UserLocationSerializer(serializers.ModelSerializer):
    """Serializer pour localisation utilisateur"""
    
    nearest_commune_name = serializers.CharField(
        source='nearest_commune.name', read_only=True
    )
    is_location_fresh = serializers.SerializerMethodField()
    
    class Meta:
        model = UserLocation
        fields = [
            'latitude', 'longitude', 'accuracy_meters',
            'transport_mode', 'location_sharing_enabled',
            'nearest_commune', 'nearest_commune_name',
            'last_updated', 'is_location_fresh'
        ]
        read_only_fields = ['last_updated']
    
    def get_is_location_fresh(self, obj):
        return obj.is_location_fresh()


class LocationUpdateSerializer(serializers.Serializer):
    """Serializer pour mise à jour localisation"""
    
    latitude = serializers.DecimalField(
        max_digits=10, decimal_places=8,
        min_value=-90, max_value=90
    )
    longitude = serializers.DecimalField(
        max_digits=11, decimal_places=8,
        min_value=-180, max_value=180
    )
    accuracy_meters = serializers.IntegerField(min_value=1, max_value=10000, required=False)
    transport_mode = serializers.ChoiceField(
        choices=UserLocation.TRANSPORT_MODES,
        required=False
    )
    location_sharing_enabled = serializers.BooleanField(required=False)


class TravelCalculationRequestSerializer(serializers.Serializer):
    """Serializer pour demande calcul temps de trajet"""
    
    organization_id = serializers.IntegerField()
    departure_time = serializers.DateTimeField(required=False)
    
    def validate_departure_time(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("L'heure de départ ne peut pas être dans le passé")
        return value


class TravelTimeEstimateSerializer(serializers.ModelSerializer):
    """Serializer pour estimations temps de trajet"""
    
    origin_commune_name = serializers.CharField(
        source='origin_commune.name', read_only=True
    )
    destination_commune_name = serializers.CharField(
        source='destination_commune.name', read_only=True
    )
    organization_name = serializers.CharField(
        source='organization.name', read_only=True
    )
    delay_risk = serializers.SerializerMethodField()
    is_estimate_valid = serializers.SerializerMethodField()
    should_notify_departure = serializers.SerializerMethodField()
    
    class Meta:
        model = TravelTimeEstimate
        fields = [
            'id', 'estimated_travel_minutes', 'distance_km', 'transport_mode',
            'origin_commune_name', 'destination_commune_name', 'organization_name',
            'traffic_factor_applied', 'weather_factor_applied', 'time_of_day_factor',
            'safety_margin_minutes', 'recommended_departure_time', 'estimated_arrival_time',
            'confidence_score', 'calculation_source',
            'delay_risk', 'is_estimate_valid', 'should_notify_departure',
            'created_at'
        ]
        read_only_fields = fields
    
    def get_delay_risk(self, obj):
        return obj.get_delay_risk()
    
    def get_is_estimate_valid(self, obj):
        return obj.is_estimate_valid()
    
    def get_should_notify_departure(self, obj):
        return obj.should_notify_departure()


class TrafficConditionSerializer(serializers.ModelSerializer):
    """Serializer pour conditions de circulation"""
    
    source_commune_name = serializers.CharField(
        source='source_commune.name', read_only=True
    )
    destination_commune_name = serializers.CharField(
        source='destination_commune.name', read_only=True
    )
    is_fresh = serializers.SerializerMethodField()
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    
    class Meta:
        model = TrafficCondition
        fields = [
            'id', 'source_commune_name', 'destination_commune_name',
            'status', 'status_display', 'travel_time_minutes', 'distance_km',
            'delay_factor', 'data_source', 'reliability_score',
            'last_updated', 'is_fresh'
        ]
        read_only_fields = fields
    
    def get_is_fresh(self, obj):
        return obj.is_fresh()


class WeatherConditionSerializer(serializers.ModelSerializer):
    """Serializer pour conditions météo"""
    
    region_name = serializers.CharField(source='region.name', read_only=True)
    condition_display = serializers.CharField(
        source='get_condition_display', read_only=True
    )
    
    class Meta:
        model = WeatherCondition
        fields = [
            'id', 'region', 'region_name',
            'condition', 'condition_display', 'travel_impact_factor',
            'temperature_celsius', 'precipitation_mm', 'visibility_km',
            'last_updated'
        ]


class NearbyOrganizationSerializer(serializers.Serializer):
    """Serializer pour organisations proches"""
    
    organization = serializers.DictField()  # OrganizationSerializer data
    distance_km = serializers.FloatField()
    travel_time_minutes = serializers.IntegerField()
    confidence = serializers.IntegerField()


class QueueReorganizationResultSerializer(serializers.Serializer):
    """Serializer pour résultats réorganisation files"""
    
    success = serializers.BooleanField()
    queue_id = serializers.IntegerField()
    tickets_reorganized = serializers.IntegerField()
    message = serializers.CharField()


class LocationStatsSerializer(serializers.Serializer):
    """Serializer pour statistiques de géolocalisation"""
    
    total_users_with_location = serializers.IntegerField()
    users_sharing_location = serializers.IntegerField()
    active_travel_estimates = serializers.IntegerField()
    queues_with_smart_ordering = serializers.IntegerField()
    avg_travel_time_minutes = serializers.FloatField()
    most_common_transport_mode = serializers.CharField()


class TravelTimeComparisonSerializer(serializers.Serializer):
    """Serializer pour comparaison temps de trajet"""
    
    base_time_minutes = serializers.IntegerField()
    with_traffic_minutes = serializers.IntegerField()
    with_weather_minutes = serializers.IntegerField()
    final_time_minutes = serializers.IntegerField()
    time_saved_or_lost = serializers.IntegerField()  # Positif = temps gagné
    factors_applied = serializers.DictField()


class LocationInsightSerializer(serializers.Serializer):
    """Serializer pour insights géolocalisation"""
    
    user_commune = serializers.CharField()
    favorite_organizations = serializers.ListField()
    avg_travel_time_to_favorites = serializers.IntegerField()
    best_travel_times = serializers.DictField()  # heure -> temps moyen
    worst_travel_times = serializers.DictField()
    recommendations = serializers.ListField()


class RushHourAnalysisSerializer(serializers.Serializer):
    """Serializer pour analyse heures de pointe"""
    
    hour = serializers.IntegerField()
    is_rush_hour = serializers.BooleanField()
    traffic_factor = serializers.FloatField()
    avg_delay_minutes = serializers.IntegerField()
    affected_routes_count = serializers.IntegerField()
    recommendation = serializers.CharField()