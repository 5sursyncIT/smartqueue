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
    OrganizationListSerializer, OrganizationDetailSerializer, OrganizationCreateSerializer,
    ServiceCreateSerializer, ServiceListSerializer, ServiceDetailSerializer, ServiceSimpleListSerializer
)

# ============================================
# VUES ORGANIZATIONS
# ============================================

@api_view(['GET', 'POST'])
def organization_list_create_view(request):
    """Vue custom pour organisations - GARANTIE DE FONCTIONNER"""
    print(f"🔍 DEBUG ORG: Méthode {request.method}")
    
    if request.method == 'POST':
        print("🔍 DEBUG ORG: POST - Création organisation")
        serializer = OrganizationCreateSerializer(data=request.data)
        if serializer.is_valid():
            organization = serializer.save()
            print(f"🔍 DEBUG ORG: Organisation créée avec ID={organization.id}")
            
            # Retourner avec l'ID
            response_data = {
                'id': organization.id,
                'name': organization.name,
                'trade_name': organization.trade_name,
                'type': organization.type
            }
            print(f"🔍 DEBUG ORG: Réponse data={response_data}")
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            print(f"🔍 DEBUG ORG: Erreurs validation={serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    else:  # GET
        print("🔍 DEBUG ORG: GET - Liste organisations")
        organizations = Organization.objects.filter(is_active=True)
        serializer = OrganizationListSerializer(organizations, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data
        })

class OrganizationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression d'organisation"""
    queryset = Organization.objects.filter(is_active=True)
    serializer_class = OrganizationDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

# ============================================
# VUES SERVICES
# ============================================

from rest_framework.decorators import api_view
from rest_framework import status

@api_view(['GET', 'POST'])
def service_list_create_view(request):
    """Vue custom pour services - GARANTIE DE FONCTIONNER"""
    print(f"🔍 DEBUG VUE CUSTOM: Méthode {request.method}")
    
    if request.method == 'POST':
        print("🔍 DEBUG VUE CUSTOM: POST - Création service")
        serializer = ServiceCreateSerializer(data=request.data)
        if serializer.is_valid():
            service = serializer.save()
            print(f"🔍 DEBUG VUE CUSTOM: Service créé avec ID={service.id}")
            
            # Sérialiser la réponse avec l'ID
            response_serializer = ServiceCreateSerializer(service)
            print(f"🔍 DEBUG VUE CUSTOM: Réponse data={response_serializer.data}")
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            print(f"🔍 DEBUG VUE CUSTOM: Erreurs validation={serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    else:  # GET
        print("🔍 DEBUG VUE CUSTOM: GET - Liste services")
        services = Service.objects.filter(status='active')
        serializer = ServiceSimpleListSerializer(services, many=True)
        return Response(serializer.data)

# Garder l'ancienne classe pour compatibilité mais ne pas l'utiliser
class ServiceListCreateView_OLD(generics.ListCreateAPIView):
    """ANCIENNE Vue - ne plus utiliser"""
    pass
    

class ServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Détail, modification et suppression de service"""
    queryset = Service.objects.filter(status='active')
    serializer_class = ServiceDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

# ============================================
# VUES RELATIONS (Organizations -> Services)
# ============================================

class OrganizationServicesView(generics.ListAPIView):
    """Services d'une organisation spécifique"""
    serializer_class = ServiceListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
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
        'total_services': Service.objects.filter(status='active').count(),
        'organizations_by_type': {},
        'services_by_category': {}
    }
    
    # Stats par type d'organisation
    from django.db.models import Count
    org_types = Organization.objects.filter(is_active=True).values('type').annotate(count=Count('type'))
    stats['organizations_by_type'] = {item['type']: item['count'] for item in org_types}
    
    # Stats par catégorie de service
    service_cats = Service.objects.filter(status='active').values('category').annotate(count=Count('category'))
    stats['services_by_category'] = {item['category']: item['count'] for item in service_cats}
    
    return Response(stats)