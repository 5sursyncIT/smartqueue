# apps/core/middleware.py
"""
Middlewares personnalisés SmartQueue
Sécurité, logs, monitoring et contrôles
"""

import logging
import time
import json
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.conf import settings
from .models import ActivityLog, Configuration

User = get_user_model()
logger = logging.getLogger(__name__)


class SecurityMiddleware(MiddlewareMixin):
    """
    Middleware de sécurité pour SmartQueue
    - Headers de sécurité
    - Rate limiting basique  
    - IP blocking
    - User-Agent validation
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # IPs bloquées (peut être stocké en cache/DB)
        self.blocked_ips = getattr(settings, 'BLOCKED_IPS', [])
        super().__init__(get_response)
    
    def process_request(self, request):
        """Vérifications de sécurité avant traitement"""
        
        # Obtenir l'IP réelle
        ip = self.get_client_ip(request)
        request.client_ip = ip
        
        # Vérifier IP bloquée
        if ip in self.blocked_ips:
            logger.warning(f"Blocked IP attempt: {ip}")
            return JsonResponse({
                'error': 'Accès refusé',
                'code': 'ACCESS_DENIED'
            }, status=403)
        
        # Rate limiting par IP (100 requêtes par minute max)
        rate_limit_key = f"rate_limit:{ip}"
        current_requests = cache.get(rate_limit_key, 0)
        
        if current_requests >= 100:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return JsonResponse({
                'error': 'Trop de requêtes. Veuillez patienter.',
                'code': 'RATE_LIMIT_EXCEEDED'
            }, status=429)
        
        # Incrémenter compteur
        cache.set(rate_limit_key, current_requests + 1, 60)  # 1 minute
        
        return None
    
    def process_response(self, request, response):
        """Ajouter headers de sécurité"""
        
        # Headers de sécurité basiques
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Pour APIs - pas de cache sensible
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
    
    def get_client_ip(self, request):
        """Obtenir l'IP réelle du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ActivityLogMiddleware(MiddlewareMixin):
    """
    Middleware pour logger automatiquement les activités
    Enregistre les actions importantes dans ActivityLog
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Marquer le début de la requête"""
        request.start_time = time.time()
        return None
    
    def process_response(self, request, response):
        """Logger l'activité après traitement"""
        
        # Ne pas logger certaines routes (media, static, admin...)
        if self._should_skip_logging(request):
            return response
        
        # Calculer le temps de traitement
        duration = None
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
        
        # Déterminer le type d'action
        action_type = self._get_action_type(request, response)
        
        # Logger seulement les actions importantes
        if action_type:
            try:
                # Préparer les métadonnées
                metadata = {
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'duration_ms': round(duration * 1000, 2) if duration else None,
                }
                
                # Ajouter query params si GET
                if request.method == 'GET' and request.GET:
                    metadata['query_params'] = dict(request.GET)
                
                # Description de l'action
                description = f"{request.method} {request.path}"
                if response.status_code >= 400:
                    description += f" (Erreur {response.status_code})"
                
                # Logger en base
                ActivityLog.log_activity(
                    user=request.user if request.user.is_authenticated else None,
                    action_type=action_type,
                    description=description,
                    ip_address=getattr(request, 'client_ip', None),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    **metadata
                )
                
            except Exception as e:
                # Ne jamais faire planter l'app pour un problème de log
                logger.error(f"Erreur logging activité: {e}")
        
        return response
    
    def _should_skip_logging(self, request):
        """Déterminer si on doit ignorer cette route"""
        skip_paths = [
            '/static/',
            '/media/',
            '/admin/jsi18n/',
            '/favicon.ico',
            '/__debug__/',
        ]
        
        for skip_path in skip_paths:
            if request.path.startswith(skip_path):
                return True
        
        return False
    
    def _get_action_type(self, request, response):
        """Déterminer le type d'action à logger"""
        
        # Erreurs serveur
        if response.status_code >= 500:
            return 'error'
        
        # APIs importantes seulement
        if not request.path.startswith('/api/'):
            return None
        
        # Mapping par méthode HTTP
        method_mapping = {
            'POST': 'create',
            'PUT': 'update', 
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        
        # Actions spéciales par path
        if 'login' in request.path:
            return 'login'
        elif 'logout' in request.path:
            return 'logout'
        elif 'payment' in request.path:
            return 'payment'
        elif request.method == 'GET' and response.status_code == 200:
            return 'view'
        
        return method_mapping.get(request.method)


class MaintenanceMiddleware(MiddlewareMixin):
    """
    Middleware pour le mode maintenance
    Bloque l'accès quand le système est en maintenance
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request):
        """Vérifier si maintenance activée"""
        
        # Chemins toujours accessibles
        allowed_paths = [
            '/admin/',
            '/api/v1/health/',
            '/static/',
            '/media/',
        ]
        
        for path in allowed_paths:
            if request.path.startswith(path):
                return None
        
        # Vérifier configuration maintenance
        try:
            config = Configuration.get_current()
            if config.maintenance_mode:
                
                # Super admins passent toujours
                if (request.user.is_authenticated and 
                    hasattr(request.user, 'user_type') and 
                    request.user.user_type == 'super_admin'):
                    return None
                
                # Message de maintenance
                message = config.maintenance_message or (
                    "SmartQueue est temporairement en maintenance. "
                    "Nous serons de retour très bientôt !"
                )
                
                # Réponse JSON pour APIs, HTML pour le reste
                if request.path.startswith('/api/'):
                    return JsonResponse({
                        'error': 'Maintenance en cours',
                        'message': message,
                        'code': 'MAINTENANCE_MODE'
                    }, status=503)
                else:
                    # Page HTML simple pour le frontend
                    html = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>SmartQueue - Maintenance</title>
                        <meta charset="utf-8">
                        <style>
                            body {{ font-family: Arial, sans-serif; text-align: center; 
                                   margin-top: 100px; background-color: #f5f5f5; }}
                            .container {{ max-width: 500px; margin: 0 auto; 
                                        background: white; padding: 40px; border-radius: 10px; 
                                        box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                            h1 {{ color: #e74c3c; }}
                            p {{ color: #666; line-height: 1.6; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>🔧 Maintenance en cours</h1>
                            <p>{message}</p>
                            <p><small>Équipe SmartQueue Sénégal</small></p>
                        </div>
                    </body>
                    </html>
                    """
                    from django.http import HttpResponse
                    return HttpResponse(html, status=503)
                
        except Exception as e:
            # En cas d'erreur, ne pas bloquer l'app
            logger.error(f"Erreur middleware maintenance: {e}")
        
        return None


class APIVersionMiddleware(MiddlewareMixin):
    """
    Middleware pour gérer les versions d'API
    Ajoute des headers et valide les versions
    """
    
    def process_request(self, request):
        """Traiter la version API demandée"""
        
        if request.path.startswith('/api/'):
            
            # Version par défaut
            api_version = 'v1'
            
            # Lire version dans l'URL ou header
            if '/v1/' in request.path:
                api_version = 'v1'
            elif '/v2/' in request.path:
                api_version = 'v2'
            else:
                # Fallback sur header
                api_version = request.META.get('HTTP_API_VERSION', 'v1')
            
            # Stocker pour usage dans les vues
            request.api_version = api_version
            
            # Versions supportées
            supported_versions = ['v1']
            
            if api_version not in supported_versions:
                return JsonResponse({
                    'error': f'Version API {api_version} non supportée',
                    'supported_versions': supported_versions,
                    'code': 'UNSUPPORTED_API_VERSION'
                }, status=400)
        
        return None
    
    def process_response(self, request, response):
        """Ajouter headers de version"""
        
        if request.path.startswith('/api/'):
            response['API-Version'] = getattr(request, 'api_version', 'v1')
            response['API-Supported-Versions'] = 'v1'
        
        return response


class CORSMiddleware(MiddlewareMixin):
    """
    Middleware CORS personnalisé pour SmartQueue
    Gère les requêtes cross-origin de façon sécurisée
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Domaines autorisés (à configurer selon l'environnement)
        self.allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [
            'http://localhost:3000',  # Frontend dev
            'https://smartqueue.sn',  # Frontend prod
            'https://app.smartqueue.sn',  # App mobile
        ])
        super().__init__(get_response)
    
    def process_request(self, request):
        """Gérer les requêtes OPTIONS (preflight)"""
        
        if request.method == 'OPTIONS':
            origin = request.META.get('HTTP_ORIGIN')
            
            if origin in self.allowed_origins:
                response = JsonResponse({'status': 'OK'})
                self._add_cors_headers(response, origin)
                return response
        
        return None
    
    def process_response(self, request, response):
        """Ajouter headers CORS à toutes les réponses API"""
        
        if request.path.startswith('/api/'):
            origin = request.META.get('HTTP_ORIGIN')
            
            if origin in self.allowed_origins:
                self._add_cors_headers(response, origin)
        
        return response
    
    def _add_cors_headers(self, response, origin):
        """Ajouter les headers CORS nécessaires"""
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = (
            'Accept, Content-Type, Content-Length, Accept-Encoding, '
            'X-CSRF-Token, Authorization, API-Version'
        )
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Max-Age'] = '86400'  # 24h cache preflight