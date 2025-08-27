# apps/core/permissions.py
"""
Permissions personnalisées SmartQueue
Système de permissions basé sur les rôles et contextes métier
"""

from rest_framework import permissions
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from .constants import UserTypes

User = get_user_model()


class BaseSmartQueuePermission(permissions.BasePermission):
    """
    Permission de base SmartQueue
    Inclut des helpers communs pour toutes les permissions
    """
    
    def has_user_type(self, user, required_types):
        """Vérifier si l'utilisateur a un des types requis"""
        if not user or not user.is_authenticated:
            return False
        
        if isinstance(required_types, str):
            required_types = [required_types]
        
        user_type = getattr(user, 'user_type', None)
        return user_type in required_types
    
    def has_higher_or_equal_permission(self, user, required_type):
        """Vérifier si l'utilisateur a des permissions >= required_type"""
        if not user or not user.is_authenticated:
            return False
        
        user_type = getattr(user, 'user_type', UserTypes.CUSTOMER)
        return UserTypes.has_higher_permission(user_type, required_type)
    
    def is_owner_or_admin(self, user, obj):
        """Vérifier si l'utilisateur est propriétaire ou admin"""
        if not user or not user.is_authenticated:
            return False
        
        # Admins ont tous les droits
        if self.has_higher_or_equal_permission(user, UserTypes.ADMIN):
            return True
        
        # Vérifier propriété
        if hasattr(obj, 'user') and obj.user == user:
            return True
        
        if hasattr(obj, 'customer') and obj.customer == user:
            return True
        
        if hasattr(obj, 'created_by') and obj.created_by == user:
            return True
        
        return False
    
    def belongs_to_same_organization(self, user, obj):
        """Vérifier si l'utilisateur appartient à la même organisation"""
        if not user or not user.is_authenticated:
            return False
        
        # Super admins peuvent tout voir
        if user.user_type == UserTypes.SUPER_ADMIN:
            return True
        
        user_orgs = getattr(user, 'organizations', None)
        if not user_orgs:
            return False
        
        user_org_ids = user_orgs.values_list('id', flat=True)
        
        # Vérifier selon le type d'objet
        if hasattr(obj, 'organization'):
            return obj.organization.id in user_org_ids
        
        if hasattr(obj, 'service') and hasattr(obj.service, 'organization'):
            return obj.service.organization.id in user_org_ids
        
        if hasattr(obj, 'queue') and hasattr(obj.queue, 'organization'):
            return obj.queue.organization.id in user_org_ids
        
        return False


class IsAuthenticatedCustomer(BaseSmartQueuePermission):
    """Permission pour clients authentifiés seulement"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and
            self.has_user_type(request.user, UserTypes.CUSTOMER)
        )


class IsStaffOrAbove(BaseSmartQueuePermission):
    """Permission pour personnel et au-dessus"""
    
    def has_permission(self, request, view):
        return self.has_higher_or_equal_permission(request.user, UserTypes.STAFF)


class IsAdminOrAbove(BaseSmartQueuePermission):
    """Permission pour admins et au-dessus"""
    
    def has_permission(self, request, view):
        return self.has_higher_or_equal_permission(request.user, UserTypes.ADMIN)


class IsSuperAdmin(BaseSmartQueuePermission):
    """Permission pour super admins uniquement"""
    
    def has_permission(self, request, view):
        return self.has_user_type(request.user, UserTypes.SUPER_ADMIN)


class IsOwnerOrReadOnly(BaseSmartQueuePermission):
    """Propriétaire peut modifier, autres peuvent lire"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Lecture pour tous les authentifiés
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Écriture pour propriétaires et admins
        return self.is_owner_or_admin(request.user, obj)


class IsOwnerOrStaffOrReadOnly(BaseSmartQueuePermission):
    """Propriétaire et staff peuvent modifier, autres peuvent lire"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Lecture pour tous les authentifiés
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Écriture pour propriétaires, staff et admins
        return (
            self.is_owner_or_admin(request.user, obj) or
            self.has_higher_or_equal_permission(request.user, UserTypes.STAFF)
        )


class OrganizationMemberPermission(BaseSmartQueuePermission):
    """Permission pour membres d'une organisation"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Super admins peuvent tout
        if request.user.user_type == UserTypes.SUPER_ADMIN:
            return True
        
        # Vérifier appartenance à l'organisation
        return self.belongs_to_same_organization(request.user, obj)


class OrganizationAdminPermission(BaseSmartQueuePermission):
    """Permission pour admins d'une organisation"""
    
    def has_permission(self, request, view):
        return self.has_higher_or_equal_permission(request.user, UserTypes.ADMIN)
    
    def has_object_permission(self, request, view, obj):
        # Super admins peuvent tout
        if request.user.user_type == UserTypes.SUPER_ADMIN:
            return True
        
        # Admins de l'organisation
        if request.user.user_type == UserTypes.ADMIN:
            return self.belongs_to_same_organization(request.user, obj)
        
        return False


class QueuePermission(BaseSmartQueuePermission):
    """Permissions spécifiques aux files d'attente"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Super admins: tout
        if user.user_type == UserTypes.SUPER_ADMIN:
            return True
        
        # Admins de l'organisation: tout
        if user.user_type == UserTypes.ADMIN:
            return self.belongs_to_same_organization(user, obj)
        
        # Staff de l'organisation: lecture + gestion file
        if user.user_type == UserTypes.STAFF:
            if self.belongs_to_same_organization(user, obj):
                # Staff peut gérer les files (pause, resume, etc.)
                allowed_methods = ['GET', 'PUT', 'PATCH']
                return request.method in allowed_methods
        
        # Clients: lecture seulement
        if user.user_type == UserTypes.CUSTOMER:
            return request.method in permissions.SAFE_METHODS
        
        return False


class TicketPermission(BaseSmartQueuePermission):
    """Permissions spécifiques aux tickets"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Super admins: tout
        if user.user_type == UserTypes.SUPER_ADMIN:
            return True
        
        # Propriétaire du ticket
        if hasattr(obj, 'customer') and obj.customer == user:
            # Client peut voir et annuler son ticket
            allowed_methods = ['GET', 'DELETE', 'PATCH']  # PATCH pour annuler
            return request.method in allowed_methods
        
        # Staff et admins de l'organisation
        if user.user_type in [UserTypes.STAFF, UserTypes.ADMIN]:
            return self.belongs_to_same_organization(user, obj)
        
        return False


class AppointmentPermission(BaseSmartQueuePermission):
    """Permissions spécifiques aux rendez-vous"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Super admins: tout
        if user.user_type == UserTypes.SUPER_ADMIN:
            return True
        
        # Propriétaire du RDV
        if hasattr(obj, 'customer') and obj.customer == user:
            # Client peut voir, modifier et annuler ses RDV
            allowed_methods = ['GET', 'PUT', 'PATCH', 'DELETE']
            return request.method in allowed_methods
        
        # Staff et admins de l'organisation
        if user.user_type in [UserTypes.STAFF, UserTypes.ADMIN]:
            return self.belongs_to_same_organization(user, obj)
        
        return False


class PaymentPermission(BaseSmartQueuePermission):
    """Permissions spécifiques aux paiements"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Super admins: tout
        if user.user_type == UserTypes.SUPER_ADMIN:
            return True
        
        # Propriétaire du paiement
        if hasattr(obj, 'user') and obj.user == user:
            # Client peut voir ses paiements uniquement
            return request.method in permissions.SAFE_METHODS
        
        # Admins de l'organisation concernée
        if user.user_type == UserTypes.ADMIN:
            return self.belongs_to_same_organization(user, obj)
        
        return False


class AnalyticsPermission(BaseSmartQueuePermission):
    """Permissions pour les analytics"""
    
    def has_permission(self, request, view):
        # Minimum staff pour voir les analytics
        return self.has_higher_or_equal_permission(request.user, UserTypes.STAFF)
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Super admins: toutes les analytics
        if user.user_type == UserTypes.SUPER_ADMIN:
            return True
        
        # Admins: analytics de leur organisation
        if user.user_type == UserTypes.ADMIN:
            return self.belongs_to_same_organization(user, obj)
        
        # Staff: analytics limitées de leur organisation
        if user.user_type == UserTypes.STAFF:
            if self.belongs_to_same_organization(user, obj):
                # Staff peut voir mais pas modifier les analytics
                return request.method in permissions.SAFE_METHODS
        
        return False


class NotificationPermission(BaseSmartQueuePermission):
    """Permissions pour les notifications"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Super admins: tout
        if user.user_type == UserTypes.SUPER_ADMIN:
            return True
        
        # Utilisateur destinataire
        if hasattr(obj, 'recipient') and obj.recipient == user:
            # Peut voir et marquer comme lu
            allowed_methods = ['GET', 'PATCH']
            return request.method in allowed_methods
        
        # Admins peuvent gérer les notifications de leur organisation
        if user.user_type == UserTypes.ADMIN:
            return self.belongs_to_same_organization(user, obj)
        
        return False


class ConfigurationPermission(BaseSmartQueuePermission):
    """Permissions pour la configuration système"""
    
    def has_permission(self, request, view):
        # Seuls les super admins peuvent modifier la config
        if request.method in permissions.SAFE_METHODS:
            return self.has_higher_or_equal_permission(request.user, UserTypes.ADMIN)
        else:
            return self.has_user_type(request.user, UserTypes.SUPER_ADMIN)


# =============================================================================
# PERMISSIONS COMPOSÉES (DÉCORATEURS)
# =============================================================================

class ReadOnlyForCustomers(BaseSmartQueuePermission):
    """Les clients peuvent lire, les autres selon leurs droits normaux"""
    
    def __init__(self, base_permission_class):
        self.base_permission = base_permission_class()
    
    def has_permission(self, request, view):
        user = request.user
        
        if not user or not user.is_authenticated:
            return False
        
        # Clients: lecture seulement
        if user.user_type == UserTypes.CUSTOMER:
            return request.method in permissions.SAFE_METHODS
        
        # Autres: permissions de base
        return self.base_permission.has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        
        # Clients: lecture seulement
        if user.user_type == UserTypes.CUSTOMER:
            return request.method in permissions.SAFE_METHODS
        
        # Autres: permissions de base
        return self.base_permission.has_object_permission(request, view, obj)


# =============================================================================
# MIXINS POUR VUES
# =============================================================================

class OrganizationFilterMixin:
    """
    Mixin pour filtrer automatiquement par organisation
    À utiliser dans les ViewSets
    """
    
    def get_queryset(self):
        """Filtrer selon l'organisation de l'utilisateur"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return queryset.none()
        
        # Super admins voient tout
        if user.user_type == UserTypes.SUPER_ADMIN:
            return queryset
        
        # Autres: filtrer par organisation
        user_orgs = getattr(user, 'organizations', None)
        if not user_orgs:
            return queryset.none()
        
        user_org_ids = user_orgs.values_list('id', flat=True)
        
        # Filtrage selon le modèle
        if hasattr(queryset.model, 'organization'):
            return queryset.filter(organization__id__in=user_org_ids)
        
        elif hasattr(queryset.model, 'service'):
            return queryset.filter(service__organization__id__in=user_org_ids)
        
        elif hasattr(queryset.model, 'queue'):
            return queryset.filter(queue__organization__id__in=user_org_ids)
        
        return queryset


class UserFilterMixin:
    """
    Mixin pour filtrer par utilisateur (ses propres données)
    """
    
    def get_queryset(self):
        """Filtrer les données de l'utilisateur connecté"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user or not user.is_authenticated:
            return queryset.none()
        
        # Admins et au-dessus voient selon leur organisation
        if user.user_type in [UserTypes.ADMIN, UserTypes.SUPER_ADMIN]:
            return queryset  # Sera filtré par OrganizationFilterMixin
        
        # Clients voient leurs données uniquement
        if user.user_type == UserTypes.CUSTOMER:
            if hasattr(queryset.model, 'customer'):
                return queryset.filter(customer=user)
            elif hasattr(queryset.model, 'user'):
                return queryset.filter(user=user)
        
        return queryset


# =============================================================================
# HELPERS POUR VUES FONCTION
# =============================================================================

def require_user_type(allowed_types):
    """Décorateur pour vues fonction - exiger un type d'utilisateur"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user or not request.user.is_authenticated:
                from django.http import JsonResponse
                return JsonResponse({'error': 'Authentification requise'}, status=401)
            
            user_type = getattr(request.user, 'user_type', UserTypes.CUSTOMER)
            if user_type not in allowed_types:
                from django.http import JsonResponse
                return JsonResponse({'error': 'Permission insuffisante'}, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_same_organization(view_func):
    """Décorateur pour vérifier l'appartenance à la même organisation"""
    def wrapper(request, *args, **kwargs):
        # À implémenter selon le contexte spécifique
        return view_func(request, *args, **kwargs)
    return wrapper