# apps/core/views.py
"""
Vues utilitaires SmartQueue Core
Health check, configuration, validation, logs
"""

from django.conf import settings
from django.db import connections
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import PhoneValidationSerializer


def home_view(request):
    """
    Page d'accueil du backend SmartQueue
    Présentation visuelle des fonctionnalités
    """
    context = {
        'apps_count': 11,
        'regions_count': 3,
        'communes_count': 17,
        'status': 'operational'
    }
    return render(request, 'core/home.html', context)
from .models import Configuration, ActivityLog
from .serializers import (
    ConfigurationSerializer, 
    ActivityLogSerializer,
    SystemStatusSerializer
)
from .permissions import IsSuperAdmin, IsAdminOrAbove
from .constants import SenegalRegions
from .utils import SenegalValidators
import logging

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Health check simple pour monitoring
    Accessible sans authentification
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """Vérifier l'état du système"""
        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'version': getattr(settings, 'API_VERSION', 'v1'),
            'checks': {}
        }
        
        # Vérifier base de données
        try:
            db_conn = connections['default']
            db_conn.cursor()
            health_status['checks']['database'] = 'ok'
        except Exception as e:
            health_status['checks']['database'] = 'error'
            health_status['status'] = 'degraded'
            logger.error(f"Health check DB error: {e}")
        
        # Vérifier cache
        try:
            cache.set('health_check', 'ok', 10)
            cache_result = cache.get('health_check')
            health_status['checks']['cache'] = 'ok' if cache_result == 'ok' else 'error'
        except Exception as e:
            health_status['checks']['cache'] = 'error'
            health_status['status'] = 'degraded'
            logger.error(f"Health check cache error: {e}")
        
        # Vérifier mode maintenance
        try:
            config = Configuration.get_current()
            if config.maintenance_mode:
                health_status['checks']['maintenance'] = 'active'
                health_status['status'] = 'maintenance'
            else:
                health_status['checks']['maintenance'] = 'inactive'
        except Exception:
            health_status['checks']['maintenance'] = 'unknown'
        
        # Status code selon l'état
        status_code = status.HTTP_200_OK
        if health_status['status'] == 'degraded':
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif health_status['status'] == 'maintenance':
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return Response(health_status, status=status_code)


class SystemStatusView(APIView):
    """
    Status détaillé du système (admin seulement)
    """
    permission_classes = [IsAdminOrAbove]
    
    def get(self, request):
        """Status complet du système"""
        import psutil
        import os
        
        try:
            system_status = {
                'timestamp': timezone.now().isoformat(),
                'system': {
                    'cpu_percent': psutil.cpu_percent(),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent,
                },
                'database': {},
                'cache': {},
                'queues': {},
                'users': {},
            }
            
            # Stats base de données
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM accounts_user")
                    total_users = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM tickets_ticket WHERE created_at >= NOW() - INTERVAL '24 hours'")
                    tickets_today = cursor.fetchone()[0]
                    
                system_status['database'] = {
                    'status': 'connected',
                    'total_users': total_users,
                    'tickets_today': tickets_today,
                }
            except Exception as e:
                system_status['database'] = {'status': 'error', 'error': str(e)}
            
            # Stats utilisateurs actifs
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                active_users_count = User.objects.filter(is_active=True).count()
                recent_logins = User.objects.filter(
                    last_login__gte=timezone.now() - timezone.timedelta(hours=24)
                ).count()
                
                system_status['users'] = {
                    'total_active': active_users_count,
                    'recent_logins_24h': recent_logins,
                }
            except Exception as e:
                system_status['users'] = {'error': str(e)}
            
            return Response(system_status)
            
        except Exception as e:
            logger.error(f"System status error: {e}")
            return Response(
                {'error': 'Erreur récupération status système'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PublicConfigView(APIView):
    """
    Configuration publique (sans données sensibles)
    Accessible à tous les utilisateurs authentifiés
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Configuration publique"""
        try:
            config = Configuration.get_current()
            
            public_config = {
                'site_name': config.site_name,
                'site_description': config.site_description,
                'support_email': config.support_email,
                'support_phone': config.support_phone,
                'default_ticket_expiry_minutes': config.default_ticket_expiry_minutes,
                'default_appointment_duration_minutes': config.default_appointment_duration_minutes,
                'max_tickets_per_user_per_day': config.max_tickets_per_user_per_day,
                'max_appointments_per_user_per_day': config.max_appointments_per_user_per_day,
                'sms_enabled': config.sms_enabled,
                'push_enabled': config.push_enabled,
                'email_enabled': config.email_enabled,
                'maintenance_mode': config.maintenance_mode,
                'maintenance_message': config.maintenance_message if config.maintenance_mode else None,
            }
            
            return Response(public_config)
            
        except Exception as e:
            logger.error(f"Public config error: {e}")
            return Response(
                {'error': 'Erreur récupération configuration'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ValidatePhoneView(APIView):
    """
    Utilitaire pour valider numéros de téléphone sénégalais
    Accessible à tous les utilisateurs authentifiés
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Valider un numéro de téléphone"""
        serializer = PhoneValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        phone = serializer.validated_data['phone']
        
        if not phone:
            return Response(
                {'error': 'Numéro de téléphone requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Normaliser
        normalized = SenegalValidators.normalize_phone_number(phone)
        
        # Valider
        is_valid = SenegalValidators.validate_phone_number(normalized) if normalized else False
        
        result = {
            'original': phone,
            'normalized': normalized,
            'is_valid': is_valid,
            'format_required': '+221XXXXXXXXX'
        }
        
        return Response(result)


class SenegalRegionsView(APIView):
    """
    Liste des régions du Sénégal
    Accessible à tous les utilisateurs authentifiés
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Régions administratives du Sénégal"""
        regions = [
            {'code': code, 'name': name}
            for code, name in SenegalRegions.CHOICES
        ]
        
        return Response({
            'regions': regions,
            'count': len(regions)
        })


class ActivityLogListView(generics.ListAPIView):
    """
    Liste des logs d'activité (admin seulement)
    """
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminOrAbove]
    filterset_fields = ['user', 'action_type', 'model_name']
    search_fields = ['description', 'user__email', 'ip_address']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrer selon l'utilisateur"""
        queryset = super().get_queryset()
        
        # Super admins voient tout
        if self.request.user.user_type == 'super_admin':
            return queryset
        
        # Admins voient les logs de leur organisation
        # TODO: filtrer par organisation quand la relation existe
        return queryset


class ActivityLogDetailView(generics.RetrieveAPIView):
    """
    Détail d'un log d'activité
    """
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAdminOrAbove]


class MaintenanceView(APIView):
    """
    Gestion du mode maintenance (super admin seulement)
    """
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        """Status maintenance actuel"""
        config = Configuration.get_current()
        return Response({
            'maintenance_mode': config.maintenance_mode,
            'maintenance_message': config.maintenance_message,
        })
    
    def post(self, request):
        """Activer/désactiver maintenance"""
        config = Configuration.get_current()
        
        maintenance_mode = request.data.get('maintenance_mode')
        maintenance_message = request.data.get('maintenance_message', '')
        
        if maintenance_mode is not None:
            config.maintenance_mode = maintenance_mode
            config.maintenance_message = maintenance_message
            config.save()
            
            # Logger l'action
            ActivityLog.log_activity(
                user=request.user,
                action_type='update',
                description=f"Mode maintenance {'activé' if maintenance_mode else 'désactivé'}",
                model_name='Configuration',
                object_id=config.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                maintenance_mode=maintenance_mode
            )
            
            return Response({
                'message': f"Mode maintenance {'activé' if maintenance_mode else 'désactivé'}",
                'maintenance_mode': config.maintenance_mode,
                'maintenance_message': config.maintenance_message,
            })
        
        return Response(
            {'error': 'maintenance_mode requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
