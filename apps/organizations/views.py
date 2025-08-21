# apps/organizations/views.py
"""
ViewSets pour les organisations SmartQueue
Gèrent les requêtes HTTP et utilisent les serializers appropriés
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Organization
from .serializers import (
    OrganizationListSerializer, OrganizationDetailSerializer,
    OrganizationCreateSerializer, OrganizationUpdateSerializer,
    OrganizationStatsSerializer
)

@extend_schema_view(
    list=extend_schema(
        summary="Liste des organisations",
        description="Récupérer toutes les organisations actives avec filtrage possible",
        tags=["Organisations"]
    ),
    retrieve=extend_schema(
        summary="Détails d'une organisation",
        description="Récupérer toutes les informations d'une organisation spécifique",
        tags=["Organisations"]
    ),
    create=extend_schema(
        summary="Créer une organisation",
        description="Créer une nouvelle organisation cliente de SmartQueue",
        tags=["Organisations"]
    ),
    update=extend_schema(
        summary="Modifier une organisation",
        description="Modifier les informations d'une organisation existante",
        tags=["Organisations"]
    ),
    destroy=extend_schema(
        summary="Supprimer une organisation",
        description="Supprimer définitivement une organisation",
        tags=["Organisations"]
    )
)
class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal pour les organisations
    
    Fournit les opérations CRUD complètes :
    - GET /api/organizations/ (liste)
    - GET /api/organizations/1/ (détails)
    - POST /api/organizations/ (création)
    - PUT/PATCH /api/organizations/1/ (modification)
    - DELETE /api/organizations/1/ (suppression)
    """
    
    queryset = Organization.objects.filter(is_active=True)
    
    # Filtrage et recherche
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'region', 'city', 'subscription_plan', 'status']
    search_fields = ['name', 'trade_name', 'description', 'email']
    ordering_fields = ['name', 'created_at', 'city']
    ordering = ['name']  # Tri par défaut
    
    def get_serializer_class(self):
        """
        Retourne le bon serializer selon l'action
        """
        if self.action == 'list':
            return OrganizationListSerializer
        elif self.action == 'retrieve':
            return OrganizationDetailSerializer
        elif self.action == 'create':
            return OrganizationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return OrganizationUpdateSerializer
        elif self.action == 'stats':
            return OrganizationStatsSerializer
        
        return OrganizationDetailSerializer
    
    def get_permissions(self):
        """
        Définit les permissions selon l'action et le type d'utilisateur
        """
        if self.action == 'list':
            # Tout le monde peut voir la liste des organisations
            permission_classes = [permissions.AllowAny]
        elif self.action == 'retrieve':
            # Tout le monde peut voir les détails d'une organisation
            permission_classes = [permissions.AllowAny]
        elif self.action == 'create':
            # Seuls les super admins peuvent créer des organisations
            permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Super admins + admin de l'organisation concernée
            permission_classes = [permissions.IsAuthenticated, IsSuperAdminOrOrganizationAdmin]
        else:
            # Actions personnalisées : utilisateur connecté
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """
        Filtre le queryset selon le type d'utilisateur
        """
        user = self.request.user
        
        if not user.is_authenticated:
            # Utilisateurs anonymes : seulement les organisations publiques
            return Organization.objects.filter(is_active=True, status='active')
        
        if user.is_super_admin:
            # Super admin voit toutes les organisations
            return Organization.objects.all()
        elif user.is_organization_admin:
            # Admin d'organisation voit seulement la sienne
            if hasattr(user, 'staff_profile'):
                return Organization.objects.filter(
                    id=user.staff_profile.organization.id
                )
        
        # Autres utilisateurs : organisations actives
        return Organization.objects.filter(is_active=True)
    
    @extend_schema(
        summary="Statistiques d'une organisation",
        description="Récupérer les statistiques en temps réel d'une organisation",
        tags=["Organisations", "Statistiques"]
    )
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Endpoint pour les statistiques d'une organisation
        GET /api/organizations/1/stats/
        """
        organization = self.get_object()
        serializer = OrganizationStatsSerializer(organization)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Services d'une organisation",
        description="Récupérer tous les services offerts par une organisation",
        tags=["Organisations", "Services"]
    )
    @action(detail=True, methods=['get'])
    def services(self, request, pk=None):
        """
        Endpoint pour les services d'une organisation
        GET /api/organizations/1/services/
        """
        organization = self.get_object()
        services = organization.services.filter(is_public=True, status='active')
        
        # Import dynamique pour éviter les imports circulaires
        from apps.services.serializers import ServiceListSerializer
        serializer = ServiceListSerializer(services, many=True)
        
        return Response({
            'organization': organization.name,
            'services_count': services.count(),
            'services': serializer.data
        })
    
    @extend_schema(
        summary="Files d'attente d'une organisation",
        description="Récupérer toutes les files d'attente actives d'une organisation",
        tags=["Organisations", "Files d'attente"]
    )
    @action(detail=True, methods=['get'])
    def queues(self, request, pk=None):
        """
        Endpoint pour les files d'attente d'une organisation
        GET /api/organizations/1/queues/
        """
        organization = self.get_object()
        queues = organization.queues.filter(is_active=True)
        
        # Import dynamique
        from apps.queues.serializers import QueueListSerializer
        serializer = QueueListSerializer(queues, many=True)
        
        return Response({
            'organization': organization.name,
            'queues_count': queues.count(),
            'active_queues': queues.filter(current_status='active').count(),
            'queues': serializer.data
        })
    
    @extend_schema(
        summary="Organisations proches",
        description="Trouver les organisations dans un rayon donné",
        parameters=[
            {
                'name': 'latitude',
                'in': 'query',
                'required': True,
                'schema': {'type': 'number'},
                'description': 'Latitude GPS (ex: 14.6928 pour Dakar)'
            },
            {
                'name': 'longitude', 
                'in': 'query',
                'required': True,
                'schema': {'type': 'number'},
                'description': 'Longitude GPS (ex: -17.4441 pour Dakar)'
            },
            {
                'name': 'radius',
                'in': 'query',
                'required': False,
                'schema': {'type': 'integer', 'default': 10},
                'description': 'Rayon de recherche en kilomètres'
            },
            {
                'name': 'type',
                'in': 'query',
                'required': False,
                'schema': {'type': 'string'},
                'description': 'Filtrer par type (bank, hospital, government, etc.)'
            }
        ],
        tags=["Organisations", "Géolocalisation"]
    )
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        Trouver les organisations proches d'une position GPS
        GET /api/organizations/nearby/?latitude=14.6928&longitude=-17.4441&radius=10
        """
        try:
            latitude = float(request.query_params.get('latitude'))
            longitude = float(request.query_params.get('longitude'))
            radius = int(request.query_params.get('radius', 10))  # 10km par défaut
            org_type = request.query_params.get('type')
        except (TypeError, ValueError):
            return Response({
                'error': 'Paramètres latitude/longitude invalides ou manquants',
                'example': '/api/organizations/nearby/?latitude=14.6928&longitude=-17.4441&radius=10'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user_location = Point(longitude, latitude)
        
        # Queryset de base
        queryset = self.get_queryset().filter(
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        # Filtrer par type si spécifié
        if org_type:
            queryset = queryset.filter(type=org_type)
        
        # Calculer la distance et filtrer par rayon
        nearby_orgs = []
        for org in queryset:
            if org.latitude and org.longitude:
                org_location = Point(float(org.longitude), float(org.latitude))
                distance_km = user_location.distance(org_location) * 111  # Conversion approximative en km
                
                if distance_km <= radius:
                    nearby_orgs.append({
                        'organization': org,
                        'distance_km': round(distance_km, 2)
                    })
        
        # Trier par distance
        nearby_orgs.sort(key=lambda x: x['distance_km'])
        
        # Sérialiser les résultats
        results = []
        for item in nearby_orgs:
            org_data = OrganizationListSerializer(item['organization']).data
            org_data['distance_km'] = item['distance_km']
            results.append(org_data)
        
        return Response({
            'search_center': {
                'latitude': latitude,
                'longitude': longitude,
                'radius_km': radius
            },
            'results_count': len(results),
            'organizations': results
        })
    
    @extend_schema(
        summary="Tableau de bord organisation",
        description="Vue d'ensemble des activités d'une organisation",
        tags=["Organisations", "Tableau de bord"]
    )
    @action(detail=True, methods=['get'])
    def dashboard(self, request, pk=None):
        """
        Tableau de bord complet d'une organisation
        GET /api/organizations/1/dashboard/
        """
        organization = self.get_object()
        
        # Statistiques des files d'attente
        queues = organization.queues.filter(is_active=True)
        active_queues = queues.filter(current_status='active')
        
        # Statistiques des tickets aujourd'hui
        from django.utils import timezone
        today = timezone.now().date()
        today_tickets = sum(
            queue.daily_tickets_issued 
            for queue in queues.filter(stats_date=today)
        )
        today_served = sum(
            queue.daily_tickets_served 
            for queue in queues.filter(stats_date=today)
        )
        current_waiting = sum(
            queue.waiting_tickets_count 
            for queue in active_queues
        )
        
        # Services les plus utilisés
        popular_services = organization.services.filter(
            status='active'
        ).order_by('-total_tickets_issued')[:5]
        
        return Response({
            'organization': {
                'id': organization.id,
                'name': organization.name,
                'type': organization.get_type_display(),
                'status': organization.get_status_display()
            },
            'queues': {
                'total': queues.count(),
                'active': active_queues.count(),
                'paused': queues.filter(current_status='paused').count(),
                'closed': queues.filter(current_status='closed').count()
            },
            'tickets_today': {
                'issued': today_tickets,
                'served': today_served,
                'success_rate': round((today_served / today_tickets * 100) if today_tickets > 0 else 0, 1)
            },
            'current_status': {
                'waiting_customers': current_waiting,
                'average_wait_time': round(sum(
                    queue.estimated_wait_time for queue in active_queues
                ) / active_queues.count() if active_queues.count() > 0 else 0)
            },
            'popular_services': [
                {
                    'name': service.name,
                    'total_tickets': service.total_tickets_issued,
                    'average_rating': float(service.average_rating)
                }
                for service in popular_services
            ]
        })


# ==============================================
# PERMISSIONS PERSONNALISÉES
# ==============================================

class IsSuperAdmin(permissions.BasePermission):
    """
    Permission pour les super admins SmartQueue uniquement
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_super_admin


class IsSuperAdminOrOrganizationAdmin(permissions.BasePermission):
    """
    Permission pour :
    - Super admins SmartQueue (accès total)
    - Admins de l'organisation concernée (accès à leur org seulement)
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Super admin a accès à tout
        if user.is_super_admin:
            return True
        
        # Admin d'organisation a accès seulement à son organisation
        if user.is_organization_admin and hasattr(user, 'staff_profile'):
            return user.staff_profile.organization == obj
        
        return False


# ==============================================
# VIEWSETS SUPPLÉMENTAIRES
# ==============================================

class PublicOrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet public pour les organisations (sans authentification)
    
    Usage : App mobile grand public
    GET /api/public/organizations/
    """
    queryset = Organization.objects.filter(is_active=True, status='active')
    serializer_class = OrganizationListSerializer
    permission_classes = [permissions.AllowAny]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['type', 'region', 'city']
    search_fields = ['name', 'trade_name']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def public_services(self, request, pk=None):
        """
        Services publics d'une organisation
        GET /api/public/organizations/1/public_services/
        """
        organization = self.get_object()
        services = organization.services.filter(
            is_public=True, 
            status='active',
            requires_authentication=False
        )
        
        from apps.services.serializers import ServiceListSerializer
        serializer = ServiceListSerializer(services, many=True)
        
        return Response({
            'organization': organization.name,
            'services': serializer.data
        })