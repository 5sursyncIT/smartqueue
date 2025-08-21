# apps/services/views.py
"""
ViewSets pour les services SmartQueue
Gèrent les requêtes HTTP et utilisent les serializers appropriés
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Service, ServiceCategory
from .serializers import (
    ServiceListSerializer, ServiceDetailSerializer,
    ServiceCreateSerializer, ServiceUpdateSerializer, 
    ServiceStatsSerializer, ServiceCategorySerializer
)

@extend_schema_view(
    list=extend_schema(
        summary="Liste des services",
        description="Récupérer tous les services avec filtrage possible",
        tags=["Services"]
    ),
    retrieve=extend_schema(
        summary="Détails d'un service",
        description="Récupérer toutes les informations d'un service spécifique",
        tags=["Services"]
    ),
    create=extend_schema(
        summary="Créer un service",
        description="Créer un nouveau service pour une organisation",
        tags=["Services"]
    ),
    update=extend_schema(
        summary="Modifier un service",
        description="Modifier les informations d'un service existant",
        tags=["Services"]
    ),
    destroy=extend_schema(
        summary="Supprimer un service",
        description="Supprimer définitivement un service",
        tags=["Services"]
    )
)
class ServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal pour les services
    
    Fournit les opérations CRUD complètes :
    - GET /api/services/ (liste)
    - GET /api/services/1/ (détails)
    - POST /api/services/ (création)
    - PUT/PATCH /api/services/1/ (modification)
    - DELETE /api/services/1/ (suppression)
    """
    
    queryset = Service.objects.select_related('organization', 'category').all()
    
    # Filtrage et recherche
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'organization', 'category', 'status', 'default_priority',
        'is_public', 'allows_appointments', 'requires_appointment'
    ]
    search_fields = ['name', 'code', 'description', 'instructions']
    ordering_fields = ['name', 'created_at', 'estimated_duration', 'cost']
    ordering = ['display_order', 'name']  # Tri par défaut
    
    def get_serializer_class(self):
        """
        Retourne le bon serializer selon l'action
        """
        if self.action == 'list':
            return ServiceListSerializer
        elif self.action == 'retrieve':
            return ServiceDetailSerializer
        elif self.action == 'create':
            return ServiceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ServiceUpdateSerializer
        elif self.action == 'stats':
            return ServiceStatsSerializer
        
        return ServiceDetailSerializer
    
    def get_permissions(self):
        """
        Définit les permissions selon l'action et le type d'utilisateur
        """
        if self.action in ['list', 'retrieve']:
            # Tout le monde peut voir les services publics
            permission_classes = [permissions.AllowAny]
        elif self.action == 'create':
            # Seuls les admins d'organisation et super admins
            permission_classes = [permissions.IsAuthenticated, IsOrganizationAdminOrSuperAdmin]
        elif self.action in ['update', 'partial_update', 'destroy']:
            # Admin de l'organisation ou super admin
            permission_classes = [permissions.IsAuthenticated, IsServiceOwnerOrSuperAdmin]
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
            # Utilisateurs anonymes : seulement les services publics actifs
            return Service.objects.filter(
                is_public=True, 
                status='active',
                organization__is_active=True
            ).select_related('organization', 'category')
        
        if user.is_super_admin:
            # Super admin voit tous les services
            return Service.objects.select_related('organization', 'category').all()
        elif user.is_organization_admin:
            # Admin d'organisation voit seulement les services de son organisation
            if hasattr(user, 'staff_profile'):
                return Service.objects.filter(
                    organization=user.staff_profile.organization
                ).select_related('organization', 'category')
        
        # Autres utilisateurs : services publics actifs
        return Service.objects.filter(
            is_public=True,
            status='active',
            organization__is_active=True
        ).select_related('organization', 'category')
    
    @extend_schema(
        summary="Statistiques d'un service",
        description="Récupérer les statistiques en temps réel d'un service",
        tags=["Services", "Statistiques"]
    )
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """
        Endpoint pour les statistiques d'un service
        GET /api/services/1/stats/
        """
        service = self.get_object()
        serializer = ServiceStatsSerializer(service)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Files d'attente d'un service",
        description="Récupérer toutes les files d'attente associées à un service",
        tags=["Services", "Files d'attente"]
    )
    @action(detail=True, methods=['get'])
    def queues(self, request, pk=None):
        """
        Endpoint pour les files d'attente d'un service
        GET /api/services/1/queues/
        """
        service = self.get_object()
        queues = service.queues.filter(is_active=True)
        
        # Import dynamique pour éviter les imports circulaires
        from apps.queues.serializers import QueueListSerializer
        serializer = QueueListSerializer(queues, many=True)
        
        return Response({
            'service': service.name,
            'organization': service.organization.name,
            'queues_count': queues.count(),
            'active_queues': queues.filter(current_status='active').count(),
            'queues': serializer.data
        })
    
    @extend_schema(
        summary="Historique des tickets d'un service",
        description="Récupérer l'historique des tickets pour un service",
        tags=["Services", "Tickets"]
    )
    @action(detail=True, methods=['get'])
    def tickets_history(self, request, pk=None):
        """
        Endpoint pour l'historique des tickets d'un service
        GET /api/services/1/tickets_history/
        """
        service = self.get_object()
        tickets = service.tickets.all()[:50]  # 50 derniers tickets
        
        # Import dynamique
        from apps.tickets.serializers import TicketListSerializer
        serializer = TicketListSerializer(tickets, many=True)
        
        return Response({
            'service': service.name,
            'total_tickets': service.total_tickets_issued,
            'recent_tickets': serializer.data
        })
    
    @extend_schema(
        summary="Services par organisation",
        description="Récupérer tous les services d'une organisation spécifique",
        parameters=[
            {
                'name': 'organization_id',
                'in': 'query',
                'required': True,
                'schema': {'type': 'integer'},
                'description': 'ID de l\'organisation'
            }
        ],
        tags=["Services", "Organisations"]
    )
    @action(detail=False, methods=['get'])
    def by_organization(self, request):
        """
        Filtrer les services par organisation
        GET /api/services/by_organization/?organization_id=1
        """
        organization_id = request.query_params.get('organization_id')
        
        if not organization_id:
            return Response({
                'error': 'Paramètre organization_id manquant',
                'example': '/api/services/by_organization/?organization_id=1'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            organization_id = int(organization_id)
        except ValueError:
            return Response({
                'error': 'organization_id doit être un nombre entier'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filtrer les services
        services = self.get_queryset().filter(organization_id=organization_id)
        
        # Sérialiser
        serializer = ServiceListSerializer(services, many=True)
        
        return Response({
            'organization_id': organization_id,
            'services_count': services.count(),
            'services': serializer.data
        })
    
    @extend_schema(
        summary="Services par catégorie",
        description="Récupérer tous les services d'une catégorie spécifique",
        parameters=[
            {
                'name': 'category_id',
                'in': 'query',
                'required': True,
                'schema': {'type': 'integer'},
                'description': 'ID de la catégorie'
            }
        ],
        tags=["Services", "Catégories"]
    )
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """
        Filtrer les services par catégorie
        GET /api/services/by_category/?category_id=1
        """
        category_id = request.query_params.get('category_id')
        
        if not category_id:
            return Response({
                'error': 'Paramètre category_id manquant',
                'example': '/api/services/by_category/?category_id=1'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            category_id = int(category_id)
        except ValueError:
            return Response({
                'error': 'category_id doit être un nombre entier'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filtrer les services
        services = self.get_queryset().filter(category_id=category_id)
        
        # Sérialiser
        serializer = ServiceListSerializer(services, many=True)
        
        return Response({
            'category_id': category_id,
            'services_count': services.count(),
            'services': serializer.data
        })


@extend_schema_view(
    list=extend_schema(
        summary="Liste des catégories de services",
        description="Récupérer toutes les catégories de services",
        tags=["Catégories"]
    ),
    retrieve=extend_schema(
        summary="Détails d'une catégorie",
        description="Récupérer les détails d'une catégorie de service",
        tags=["Catégories"]
    ),
    create=extend_schema(
        summary="Créer une catégorie",
        description="Créer une nouvelle catégorie de service",
        tags=["Catégories"]
    )
)
class ServiceCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les catégories de services
    
    Gère les catégories comme "Comptes", "Consultations", etc.
    """
    
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'display_order', 'created_at']
    ordering = ['display_order', 'name']
    
    def get_permissions(self):
        """
        Permissions pour les catégories
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
        
        return [permission() for permission in permission_classes]


# ==============================================
# PERMISSIONS PERSONNALISÉES
# ==============================================

class IsSuperAdmin(permissions.BasePermission):
    """
    Permission pour les super admins SmartQueue uniquement
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_super_admin


class IsOrganizationAdminOrSuperAdmin(permissions.BasePermission):
    """
    Permission pour :
    - Super admins SmartQueue (accès total)
    - Admins d'organisation (pour leur org seulement)
    """
    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        
        return user.is_super_admin or user.is_organization_admin


class IsServiceOwnerOrSuperAdmin(permissions.BasePermission):
    """
    Permission pour :
    - Super admins SmartQueue (accès total)
    - Admins de l'organisation qui possède le service
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Super admin a accès à tout
        if user.is_super_admin:
            return True
        
        # Admin d'organisation a accès aux services de son organisation
        if user.is_organization_admin and hasattr(user, 'staff_profile'):
            return user.staff_profile.organization == obj.organization
        
        return False


# ==============================================
# VIEWSETS SUPPLÉMENTAIRES
# ==============================================

class PublicServiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet public pour les services (sans authentification)
    
    Usage : App mobile grand public
    GET /api/public/services/
    """
    queryset = Service.objects.filter(
        is_public=True, 
        status='active',
        organization__is_active=True
    ).select_related('organization', 'category')
    
    serializer_class = ServiceListSerializer
    permission_classes = [permissions.AllowAny]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['organization', 'category', 'allows_appointments']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']