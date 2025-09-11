# apps/locations/views.py
"""
API REST pour géolocalisation intelligente SmartQueue
"""

from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsStaffOrAbove, IsAdminOrAbove
from .models import (
    Region, Commune, UserLocation, TravelTimeEstimate, 
    TrafficCondition, WeatherCondition
)
from .serializers import (
    RegionSerializer, CommuneSerializer, UserLocationSerializer,
    TravelTimeEstimateSerializer, TrafficConditionSerializer,
    LocationUpdateSerializer, TravelCalculationRequestSerializer
)
from .services import SmartTravelTimeCalculator, QueueReorganizationService
import logging

logger = logging.getLogger(__name__)


class RegionListView(generics.ListAPIView):
    """Liste des régions du Sénégal"""
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]


class CommuneListView(generics.ListAPIView):
    """Liste des communes/quartiers"""
    queryset = Commune.objects.all()
    serializer_class = CommuneSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['region', 'locality_type']
    search_fields = ['name', 'region__name']
    ordering = ['region__name', 'name']


class CommunesByRegionView(generics.ListAPIView):
    """Communes d'une région spécifique"""
    serializer_class = CommuneSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        region_id = self.kwargs['region_id']
        return Commune.objects.filter(region_id=region_id)


class UpdateUserLocationView(APIView):
    """Mettre à jour localisation utilisateur"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Mettre à jour position GPS utilisateur"""
        serializer = LocationUpdateSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                latitude = serializer.validated_data['latitude']
                longitude = serializer.validated_data['longitude']
                accuracy = serializer.validated_data.get('accuracy_meters', 50)
                transport_mode = serializer.validated_data.get('transport_mode', 'car')
                sharing_enabled = serializer.validated_data.get('location_sharing_enabled', True)
                
                # Mettre à jour ou créer localisation
                user_location, created = UserLocation.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'latitude': latitude,
                        'longitude': longitude,
                        'accuracy_meters': accuracy,
                        'transport_mode': transport_mode,
                        'location_sharing_enabled': sharing_enabled,
                        'last_updated': timezone.now()
                    }
                )
                
                # Mettre à jour commune la plus proche
                user_location.update_nearest_commune()
                
                # Réponse
                response_data = {
                    'success': True,
                    'location_updated': True,
                    'nearest_commune': user_location.nearest_commune.name if user_location.nearest_commune else None,
                    'sharing_enabled': user_location.location_sharing_enabled
                }
                
                logger.info(f"Location updated for user {request.user.email}: {user_location.nearest_commune}")
                
                return Response(response_data, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Erreur MAJ localisation: {e}")
                return Response(
                    {'error': 'Erreur mise à jour localisation'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GetUserLocationView(APIView):
    """Obtenir localisation actuelle utilisateur"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Localisation actuelle de l'utilisateur"""
        try:
            user_location = UserLocation.objects.get(user=request.user)
            serializer = UserLocationSerializer(user_location)
            
            return Response({
                'location': serializer.data,
                'is_fresh': user_location.is_location_fresh(),
                'sharing_enabled': user_location.location_sharing_enabled
            })
            
        except UserLocation.DoesNotExist:
            return Response(
                {'error': 'Localisation non disponible'},
                status=status.HTTP_404_NOT_FOUND
            )


class CalculateTravelTimeView(APIView):
    """Calculer temps de trajet intelligent"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Calculer temps trajet vers organisation"""
        serializer = TravelCalculationRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                organization_id = serializer.validated_data['organization_id']
                departure_time = serializer.validated_data.get('departure_time', timezone.now())
                
                # Vérifier localisation utilisateur
                try:
                    user_location = request.user.current_location
                except UserLocation.DoesNotExist:
                    return Response(
                        {'error': 'Localisation utilisateur requise'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Vérifier organisation
                from apps.business.models import Organization
                try:
                    organization = Organization.objects.get(id=organization_id)
                except Organization.DoesNotExist:
                    return Response(
                        {'error': 'Organisation non trouvée'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                # Vérifier que l'organisation a des coordonnées
                if not organization.latitude or not organization.longitude:
                    return Response(
                        {'error': 'Organisation sans coordonnées GPS'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Calculer temps de trajet
                travel_data = SmartTravelTimeCalculator.calculate_travel_time(
                    user=request.user,
                    origin_lat=float(user_location.latitude),
                    origin_lng=float(user_location.longitude),
                    dest_lat=float(organization.latitude),
                    dest_lng=float(organization.longitude),
                    organization=organization,
                    departure_time=departure_time
                )
                
                # Sauvegarder estimation
                estimate = TravelTimeEstimate.objects.create(
                    user=request.user,
                    origin_latitude=user_location.latitude,
                    origin_longitude=user_location.longitude,
                    origin_commune=travel_data['origin_commune'],
                    destination_latitude=organization.latitude,
                    destination_longitude=organization.longitude,
                    destination_commune=travel_data['destination_commune'],
                    organization=organization,
                    estimated_travel_minutes=travel_data['estimated_travel_minutes'],
                    distance_km=travel_data['distance_km'],
                    transport_mode=travel_data['transport_mode'],
                    traffic_factor_applied=travel_data['traffic_factor'],
                    weather_factor_applied=travel_data['weather_factor'],
                    time_of_day_factor=travel_data.get('time_of_day_factor', 1.0),
                    safety_margin_minutes=travel_data['safety_margin_minutes'],
                    recommended_departure_time=departure_time,
                    estimated_arrival_time=travel_data['estimated_arrival_time'],
                    confidence_score=travel_data['confidence_score'],
                    calculation_source=travel_data['calculation_source']
                )
                
                response_data = {
                    'travel_time_minutes': travel_data['estimated_travel_minutes'],
                    'distance_km': travel_data['distance_km'],
                    'transport_mode': travel_data['transport_mode'],
                    'recommended_departure_time': travel_data['departure_time'].isoformat(),
                    'estimated_arrival_time': travel_data['estimated_arrival_time'].isoformat(),
                    'confidence_score': travel_data['confidence_score'],
                    'factors': {
                        'traffic': travel_data['traffic_factor'],
                        'route': travel_data.get('route_factor', 1.0),
                        'weather': travel_data['weather_factor']
                    },
                    'safety_margin_minutes': travel_data['safety_margin_minutes'],
                    'is_rush_hour': travel_data['is_rush_hour'],
                    'estimate_id': estimate.id
                }
                
                logger.info(
                    f"Travel time calculated: {request.user.email} → {organization.name} "
                    f"({travel_data['estimated_travel_minutes']}min)"
                )
                
                return Response(response_data, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Erreur calcul temps trajet: {e}")
                return Response(
                    {'error': 'Erreur calcul temps de trajet'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserTravelEstimatesView(generics.ListAPIView):
    """Historique estimations utilisateur"""
    serializer_class = TravelTimeEstimateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return TravelTimeEstimate.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:20]


class TrafficConditionsView(generics.ListAPIView):
    """Conditions de circulation actuelles"""
    queryset = TrafficCondition.objects.all()
    serializer_class = TrafficConditionSerializer
    permission_classes = [IsStaffOrAbove]
    filterset_fields = ['status', 'source_commune', 'destination_commune']
    ordering = ['-last_updated']


class NearbyOrganizationsView(APIView):
    """Organisations proches de l'utilisateur"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Organisations dans un rayon donné"""
        try:
            # Paramètres
            radius_km = float(request.GET.get('radius_km', 10))
            max_results = int(request.GET.get('max_results', 20))
            
            # Localisation utilisateur
            try:
                user_location = request.user.current_location
            except UserLocation.DoesNotExist:
                return Response(
                    {'error': 'Localisation utilisateur requise'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Organisations proches
            from apps.business.models import Organization
            from apps.business.serializers import OrganizationListSerializer
            
            nearby_organizations = []
            
            for org in Organization.objects.filter(is_active=True):
                # Vérifier que l'organisation a des coordonnées
                if not org.latitude or not org.longitude:
                    continue
                    
                distance = user_location.calculate_distance_to_commune(org)
                
                if distance and distance <= radius_km:
                    # Calculer temps de trajet rapide
                    try:
                        travel_data = SmartTravelTimeCalculator.calculate_travel_time(
                            user=request.user,
                            origin_lat=float(user_location.latitude),
                            origin_lng=float(user_location.longitude),
                            dest_lat=float(org.latitude),
                            dest_lng=float(org.longitude),
                            organization=org
                        )
                        
                        nearby_organizations.append({
                            'organization': OrganizationListSerializer(org).data,
                            'distance_km': round(distance, 2),
                            'travel_time_minutes': travel_data['estimated_travel_minutes'],
                            'confidence': travel_data['confidence_score']
                        })
                        
                    except Exception:
                        # Fallback si calcul échoue
                        nearby_organizations.append({
                            'organization': OrganizationListSerializer(org).data,
                            'distance_km': round(distance, 2),
                            'travel_time_minutes': int(distance * 2),  # Estimation simple
                            'confidence': 50
                        })
            
            # Trier par distance
            nearby_organizations.sort(key=lambda x: x['distance_km'])
            
            return Response({
                'organizations': nearby_organizations[:max_results],
                'user_location': {
                    'commune': user_location.nearest_commune.name if user_location.nearest_commune else None,
                    'last_updated': user_location.last_updated
                },
                'search_radius_km': radius_km
            })
            
        except Exception as e:
            logger.error(f"Erreur recherche organisations proches: {e}")
            return Response(
                {'error': 'Erreur recherche organisations'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsStaffOrAbove])
def trigger_queue_reorganization(request, queue_id):
    """Déclencher manuellement réorganisation de file"""
    try:
        from apps.queue_management.models import Queue
        
        queue = Queue.objects.get(id=queue_id)
        
        # Tickets avec géolocalisation
        tickets_with_location = queue.tickets.filter(
            status__in=['waiting', 'called'],
            customer__current_location__location_sharing_enabled=True
        )
        
        reorganized_count = 0
        
        for ticket in tickets_with_location:
            should_reorganize = QueueReorganizationService.should_reorganize_queue(ticket, queue)
            
            if should_reorganize:
                optimal_position = QueueReorganizationService.calculate_optimal_position(ticket, queue)
                
                if optimal_position != ticket.position:
                    old_position = ticket.position
                    ticket.position = optimal_position
                    ticket.save(update_fields=['position'])
                    
                    reorganized_count += 1
                    
                    logger.info(f"Ticket {ticket.id} moved: {old_position} → {optimal_position}")
        
        if reorganized_count > 0:
            queue.reorder_tickets()
        
        return Response({
            'success': True,
            'queue_id': queue_id,
            'tickets_reorganized': reorganized_count,
            'message': f'{reorganized_count} tickets repositionnés selon géolocalisation'
        })
        
    except Queue.DoesNotExist:
        return Response(
            {'error': 'File non trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Erreur réorganisation manuelle: {e}")
        return Response(
            {'error': 'Erreur réorganisation'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
