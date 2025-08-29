# apps/business/views.py
"""
Vues unifiées pour la gestion Business (Organizations + Services)
Approche superviseur : logique métier cohérente
"""

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

# Import depuis les modèles séparés
from .models import Organization, Service
from .serializers import (
    OrganizationListSerializer, OrganizationDetailSerializer,
    ServiceCreateSerializer, ServiceListSerializer, ServiceDetailSerializer
)

# ============================================
# VUES ORGANIZATIONS
# ============================================

class OrganizationListCreateView(generics.ListCreateAPIView):
    """Liste et création d'organisations"""
    queryset = Organization.objects.filter(is_active=True)
    serializer_class = OrganizationListSerializer
    permission_classes = [permissions.AllowAny]  # TEMPORAIRE pour tests
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['type', 'region', 'status']
    search_fields = ['name', 'trade_name', 'city']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']

class OrganizationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression d'organisation"""
    queryset = Organization.objects.filter(is_active=True)
    serializer_class = OrganizationDetailSerializer
    permission_classes = [permissions.AllowAny]  # TEMPORAIRE pour tests

# ============================================
# VUES SERVICES
# ============================================

class ServiceListCreateView(generics.ListCreateAPIView):
    """Liste et création de services"""
    queryset = Service.objects.filter(status='active')
    serializer_class = ServiceCreateSerializer  # FORCER le serializer simple
    permission_classes = [permissions.AllowAny]  # TEMPORAIRE pour tests
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['organization', 'category', 'status']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name', 'cost']
    ordering = ['name']

class ServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression de service"""
    queryset = Service.objects.filter(status='active')
    serializer_class = ServiceDetailSerializer
    permission_classes = [permissions.AllowAny]  # TEMPORAIRE pour tests

# ============================================
# VUES RELATIONS (Organizations -> Services)
# ============================================

class OrganizationServicesView(generics.ListAPIView):
    """Services d'une organisation spécifique"""
    serializer_class = ServiceListSerializer
    permission_classes = [permissions.AllowAny]  # TEMPORAIRE pour tests
    
    def get_queryset(self):
        organization_id = self.kwargs['organization_id']
        return Service.objects.filter(
            organization_id=organization_id,
            status='active'
        )

# ============================================
# VUES UTILITAIRES
# ============================================

@api_view(['GET'])
def business_stats(request):
    """Statistiques générales business"""
    stats = {
        'total_organizations': Organization.objects.filter(is_active=True).count(),
        'total_services': Service.objects.filter(is_active=True).count(),
        'organizations_by_type': {},
        'services_by_category': {}
    }
    
    # Stats par type d'organisation
    from django.db.models import Count
    org_types = Organization.objects.filter(is_active=True).values('type').annotate(count=Count('type'))
    stats['organizations_by_type'] = {item['type']: item['count'] for item in org_types}
    
    # Stats par catégorie de service
    service_cats = Service.objects.filter(is_active=True).values('category').annotate(count=Count('category'))
    stats['services_by_category'] = {item['category']: item['count'] for item in service_cats}
    
    return Response(stats)