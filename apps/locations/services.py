# apps/locations/services.py
"""
Services intelligents de calcul de temps de trajet SmartQueue
Algorithmes pour prédire les temps de trajet avec embouteillages
"""

import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from typing import Dict, Optional, Tuple
from .models import (
    Region, Commune, TrafficCondition, UserLocation, 
    TravelTimeEstimate, WeatherCondition
)

logger = logging.getLogger(__name__)


class TrafficPredictionService:
    """
    Service de prédiction des embouteillages au Sénégal
    Basé sur historique + APIs externes + patterns locaux
    """
    
    # Heures de pointe à Dakar
    RUSH_HOURS = {
        'morning': (7, 9),    # 7h-9h
        'evening': (17, 19),  # 17h-19h
    }
    
    # Facteurs embouteillage par heure
    HOURLY_TRAFFIC_FACTORS = {
        6: 1.1,   7: 1.8,   8: 2.2,   9: 1.7,   # Matin
        10: 1.0,  11: 1.0,  12: 1.3,  13: 1.4,  # Matinée
        14: 1.2,  15: 1.1,  16: 1.1,  17: 2.0,  # Après-midi  
        18: 2.5,  19: 1.9,  20: 1.4,  21: 1.0,  # Soirée
        22: 0.9,  23: 0.8,  0: 0.7,   1: 0.6,   # Nuit
        2: 0.6,   3: 0.6,   4: 0.7,   5: 0.8,   # Nuit
    }
    
    # Facteurs par jour de la semaine
    DAILY_TRAFFIC_FACTORS = {
        0: 1.0,   # Lundi
        1: 1.1,   # Mardi  
        2: 1.1,   # Mercredi
        3: 1.2,   # Jeudi
        4: 1.3,   # Vendredi (plus chargé)
        5: 0.8,   # Samedi
        6: 0.7,   # Dimanche
    }
    
    @staticmethod
    def get_traffic_factor_for_time(departure_time: datetime) -> float:
        """Calculer facteur embouteillage selon l'heure"""
        hour = departure_time.hour
        day_of_week = departure_time.weekday()
        
        # Facteur horaire
        hourly_factor = TrafficPredictionService.HOURLY_TRAFFIC_FACTORS.get(hour, 1.0)
        
        # Facteur jour semaine
        daily_factor = TrafficPredictionService.DAILY_TRAFFIC_FACTORS.get(day_of_week, 1.0)
        
        # Facteur final
        return hourly_factor * daily_factor
    
    @staticmethod
    def is_rush_hour(departure_time: datetime) -> bool:
        """Vérifier si c'est l'heure de pointe"""
        hour = departure_time.hour
        
        morning_start, morning_end = TrafficPredictionService.RUSH_HOURS['morning']
        evening_start, evening_end = TrafficPredictionService.RUSH_HOURS['evening']
        
        return (morning_start <= hour < morning_end or 
                evening_start <= hour < evening_end)
    
    @staticmethod
    def get_route_traffic_factor(origin_commune: Commune, destination_commune: Commune) -> float:
        """Obtenir facteur embouteillage pour un trajet spécifique"""
        try:
            # Chercher condition trafic existante
            traffic = TrafficCondition.objects.filter(
                source_commune=origin_commune,
                destination_commune=destination_commune
            ).first()
            
            if traffic and traffic.is_fresh():
                return traffic.delay_factor
            
            # Fallback: moyenne des facteurs des communes
            avg_factor = (origin_commune.traffic_factor + destination_commune.traffic_factor) / 2
            return avg_factor
            
        except Exception as e:
            logger.error(f"Erreur calcul facteur trafic: {e}")
            return 1.2  # Facteur par défaut conservateur


class ExternalAPIService:
    """
    Service d'intégration avec APIs externes pour temps de trajet
    Google Maps, OpenStreetMap, etc.
    """
    
    @staticmethod
    def get_google_maps_duration(origin_lat: float, origin_lng: float, 
                                dest_lat: float, dest_lng: float,
                                departure_time: datetime = None) -> Optional[Dict]:
        """
        Calculer temps de trajet via Google Maps API
        """
        try:
            # Clé API Google Maps (à configurer)
            api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', None)
            if not api_key:
                logger.warning("Google Maps API key non configurée")
                return None
            
            # URL API Google Maps Directions
            url = "https://maps.googleapis.com/maps/api/directions/json"
            
            params = {
                'origin': f"{origin_lat},{origin_lng}",
                'destination': f"{dest_lat},{dest_lng}",
                'key': api_key,
                'traffic_model': 'best_guess',
                'departure_time': 'now' if not departure_time else int(departure_time.timestamp()),
                'language': 'fr',  # Français
            }
            
            # Cache key pour éviter appels répétés
            cache_key = f"gmaps:{origin_lat},{origin_lng}:{dest_lat},{dest_lng}"
            cached_result = cache.get(cache_key)
            
            if cached_result:
                return cached_result
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['status'] == 'OK' and data['routes']:
                route = data['routes'][0]
                leg = route['legs'][0]
                
                result = {
                    'duration_seconds': leg['duration']['value'],
                    'duration_minutes': leg['duration']['value'] // 60,
                    'distance_meters': leg['distance']['value'],
                    'distance_km': leg['distance']['value'] / 1000,
                    'traffic_duration_seconds': leg.get('duration_in_traffic', {}).get('value'),
                    'source': 'google_maps'
                }
                
                # Cache pendant 10 minutes
                cache.set(cache_key, result, 600)
                return result
            
        except requests.RequestException as e:
            logger.error(f"Erreur Google Maps API: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue Google Maps: {e}")
        
        return None
    
    @staticmethod
    def get_openstreetmap_duration(origin_lat: float, origin_lng: float,
                                 dest_lat: float, dest_lng: float) -> Optional[Dict]:
        """
        Calculer temps de trajet via OSRM (OpenStreetMap)
        API gratuite mais sans données trafic temps réel
        """
        try:
            # URL OSRM (serveur de démo)
            url = f"http://router.project-osrm.org/route/v1/driving/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
            
            params = {
                'overview': 'false',
                'geometries': 'polyline',
                'steps': 'false'
            }
            
            cache_key = f"osrm:{origin_lat},{origin_lng}:{dest_lat},{dest_lng}"
            cached_result = cache.get(cache_key)
            
            if cached_result:
                return cached_result
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data['code'] == 'Ok' and data['routes']:
                route = data['routes'][0]
                
                result = {
                    'duration_seconds': route['duration'],
                    'duration_minutes': int(route['duration'] // 60),
                    'distance_meters': route['distance'],
                    'distance_km': route['distance'] / 1000,
                    'source': 'osrm'
                }
                
                # Cache pendant 30 minutes (pas de trafic temps réel)
                cache.set(cache_key, result, 1800)
                return result
                
        except requests.RequestException as e:
            logger.error(f"Erreur OSRM API: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue OSRM: {e}")
        
        return None


class SmartTravelTimeCalculator:
    """
    Calculateur intelligent de temps de trajet
    Combine APIs externes + données locales + ML
    """
    
    @staticmethod
    def calculate_travel_time(user, origin_lat: float, origin_lng: float,
                            dest_lat: float, dest_lng: float,
                            organization, departure_time: datetime = None) -> Dict:
        """
        Calculer temps de trajet intelligent avec tous les facteurs
        """
        if not departure_time:
            departure_time = timezone.now()
        
        try:
            # 1. Obtenir communes origine/destination
            origin_commune = SmartTravelTimeCalculator._find_nearest_commune(origin_lat, origin_lng)
            dest_commune = SmartTravelTimeCalculator._find_nearest_commune(dest_lat, dest_lng)
            
            if not origin_commune or not dest_commune:
                raise ValueError("Impossible de déterminer les communes")
            
            # 2. Distance géographique de base (Haversine)
            base_distance_km = SmartTravelTimeCalculator._calculate_haversine_distance(
                origin_lat, origin_lng, dest_lat, dest_lng
            )
            
            # 3. Temps de base (sans embouteillages)
            user_location = getattr(user, 'current_location', None)
            transport_mode = user_location.transport_mode if user_location else 'car'
            
            base_speed_kmh = SmartTravelTimeCalculator._get_base_speed(transport_mode)
            base_time_minutes = (base_distance_km / base_speed_kmh) * 60
            
            # 4. Essayer APIs externes
            external_data = SmartTravelTimeCalculator._get_external_api_data(
                origin_lat, origin_lng, dest_lat, dest_lng, departure_time
            )
            
            if external_data:
                # Utiliser données API externes comme base
                api_time_minutes = external_data['duration_minutes']
                distance_km = external_data['distance_km']
                confidence = 85
                source = external_data['source']
            else:
                # Fallback: calcul interne
                api_time_minutes = base_time_minutes
                distance_km = base_distance_km
                confidence = 60
                source = 'internal'
            
            # 5. Appliquer facteurs locaux
            traffic_factor = TrafficPredictionService.get_traffic_factor_for_time(departure_time)
            route_factor = TrafficPredictionService.get_route_traffic_factor(origin_commune, dest_commune)
            weather_factor = SmartTravelTimeCalculator._get_weather_factor(dest_commune.region)
            
            # 6. Calcul final
            total_factor = traffic_factor * route_factor * weather_factor
            estimated_time_minutes = int(api_time_minutes * total_factor)
            
            # 7. Marge de sécurité
            safety_margin = SmartTravelTimeCalculator._calculate_safety_margin(
                estimated_time_minutes, confidence, transport_mode
            )
            
            final_time_minutes = estimated_time_minutes + safety_margin
            
            # 8. Temps de départ recommandé
            arrival_time = departure_time + timedelta(minutes=final_time_minutes)
            
            result = {
                'estimated_travel_minutes': final_time_minutes,
                'distance_km': distance_km,
                'transport_mode': transport_mode,
                'origin_commune': origin_commune,
                'destination_commune': dest_commune,
                'traffic_factor': traffic_factor,
                'route_factor': route_factor,
                'weather_factor': weather_factor,
                'safety_margin_minutes': safety_margin,
                'confidence_score': confidence,
                'calculation_source': source,
                'departure_time': departure_time,
                'estimated_arrival_time': arrival_time,
                'is_rush_hour': TrafficPredictionService.is_rush_hour(departure_time)
            }
            
            logger.info(f"Calcul trajet: {origin_commune} → {dest_commune} = {final_time_minutes}min")
            return result
            
        except Exception as e:
            logger.error(f"Erreur calcul temps trajet: {e}")
            raise
    
    @staticmethod
    def _find_nearest_commune(lat: float, lng: float) -> Optional[Commune]:
        """Trouver commune la plus proche"""
        try:
            min_distance = float('inf')
            nearest_commune = None
            
            for commune in Commune.objects.all():
                distance = SmartTravelTimeCalculator._calculate_haversine_distance(
                    lat, lng, float(commune.latitude), float(commune.longitude)
                )
                
                if distance < min_distance:
                    min_distance = distance
                    nearest_commune = commune
            
            return nearest_commune
            
        except Exception as e:
            logger.error(f"Erreur recherche commune: {e}")
            return None
    
    @staticmethod
    def _calculate_haversine_distance(lat1: float, lng1: float, 
                                    lat2: float, lng2: float) -> float:
        """Calculer distance géographique (formule Haversine)"""
        import math
        
        # Conversion en radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Différences
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        # Formule Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Rayon Terre en km
        r = 6371
        
        return c * r
    
    @staticmethod
    def _get_base_speed(transport_mode: str) -> float:
        """Vitesse de base selon mode transport (km/h)"""
        speeds = {
            'walking': 5,
            'bike': 15,
            'moto': 35,
            'car': 40,  # Vitesse urbaine Dakar
            'taxi': 35, # Moins rapide (arrêts)
            'bus': 25,  # Arrêts fréquents
        }
        
        return speeds.get(transport_mode, 40)
    
    @staticmethod
    def _get_external_api_data(origin_lat: float, origin_lng: float,
                             dest_lat: float, dest_lng: float,
                             departure_time: datetime) -> Optional[Dict]:
        """Obtenir données d'APIs externes"""
        
        # Essayer Google Maps en priorité
        google_data = ExternalAPIService.get_google_maps_duration(
            origin_lat, origin_lng, dest_lat, dest_lng, departure_time
        )
        
        if google_data:
            return google_data
        
        # Fallback: OSRM
        osrm_data = ExternalAPIService.get_openstreetmap_duration(
            origin_lat, origin_lng, dest_lat, dest_lng
        )
        
        return osrm_data
    
    @staticmethod
    def _get_weather_factor(region: Region) -> float:
        """Facteur météorologique"""
        try:
            weather = WeatherCondition.objects.filter(region=region).first()
            if weather:
                return weather.travel_impact_factor
        except Exception:
            pass
        
        return 1.0  # Pas d'impact météo par défaut
    
    @staticmethod
    def _calculate_safety_margin(estimated_minutes: int, confidence: int, 
                               transport_mode: str) -> int:
        """Calculer marge de sécurité"""
        
        # Marge de base selon confiance
        base_margin = max(5, int(estimated_minutes * (100 - confidence) / 100))
        
        # Ajustement selon transport
        transport_margins = {
            'walking': 1.2,   # Plus prévisible
            'bike': 1.3,
            'car': 1.5,       # Embouteillages imprévisibles
            'taxi': 1.7,      # Peut être en retard
            'bus': 2.0,       # Le moins fiable
            'moto': 1.1,      # Plus flexible
        }
        
        factor = transport_margins.get(transport_mode, 1.5)
        final_margin = int(base_margin * factor)
        
        # Limites raisonnables
        return min(max(final_margin, 5), 30)


class QueueReorganizationService:
    """
    Service de réorganisation intelligente des files d'attente
    Basé sur géolocalisation et temps de trajet
    """
    
    @staticmethod
    def should_reorganize_queue(ticket, queue):
        """Déterminer si la file doit être réorganisée pour ce ticket"""
        try:
            user = ticket.customer
            user_location = getattr(user, 'current_location', None)
            
            if not user_location or not user_location.location_sharing_enabled:
                return False
            
            # Calculer temps de trajet actuel
            travel_estimate = SmartTravelTimeCalculator.calculate_travel_time(
                user=user,
                origin_lat=float(user_location.latitude),
                origin_lng=float(user_location.longitude),
                dest_lat=float(queue.organization.latitude),
                dest_lng=float(queue.organization.longitude),
                organization=queue.organization,
                departure_time=timezone.now()
            )
            
            # Temps d'attente dans la file
            estimated_service_time = queue.get_estimated_wait_time_for_ticket(ticket)
            
            # Temps de trajet
            travel_time = travel_estimate['estimated_travel_minutes']
            
            # Si le trajet prend plus de temps que l'attente + marge
            time_difference = travel_time - estimated_service_time
            
            # Seuil de réorganisation (15 minutes)
            REORGANIZATION_THRESHOLD = 15
            
            if time_difference > REORGANIZATION_THRESHOLD:
                logger.info(
                    f"Réorganisation recommandée - Trajet: {travel_time}min, "
                    f"Attente: {estimated_service_time}min, Diff: {time_difference}min"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur évaluation réorganisation: {e}")
            return False
    
    @staticmethod
    def calculate_optimal_position(ticket, queue):
        """Calculer position optimale dans la file pour un ticket"""
        try:
            user = ticket.customer
            user_location = getattr(user, 'current_location', None)
            
            if not user_location:
                return ticket.position  # Garder position actuelle
            
            # Calculer temps de trajet
            travel_estimate = SmartTravelTimeCalculator.calculate_travel_time(
                user=user,
                origin_lat=float(user_location.latitude),
                origin_lng=float(user_location.longitude),
                dest_lat=float(queue.organization.latitude),
                dest_lng=float(queue.organization.longitude),
                organization=queue.organization
            )
            
            travel_time = travel_estimate['estimated_travel_minutes']
            
            # Trouver position optimale
            current_wait = 0
            optimal_position = 1
            
            for pos in range(1, queue.get_total_tickets() + 1):
                service_time = queue.get_estimated_wait_time_for_position(pos)
                
                # Position idéale: temps service ≈ temps trajet
                if abs(service_time - travel_time) < 10:  # Marge 10 min
                    optimal_position = pos
                    break
                
                if service_time > travel_time:
                    optimal_position = max(1, pos - 1)
                    break
            
            logger.info(f"Position optimale calculée: {optimal_position} (trajet: {travel_time}min)")
            return optimal_position
            
        except Exception as e:
            logger.error(f"Erreur calcul position optimale: {e}")
            return ticket.position


class LocationNotificationService:
    """
    Service de notifications basées sur localisation
    """
    
    @staticmethod
    def should_send_departure_notification(user, organization, appointment_time: datetime):
        """Déterminer s'il faut envoyer notification de départ"""
        try:
            user_location = getattr(user, 'current_location', None)
            
            if not user_location or not user_location.location_sharing_enabled:
                return False
            
            # Calculer temps de trajet
            travel_estimate = SmartTravelTimeCalculator.calculate_travel_time(
                user=user,
                origin_lat=float(user_location.latitude),
                origin_lng=float(user_location.longitude), 
                dest_lat=float(organization.latitude),
                dest_lng=float(organization.longitude),
                organization=organization,
                departure_time=timezone.now()
            )
            
            travel_time = travel_estimate['estimated_travel_minutes']
            recommended_departure = appointment_time - timedelta(minutes=travel_time)
            
            # Notifier 5 minutes avant l'heure recommandée
            notification_time = recommended_departure - timedelta(minutes=5)
            
            now = timezone.now()
            return now >= notification_time and now <= recommended_departure
            
        except Exception as e:
            logger.error(f"Erreur notification départ: {e}")
            return False