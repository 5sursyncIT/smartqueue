# apps/notifications/sms_service.py
"""
Service SMS amélioré avec providers réels sénégalais
Intégration Orange, SMS.to, eSMS Africa

⚠️  SMS FONCTIONNALITÉ COMMENTÉE (Décision superviseur)
    - Priorité: PUSH + EMAIL uniquement
    - SMS sera réactivé plus tard si besoin
    - Code conservé pour future utilisation
"""

# ============================================
# SMS FONCTIONNALITÉ DÉSACTIVÉE TEMPORAIREMENT
# ============================================

import logging
import requests
import json
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.cache import cache
from datetime import datetime, timedelta
from .models import SMSProvider, NotificationLog, Notification

logger = logging.getLogger(__name__)


class SMSService:
    """
    Service SMS avec support multi-providers sénégalais
    """

    def __init__(self):
        self.config = getattr(settings, 'SMS_CONFIG', {})
        self.enabled = self.config.get('ENABLED', False)
        self.default_provider = self.config.get('DEFAULT_PROVIDER', 'orange')

    def send_sms(self, phone_number: str, message: str, provider_name: str = None) -> Dict[str, Any]:
        """
        Envoyer SMS avec provider spécifié ou par défaut

        Args:
            phone_number: Numéro au format +221XXXXXXXXX
            message: Message à envoyer
            provider_name: Provider spécifique (orange, sms_to, esms_africa)

        Returns:
            Dict avec résultat de l'envoi
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Service SMS désactivé',
                'provider': None,
                'cost': 0
            }

        # Validation du numéro
        if not self._validate_senegal_phone(phone_number):
            return {
                'success': False,
                'error': f'Numéro invalide: {phone_number}',
                'provider': None,
                'cost': 0
            }

        # Choisir provider
        provider_name = provider_name or self.default_provider
        provider_config = self.config.get('PROVIDERS', {}).get(provider_name)

        if not provider_config:
            return {
                'success': False,
                'error': f'Provider {provider_name} non configuré',
                'provider': provider_name,
                'cost': 0
            }

        # Vérifier rate limiting
        if self._is_rate_limited(provider_name):
            return {
                'success': False,
                'error': f'Rate limit atteint pour {provider_name}',
                'provider': provider_name,
                'cost': 0
            }

        # Envoyer selon le provider
        try:
            if provider_name == 'orange':
                result = self._send_via_orange(phone_number, message, provider_config)
            elif provider_name == 'free':
                result = self._send_via_free(phone_number, message, provider_config)
            elif provider_name == 'expresso':
                result = self._send_via_expresso(phone_number, message, provider_config)
            else:
                result = {
                    'success': False,
                    'error': f'Provider {provider_name} non supporté',
                    'provider': provider_name,
                    'cost': 0
                }

            # Incrémenter compteur rate limiting si succès
            if result.get('success'):
                self._increment_rate_limit(provider_name)

            return result

        except Exception as e:
            logger.error(f"Erreur envoi SMS {provider_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'provider': provider_name,
                'cost': 0
            }

    def _send_via_orange(self, phone_number: str, message: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Envoyer SMS via Orange Sénégal API"""

        # 1. Obtenir token OAuth 2.0
        token = self._get_orange_token(config)
        if not token:
            return {
                'success': False,
                'error': 'Impossible d\'obtenir le token Orange',
                'provider': 'orange',
                'cost': 0
            }

        # 2. Préparer la requête SMS
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

        # Format spécifique Orange API
        data = {
            "outboundSMSMessageRequest": {
                "address": f"tel:{phone_number}",
                "senderAddress": f"tel:{config['SENDER_NAME']}",
                "outboundSMSTextMessage": {
                    "message": message
                }
            }
        }

        # 3. Envoyer SMS
        try:
            response = requests.post(
                config['API_URL'],
                headers=headers,
                json=data,
                timeout=30
            )

            response_data = response.json() if response.content else {}

            if response.status_code == 201:  # Orange utilise 201 pour succès
                return {
                    'success': True,
                    'provider': 'orange',
                    'cost': config.get('COST_PER_SMS', 20.0),
                    'message_id': response_data.get('outboundSMSMessageRequest', {}).get('resourceURL', ''),
                    'details': response_data
                }
            else:
                return {
                    'success': False,
                    'error': f'Orange API error: {response.status_code}',
                    'provider': 'orange',
                    'cost': 0,
                    'details': response_data
                }

        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Orange API request failed: {str(e)}',
                'provider': 'orange',
                'cost': 0
            }

    def _send_via_free(self, phone_number: str, message: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envoyer SMS via Free Sénégal

        PLACEHOLDER - En attente de la documentation API Free Sénégal
        Une fois reçue, cette méthode sera implémentée selon leurs spécifications
        """
        return {
            'success': False,
            'provider': 'free',
            'cost': 0,
            'error': 'Service Free SMS - En attente des spécifications API officielle'
        }

    def _send_via_expresso(self, phone_number: str, message: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Envoyer SMS via Expresso Sénégal

        PLACEHOLDER - En attente de la documentation API Expresso Sénégal
        Une fois reçue, cette méthode sera implémentée selon leurs spécifications
        """
        return {
            'success': False,
            'provider': 'expresso',
            'cost': 0,
            'error': 'Service Expresso SMS - En attente des spécifications API officielle'
        }

    def _get_orange_token(self, config: Dict[str, Any]) -> Optional[str]:
        """
        Obtenir token OAuth 2.0 pour Orange API
        """
        # Vérifier cache
        cache_key = 'orange_sms_token'
        token = cache.get(cache_key)
        if token:
            return token

        # Authentification OAuth 2.0
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': config['CLIENT_ID'],
            'client_secret': config['CLIENT_SECRET'],
            'scope': 'sms'
        }

        try:
            response = requests.post(
                config['AUTH_URL'],
                data=auth_data,
                timeout=30
            )

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)

                # Mettre en cache avec expiration
                cache.set(cache_key, access_token, expires_in - 300)  # -5min sécurité
                return access_token

        except requests.RequestException as e:
            logger.error(f"Erreur authentification Orange: {e}")

        return None

    def _validate_senegal_phone(self, phone: str) -> bool:
        """Valider numéro de téléphone sénégalais"""
        import re
        pattern = r'^\+221[0-9]{9}$'
        return bool(re.match(pattern, phone))

    def _is_rate_limited(self, provider_name: str) -> bool:
        """Vérifier rate limiting"""
        cache_key = f'sms_rate_limit:{provider_name}'
        count = cache.get(cache_key, 0)

        provider_config = self.config.get('PROVIDERS', {}).get(provider_name, {})
        limit = provider_config.get('RATE_LIMIT_PER_MINUTE', 60)

        return count >= limit

    def _increment_rate_limit(self, provider_name: str):
        """Incrémenter compteur rate limiting"""
        cache_key = f'sms_rate_limit:{provider_name}'
        count = cache.get(cache_key, 0)
        cache.set(cache_key, count + 1, 60)  # 1 minute

    def send_otp(self, phone_number: str, code: str) -> Dict[str, Any]:
        """
        Envoyer code OTP via SMS

        Args:
            phone_number: Numéro de téléphone
            code: Code OTP à envoyer

        Returns:
            Résultat d'envoi
        """
        message = f"Votre code SmartQueue: {code}. Valable 10 minutes. Ne le partagez jamais."

        return self.send_sms(phone_number, message)

    def send_ticket_notification(self, phone_number: str, ticket_number: str,
                                window_number: str = None) -> Dict[str, Any]:
        """
        Envoyer notification de ticket appelé
        """
        if window_number:
            message = f"SmartQueue: Votre ticket #{ticket_number} est appelé. Présentez-vous au guichet {window_number}."
        else:
            message = f"SmartQueue: Votre ticket #{ticket_number} est appelé. Présentez-vous à l'accueil."

        return self.send_sms(phone_number, message)

    def send_appointment_confirmation(self, phone_number: str, appointment_ref: str,
                                    date: str, time: str, organization: str) -> Dict[str, Any]:
        """
        Envoyer confirmation de RDV
        """
        message = f"SmartQueue: RDV confirmé le {date} à {time} chez {organization}. Réf: {appointment_ref}"

        return self.send_sms(phone_number, message)

    def get_provider_status(self) -> Dict[str, Any]:
        """
        Obtenir statut de tous les providers SMS
        """
        status = {
            'enabled': self.enabled,
            'default_provider': self.default_provider,
            'providers': {}
        }

        for name, config in self.config.get('PROVIDERS', {}).items():
            # Vérifier si les clés sont configurées
            api_key = config.get('API_KEY', '') or config.get('CLIENT_ID', '')
            configured = bool(api_key)

            # Vérifier rate limiting
            cache_key = f'sms_rate_limit:{name}'
            current_usage = cache.get(cache_key, 0)
            rate_limit = config.get('RATE_LIMIT_PER_MINUTE', 60)

            status['providers'][name] = {
                'name': config.get('NAME', name),
                'configured': configured,
                'priority': config.get('PRIORITY', 999),
                'cost_per_sms': config.get('COST_PER_SMS', 0),
                'rate_limit': rate_limit,
                'current_usage': current_usage,
                'available': configured and current_usage < rate_limit
            }

        return status


# Instance globale
sms_service = SMSService()