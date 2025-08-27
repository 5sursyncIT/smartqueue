# apps/locations/models.py
"""
Modèles de géolocalisation intelligente SmartQueue Sénégal
Calcul intelligent des temps de trajet avec embouteillages
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.core.models import BaseSmartQueueModel
from apps.core.constants import SenegalRegions
import math
import requests
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Region(BaseSmartQueueModel):
    """
    Régions administratives du Sénégal avec données géographiques
    """
    
    code = models.CharField(
        max_length=20,
        choices=SenegalRegions.CHOICES,
        unique=True,
        verbose_name=_('Code région')
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Nom de la région')
    )
    
    # Coordonnées centre de la région
    center_latitude = models.DecimalField(
        max_digits=10, decimal_places=8,
        verbose_name=_('Latitude centre')
    )
    
    center_longitude = models.DecimalField(
        max_digits=11, decimal_places=8,
        verbose_name=_('Longitude centre')
    )
    
    # Zone de couverture (rayon en km)
    coverage_radius_km = models.PositiveIntegerField(
        default=50,
        verbose_name=_('Rayon couverture (km)')
    )
    
    class Meta:
        verbose_name = _('Région')
        verbose_name_plural = _('Régions')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Commune(BaseSmartQueueModel):
    """
    Communes et quartiers du Sénégal
    """
    
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='communes',
        verbose_name=_('Région')
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Nom commune/quartier')
    )
    
    # Type de localité
    TYPE_CHOICES = [
        ('commune', _('Commune')),
        ('quartier', _('Quartier')), 
        ('village', _('Village')),
        ('arrondissement', _('Arrondissement')),
    ]
    
    locality_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='commune',
        verbose_name=_('Type de localité')
    )
    
    # Coordonnées
    latitude = models.DecimalField(
        max_digits=10, decimal_places=8,
        verbose_name=_('Latitude')
    )
    
    longitude = models.DecimalField(
        max_digits=11, decimal_places=8,
        verbose_name=_('Longitude')
    )
    
    # Population (pour calcul embouteillages)
    population = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Population estimée')
    )
    
    # Facteur embouteillage (1.0 = normal, 2.0 = très embouteillé)
    traffic_factor = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.5), MaxValueValidator(5.0)],
        verbose_name=_('Facteur embouteillage')
    )
    
    class Meta:
        verbose_name = _('Commune')
        verbose_name_plural = _('Communes')
        unique_together = ['region', 'name']
        ordering = ['region', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.region.name})"


class TrafficCondition(models.Model):
    """
    Conditions de circulation temps réel
    Mis à jour par APIs externes ou manuellement
    """
    
    source_commune = models.ForeignKey(
        Commune,
        on_delete=models.CASCADE,
        related_name='traffic_from',
        verbose_name=_('Commune de départ')
    )
    
    destination_commune = models.ForeignKey(
        Commune,
        on_delete=models.CASCADE,
        related_name='traffic_to',
        verbose_name=_('Commune de destination')
    )
    
    # Conditions de circulation
    TRAFFIC_STATUS = [
        ('fluide', _('Fluide')),
        ('normal', _('Normal')),
        ('dense', _('Dense')),
        ('embouteille', _('Embouteillé')),
        ('bloque', _('Bloqué')),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=TRAFFIC_STATUS,
        default='normal',
        verbose_name=_('État circulation')
    )
    
    # Temps de trajet (en minutes)
    travel_time_minutes = models.PositiveIntegerField(
        verbose_name=_('Temps trajet (min)')
    )
    
    # Distance en km
    distance_km = models.FloatField(
        verbose_name=_('Distance (km)')
    )
    
    # Facteur multiplicateur selon les conditions
    delay_factor = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.5), MaxValueValidator(10.0)],
        verbose_name=_('Facteur de retard')
    )
    
    # Source de données
    DATA_SOURCES = [
        ('manual', _('Saisie manuelle')),
        ('google', _('Google Maps')),
        ('osm', _('OpenStreetMap')),
        ('local_api', _('API locale')),
    ]
    
    data_source = models.CharField(
        max_length=20,
        choices=DATA_SOURCES,
        default='manual',
        verbose_name=_('Source données')
    )
    
    # Horodatage
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Dernière MAJ')
    )
    
    # Fiabilité (0-100%)
    reliability_score = models.PositiveIntegerField(
        default=80,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Score fiabilité (%)')
    )
    
    class Meta:
        verbose_name = _('Condition de circulation')
        verbose_name_plural = _('Conditions de circulation')
        unique_together = ['source_commune', 'destination_commune']
        ordering = ['-last_updated']
    
    def __str__(self):
        return f"{self.source_commune.name} → {self.destination_commune.name} ({self.travel_time_minutes}min)"
    
    def is_fresh(self, max_age_minutes=30):
        """Vérifier si les données sont récentes"""
        age = timezone.now() - self.last_updated
        return age.total_seconds() < (max_age_minutes * 60)


class UserLocation(models.Model):
    """
    Localisation temps réel des clients
    Mis à jour via mobile/GPS
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='current_location',
        verbose_name=_('Utilisateur')
    )
    
    # Coordonnées actuelles
    latitude = models.DecimalField(
        max_digits=10, decimal_places=8,
        verbose_name=_('Latitude actuelle')
    )
    
    longitude = models.DecimalField(
        max_digits=11, decimal_places=8,
        verbose_name=_('Longitude actuelle')
    )
    
    # Commune la plus proche
    nearest_commune = models.ForeignKey(
        Commune,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_('Commune la plus proche')
    )
    
    # Précision GPS (en mètres)
    accuracy_meters = models.PositiveIntegerField(
        default=50,
        verbose_name=_('Précision GPS (m)')
    )
    
    # Dernière mise à jour
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Dernière localisation')
    )
    
    # Mode de transport déclaré
    TRANSPORT_MODES = [
        ('walking', _('À pied')),
        ('car', _('Voiture')),
        ('taxi', _('Taxi')),
        ('bus', _('Bus')),
        ('moto', _('Moto')),
        ('bike', _('Vélo')),
    ]
    
    transport_mode = models.CharField(
        max_length=20,
        choices=TRANSPORT_MODES,
        default='car',
        verbose_name=_('Mode transport')
    )
    
    # Partage de localisation activé
    location_sharing_enabled = models.BooleanField(
        default=False,
        verbose_name=_('Partage localisation activé')
    )
    
    class Meta:
        verbose_name = _('Localisation utilisateur')
        verbose_name_plural = _('Localisations utilisateurs')
    
    def __str__(self):
        return f"{self.user.email} - {self.nearest_commune}"
    
    def is_location_fresh(self, max_age_minutes=10):
        """Vérifier si la localisation est récente"""
        age = timezone.now() - self.last_updated
        return age.total_seconds() < (max_age_minutes * 60)
    
    def update_nearest_commune(self):
        """Trouver et mettre à jour la commune la plus proche"""
        try:
            nearest = None
            min_distance = float('inf')
            
            for commune in Commune.objects.all():
                distance = self.calculate_distance_to_commune(commune)
                if distance < min_distance:
                    min_distance = distance
                    nearest = commune
            
            if nearest:
                self.nearest_commune = nearest
                self.save(update_fields=['nearest_commune'])
                
        except Exception as e:
            logger.error(f"Erreur calcul commune la plus proche: {e}")
    
    def calculate_distance_to_commune(self, commune):
        """Calculer distance à une commune (formule Haversine)"""
        lat1, lon1 = float(self.latitude), float(self.longitude)
        lat2, lon2 = float(commune.latitude), float(commune.longitude)
        
        # Conversion en radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Différences
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Formule Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Rayon Terre en km
        r = 6371
        
        return c * r


class TravelTimeEstimate(BaseSmartQueueModel):
    """
    Estimations de temps de trajet calculées intelligemment
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('Utilisateur')
    )
    
    # Localisation de départ (actuelle utilisateur)
    origin_latitude = models.DecimalField(
        max_digits=10, decimal_places=8,
        verbose_name=_('Latitude départ')
    )
    
    origin_longitude = models.DecimalField(
        max_digits=11, decimal_places=8,
        verbose_name=_('Longitude départ')
    )
    
    origin_commune = models.ForeignKey(
        Commune,
        on_delete=models.CASCADE,
        related_name='travels_from',
        verbose_name=_('Commune départ')
    )
    
    # Destination (organisation)
    destination_latitude = models.DecimalField(
        max_digits=10, decimal_places=8,
        verbose_name=_('Latitude destination')
    )
    
    destination_longitude = models.DecimalField(
        max_digits=11, decimal_places=8,
        verbose_name=_('Longitude destination')
    )
    
    destination_commune = models.ForeignKey(
        Commune,
        on_delete=models.CASCADE,
        related_name='travels_to',
        verbose_name=_('Commune destination')
    )
    
    # Organisation de destination
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        verbose_name=_('Organisation')
    )
    
    # Temps de trajet calculé
    estimated_travel_minutes = models.PositiveIntegerField(
        verbose_name=_('Temps trajet estimé (min)')
    )
    
    # Distance
    distance_km = models.FloatField(
        verbose_name=_('Distance (km)')
    )
    
    # Mode de transport utilisé pour le calcul
    transport_mode = models.CharField(
        max_length=20,
        choices=UserLocation.TRANSPORT_MODES,
        verbose_name=_('Mode transport')
    )
    
    # Facteurs pris en compte
    traffic_factor_applied = models.FloatField(
        default=1.0,
        verbose_name=_('Facteur embouteillage appliqué')
    )
    
    weather_factor_applied = models.FloatField(
        default=1.0,
        verbose_name=_('Facteur météo appliqué')
    )
    
    time_of_day_factor = models.FloatField(
        default=1.0,
        verbose_name=_('Facteur heure')
    )
    
    # Marge de sécurité ajoutée (en minutes)
    safety_margin_minutes = models.PositiveIntegerField(
        default=10,
        verbose_name=_('Marge sécurité (min)')
    )
    
    # Temps recommandé de départ
    recommended_departure_time = models.DateTimeField(
        verbose_name=_('Heure départ recommandée')
    )
    
    # Temps d'arrivée estimé
    estimated_arrival_time = models.DateTimeField(
        verbose_name=_('Arrivée estimée')
    )
    
    # Fiabilité de l'estimation
    confidence_score = models.PositiveIntegerField(
        default=75,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('Score confiance (%)')
    )
    
    # APIs utilisées pour le calcul
    calculation_source = models.CharField(
        max_length=100,
        default='internal',
        verbose_name=_('Source calcul')
    )
    
    class Meta:
        verbose_name = _('Estimation temps trajet')
        verbose_name_plural = _('Estimations temps trajet')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email}: {self.origin_commune} → {self.organization.name} ({self.estimated_travel_minutes}min)"
    
    def is_estimate_valid(self, max_age_minutes=15):
        """Vérifier si l'estimation est encore valable"""
        age = timezone.now() - self.created_at
        return age.total_seconds() < (max_age_minutes * 60)
    
    def should_notify_departure(self, current_time=None):
        """Vérifier s'il faut notifier l'utilisateur de partir"""
        if not current_time:
            current_time = timezone.now()
        
        # Notifier 5 minutes avant l'heure recommandée
        notify_time = self.recommended_departure_time - timezone.timedelta(minutes=5)
        
        return current_time >= notify_time and current_time <= self.recommended_departure_time
    
    def get_delay_risk(self):
        """Évaluer le risque de retard"""
        now = timezone.now()
        
        if now > self.recommended_departure_time:
            delay_minutes = (now - self.recommended_departure_time).total_seconds() / 60
            if delay_minutes > 30:
                return 'high'
            elif delay_minutes > 10:
                return 'medium'
            else:
                return 'low'
        
        return 'none'


class WeatherCondition(models.Model):
    """
    Conditions météorologiques affectant les trajets
    """
    
    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        verbose_name=_('Région')
    )
    
    # Conditions météo
    WEATHER_CONDITIONS = [
        ('sunny', _('Ensoleillé')),
        ('cloudy', _('Nuageux')),
        ('rainy', _('Pluvieux')),
        ('stormy', _('Orageux')),
        ('foggy', _('Brouillard')),
        ('windy', _('Venteux')),
    ]
    
    condition = models.CharField(
        max_length=20,
        choices=WEATHER_CONDITIONS,
        verbose_name=_('Condition météo')
    )
    
    # Impact sur les trajets (multiplicateur)
    travel_impact_factor = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0.8), MaxValueValidator(3.0)],
        verbose_name=_('Impact trajets')
    )
    
    # Température en Celsius
    temperature_celsius = models.IntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(50)],
        verbose_name=_('Température (°C)')
    )
    
    # Précipitations en mm
    precipitation_mm = models.FloatField(
        default=0.0,
        verbose_name=_('Précipitations (mm)')
    )
    
    # Visibilité en km
    visibility_km = models.PositiveIntegerField(
        default=10,
        verbose_name=_('Visibilité (km)')
    )
    
    # Dernière mise à jour
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Dernière MAJ')
    )
    
    class Meta:
        verbose_name = _('Condition météorologique')
        verbose_name_plural = _('Conditions météorologiques')
        unique_together = ['region']
    
    def __str__(self):
        return f"{self.region.name}: {self.get_condition_display()} ({self.temperature_celsius}°C)"
