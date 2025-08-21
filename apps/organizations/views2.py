# apps/organizations/views.py
"""
ViewSets pour les organisations SmartQueue
Gèrent les endpoints API REST
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance
from .models import Organization
from .serializers import (
    OrganizationListSerializer,
    OrganizationDetailSerializer, 
    OrganizationCreateSerializer,
    OrganizationUpdateSerializer,
    OrganizationStatsSerializer
)

class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les organisations
    
    Endpoints générés automatiquement :
    - GET /api/organizations/ → Liste des organisations
    - GET /api/organizations/1/ → Détail d'une organisation  
    - POST /api/organizations/ → Créer une organisation
    - PUT /api/organizations/1/ → Modifier une organisation
    - DELETE /api/organizations/1/ → Supprimer une organisation
    """
    
    queryset = Organization.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    
    # Configuration du filtrage et recherche
    filter_backends = [
        DjangoFilterBackend,    # Filtrage par champs
        filters.SearchFilter,   # Recherche textuelle
        filters.OrderingFilter  # Tri
    ]
    
    # Champs sur lesquels on peut filtrer
    filterset_fields = {
        'type': ['exact', 'in'],                    # ?type=bank ou ?type__in=bank,hospital
        'region': ['exact', 'in'],                  # ?region=dakar
        'city': ['icontains'],                      # ?city__icontains=dakar
        'subscription_plan': ['exact'],             # ?subscription_plan=enterprise
        'status': ['exact', 'in'],                  # ?status=active
        'created_at': ['date', 'date__gte', 'date__lte']  # ?created_at__date=2025-08-15
    }
    
    # Champs dans lesquels rechercher avec ?search=
    search_fields = ['name', 'trade_name', 'description', 'city']
    
    # Champs sur lesquels on peut trier avec ?ordering=
    ordering_fields = ['name', 'created_at', 'city', 'subscription_plan']
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
        Permissions selon l'action et le type d'utilisateur
        """
        if self.action in ['list', 'retrieve']:
            # Lecture : tous les utilisateurs authentifiés
            permission_classes = [permissions.IsAuthenticated]
            
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Écriture : seulement super admins
            permission_classes = [permissions.IsAuthenticated]
            
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """
        Logique personnalisée lors de la création
        """
        # Associer l'utilisateur créateur
        serializer.save(created_by=self.request.user)
    
    def get_queryset(self):
        """
        Filtrer les organisations selon l'utilisateur connecté
        """
        user = self.request.user
        queryset = Organization.objects.filter(is_active=True)
        
        # Super admins voient tout
        if user.is_super_admin:
            return queryset
            
        # Organization admins voient seulement leur organisation
        elif user.is_organization_admin:
            # TODO: Implémenter la relation user -> organization
            return queryset
            
        # Staff voient seulement leur organisation
        elif user.is_staff_member:
            # TODO: Implémenter la relation user -> organization  
            return queryset
            
        # Clients voient toutes les organisations publiques
        else:
            return queryset
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        Endpoint personnalisé : organisations proches
        
        Usage : GET /api/organizations/nearby/?latitude=14.6928&longitude=-17.4441&radius=10
        """
        try:
            latitude = float(request.query_params.get('latitude'))
            longitude = float(request.query_params.get('longitude'))
            radius = int(request.query_params.get('radius', 10))  # 10km par défaut
        except (TypeError, ValueError):
            return Response({
                'error': 'Paramètres latitude, longitude requis (nombres)'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filtrer les organisations dans le rayon
        # Note : Pour SQLite, on fait un calcul simple. En production avec PostGIS, on utilisera ST_Distance
        nearby_orgs = []
        for org in self.get_queryset():
            if org.latitude and org.longitude:
                # Calcul distance approximatif (formule haversine simplifiée)
                lat_diff = abs(float(org.latitude) - latitude)
                lng_diff = abs(float(org.longitude) - longitude)
                distance_approx = ((lat_diff ** 2) + (lng_diff ** 2)) ** 0.5 * 111  # 111km par degré approx
                
                if distance_approx <= radius:
                    nearby_orgs.append(org)
        
        # Sérialiser et retourner
        serializer = OrganizationListSerializer(nearby_orgs, many=True)
        return Response({
            'count': len(nearby_orgs),
            'radius_km': radius,
            'center': {'latitude': latitude, 'longitude': longitude},
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def services(self, request, pk=None):
        """
        Endpoint personnalisé : services d'une organisation
        
        Usage : GET /api/organizations/1/services/
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
    
    @action(detail=True, methods=['get'])
    def queues(self, request, pk=None):
        """
        Endpoint personnalisé : files d'attente d'une organisation
        
        Usage : GET /api/organizations/1/queues/
        """
        organization = self.get_object()
        queues = organization.queues.filter(is_active=True)
        
        # Filtrer par statut si demandé
        status_filter = request.query_params.get('status')
        if status_filter:
            queues = queues.filter(current_status=status_filter)
        
        # Import dynamique
        from apps.queues.serializers import QueueListSerializer
        serializer = QueueListSerializer(queues, many=True)
        
        return Response({
            'organization': organization.name,
            'queues_count': queues.count(),
            'queues': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Endpoint personnalisé : statistiques d'une organisation
        
        Usage : GET /api/organizations/1/stats/
        """
        organization = self.get_object()
        serializer = OrganizationStatsSerializer(organization)
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Endpoint personnalisé : types d'organisations disponibles
        
        Usage : GET /api/organizations/types/
        """
        types_data = [
            {'key': key, 'label': label} 
            for key, label in Organization.ORGANIZATION_TYPES
        ]
        
        return Response({
            'types': types_data,
            'regions': [
                {'key': key, 'label': label}
                for key, label in Organization.SENEGAL_REGIONS
            ],
            'subscription_plans': [
                {'key': key, 'label': label}
                for key, label in Organization.SUBSCRIPTION_PLANS
            ]
        })
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Endpoint personnalisé : tableau de bord général
        
        Usage : GET /api/organizations/dashboard/
        Réservé aux super admins
        """
        if not request.user.is_super_admin:
            return Response({
                'error': 'Accès réservé aux super administrateurs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        queryset = self.get_queryset()
        
        # Statistiques globales
        stats = {
            'total_organizations': queryset.count(),
            'by_type': {},
            'by_region': {},
            'by_subscription_plan': {},
            'by_status': {},
            'recent_registrations': queryset.order_by('-created_at')[:5].values(
                'id', 'name', 'type', 'created_at'
            )
        }
        
        # Grouper par type
        for org_type, org_type_label in Organization.ORGANIZATION_TYPES:
            count = queryset.filter(type=org_type).count()
            if count > 0:
                stats['by_type'][org_type] = {
                    'label': org_type_label,
                    'count': count
                }
        
        # Grouper par région
        for region, region_label in Organization.SENEGAL_REGIONS:
            count = queryset.filter(region=region).count()
            if count > 0:
                stats['by_region'][region] = {
                    'label': region_label,
                    'count': count
                }
        
        # Grouper par plan d'abonnement
        for plan, plan_label in Organization.SUBSCRIPTION_PLANS:
            count = queryset.filter(subscription_plan=plan).count()
            if count > 0:
                stats['by_subscription_plan'][plan] = {
                    'label': plan_label,
                    'count': count
                }
        
        return Response(stats)


class OrganizationPermission(permissions.BasePermission):
    """
    Permission personnalisée pour les organisations
    """
    
    def has_permission(self, request, view):
        """
        Vérifier les permissions au niveau de la vue
        """
        # Utilisateur doit être authentifié
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Lecture : tous les utilisateurs authentifiés
        if view.action in ['list', 'retrieve', 'nearby', 'types']:
            return True
            
        # Écriture : seulement super admins
        if view.action in ['create', 'update', 'partial_update', 'destroy']:
            return request.user.is_super_admin
            
        # Actions spécialisées : selon le contexte
        if view.action in ['services', 'queues', 'stats']:
            return True
            
        if view.action == 'dashboard':
            return request.user.is_super_admin
        
        return False
    
    def has_object_permission(self, request, view, obj):
        """
        Vérifier les permissions au niveau de l'objet
        """
        # Super admins : accès total
        if request.user.is_super_admin:
            return True
            
        # Organization admins : seulement leur organisation
        if request.user.is_organization_admin:
            # TODO: Vérifier que user.organization == obj
            return True
            
        # Staff : seulement leur organisation en lecture
        if request.user.is_staff_member:
            if view.action in ['retrieve', 'services', 'queues', 'stats']:
                # TODO: Vérifier que user.organization == obj
                return True
            return False
            
        # Clients : lecture seulement
        if view.action in ['retrieve', 'services', 'queues']:
            return True
            
        return False
