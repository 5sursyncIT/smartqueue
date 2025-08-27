# apps/core/utils.py
"""
Utilitaires et générateurs SmartQueue
Fonctions helper réutilisables dans tout le projet
"""

import hashlib
import hmac
import secrets
import string
import uuid
import random
import re
import base64
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from typing import Optional, Dict, Any, List
import qrcode
import io
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# GÉNÉRATEURS DE TOKENS ET CODES
# =============================================================================

class TokenGenerator:
    """Générateur de tokens sécurisés pour SmartQueue"""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Générer un token sécurisé aléatoire"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_numeric_code(length: int = 6) -> str:
        """Générer un code numérique (pour SMS)"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    def generate_ticket_number(prefix: str = 'SQ') -> str:
        """Générer un numéro de ticket unique"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"{prefix}{timestamp}{random_part}"
    
    @staticmethod
    def generate_appointment_ref() -> str:
        """Générer une référence de RDV"""
        return f"RDV{datetime.now().strftime('%Y%m%d')}{TokenGenerator.generate_numeric_code(6)}"
    
    @staticmethod
    def generate_payment_ref() -> str:
        """Générer une référence de paiement"""
        return f"PAY{datetime.now().strftime('%Y%m%d')}{TokenGenerator.generate_secure_token(8).upper()}"
    
    @staticmethod
    def generate_api_key(user_id: int) -> str:
        """Générer une clé API pour un utilisateur"""
        user_part = str(user_id).zfill(6)
        random_part = TokenGenerator.generate_secure_token(24)
        timestamp = str(int(timezone.now().timestamp()))
        
        # Concaténer et hasher
        raw_key = f"sq_{user_part}_{timestamp}_{random_part}"
        return raw_key
    
    @staticmethod
    def generate_webhook_signature(payload: str, secret: str) -> str:
        """Générer signature webhook pour validation"""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    @staticmethod
    def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
        """Vérifier signature webhook"""
        expected_signature = TokenGenerator.generate_webhook_signature(payload, secret)
        return hmac.compare_digest(signature, expected_signature)


class OTPManager:
    """Gestionnaire de codes OTP (One-Time Password)"""
    
    @staticmethod
    def generate_otp(phone_number: str, length: int = 6, validity_minutes: int = 10) -> str:
        """Générer et stocker un OTP"""
        code = TokenGenerator.generate_numeric_code(length)
        
        # Stocker en cache avec expiration
        cache_key = f"otp:{phone_number}"
        cache.set(cache_key, code, validity_minutes * 60)
        
        # Logger pour debug (sans exposer le code)
        logger.info(f"OTP généré pour {phone_number[:8]}***")
        
        return code
    
    @staticmethod
    def verify_otp(phone_number: str, code: str) -> bool:
        """Vérifier un code OTP"""
        cache_key = f"otp:{phone_number}"
        stored_code = cache.get(cache_key)
        
        if stored_code and stored_code == code:
            # Supprimer après usage
            cache.delete(cache_key)
            logger.info(f"OTP vérifié avec succès pour {phone_number[:8]}***")
            return True
        
        logger.warning(f"Échec vérification OTP pour {phone_number[:8]}***")
        return False
    
    @staticmethod
    def is_rate_limited(phone_number: str, max_attempts: int = 3, window_minutes: int = 5) -> bool:
        """Vérifier si le numéro est rate limité"""
        cache_key = f"otp_attempts:{phone_number}"
        attempts = cache.get(cache_key, 0)
        
        if attempts >= max_attempts:
            return True
        
        # Incrémenter tentatives
        cache.set(cache_key, attempts + 1, window_minutes * 60)
        return False


# =============================================================================
# GÉNÉRATEURS QR CODE
# =============================================================================

class QRCodeGenerator:
    """Générateur de QR codes pour tickets et RDV"""
    
    @staticmethod
    def generate_ticket_qr(ticket_data: Dict[str, Any]) -> bytes:
        """Générer QR code pour ticket"""
        qr_data = {
            'type': 'ticket',
            'id': ticket_data.get('id'),
            'number': ticket_data.get('number'),
            'service': ticket_data.get('service_name'),
            'organization': ticket_data.get('organization_name'),
            'timestamp': timezone.now().isoformat(),
        }
        
        # Convertir en string JSON compacte
        import json
        qr_string = json.dumps(qr_data, separators=(',', ':'))
        
        return QRCodeGenerator._generate_qr_image(qr_string)
    
    @staticmethod
    def generate_appointment_qr(appointment_data: Dict[str, Any]) -> bytes:
        """Générer QR code pour RDV"""
        qr_data = {
            'type': 'appointment',
            'ref': appointment_data.get('reference'),
            'date': appointment_data.get('date'),
            'time': appointment_data.get('time'),
            'service': appointment_data.get('service_name'),
            'organization': appointment_data.get('organization_name'),
        }
        
        import json
        qr_string = json.dumps(qr_data, separators=(',', ':'))
        
        return QRCodeGenerator._generate_qr_image(qr_string)
    
    @staticmethod
    def _generate_qr_image(data: str, size: int = 10) -> bytes:
        """Générer l'image QR code"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=size,
            border=4,
        )
        
        qr.add_data(data)
        qr.make(fit=True)
        
        # Créer image en mémoire
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convertir en bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer.read()


# =============================================================================
# VALIDATEURS
# =============================================================================

class SenegalValidators:
    """Validateurs spécifiques au Sénégal"""
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Valider numéro de téléphone sénégalais"""
        pattern = r'^\+221[0-9]{9}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def normalize_phone_number(phone: str) -> Optional[str]:
        """Normaliser un numéro de téléphone"""
        # Supprimer espaces et tirets
        phone = re.sub(r'[\s\-]', '', phone)
        
        # Formats acceptés:
        # +221XXXXXXXXX
        # 221XXXXXXXXX  
        # 0XXXXXXXXX (local)
        # XXXXXXXXX (sans indicatif)
        
        if phone.startswith('+221') and len(phone) == 13:
            return phone
        elif phone.startswith('221') and len(phone) == 12:
            return f"+{phone}"
        elif phone.startswith('0') and len(phone) == 10:
            return f"+221{phone[1:]}"
        elif len(phone) == 9:
            return f"+221{phone}"
        
        return None
    
    @staticmethod
    def validate_nin(nin: str) -> bool:
        """Valider Numéro d'Identification Nationale (Sénégal)"""
        # Format: 13 chiffres
        if not nin or len(nin) != 13:
            return False
        
        return nin.isdigit()


# =============================================================================
# FORMATTERS DE TEMPS ET DATES
# =============================================================================

class TimeFormatter:
    """Formatage des temps et dates pour SmartQueue"""
    
    @staticmethod
    def format_duration(minutes: int, language: str = 'fr') -> str:
        """Formater une durée en texte lisible"""
        if language == 'wo':  # Wolof
            if minutes < 60:
                return f"{minutes} simili" if minutes > 1 else f"{minutes} simili"
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours} waxtu" if hours > 1 else f"{hours} waxtu"
            return f"{hours}w {remaining_minutes}s"
        
        else:  # Français
            if minutes < 60:
                return f"{minutes} min"
            hours = minutes // 60
            remaining_minutes = minutes % 60
            if remaining_minutes == 0:
                return f"{hours}h"
            return f"{hours}h{remaining_minutes:02d}"
    
    @staticmethod
    def estimate_waiting_time(queue_position: int, avg_service_time: int) -> int:
        """Estimer temps d'attente en minutes"""
        return queue_position * avg_service_time
    
    @staticmethod
    def format_business_hours(start_time: str, end_time: str, language: str = 'fr') -> str:
        """Formater horaires d'ouverture"""
        if language == 'wo':
            return f"Ci {start_time} ba {end_time}"
        return f"De {start_time} à {end_time}"


# =============================================================================
# HELPERS NOTIFICATIONS
# =============================================================================

class NotificationHelper:
    """Helper pour notifications (SMS, Email, Push)"""
    
    @staticmethod
    def format_sms_message(template: str, context: Dict[str, Any], max_length: int = 160) -> str:
        """Formater message SMS avec limitation de caractères"""
        message = template.format(**context)
        
        if len(message) <= max_length:
            return message
        
        # Raccourcir intelligemment
        # Garder les infos essentielles
        essential_parts = []
        if 'ticket_number' in context:
            essential_parts.append(f"#{context['ticket_number']}")
        if 'position' in context:
            essential_parts.append(f"Pos:{context['position']}")
        if 'estimated_time' in context:
            essential_parts.append(f"{context['estimated_time']}min")
        
        base_message = "SmartQueue: " + " ".join(essential_parts)
        return base_message[:max_length]
    
    @staticmethod
    def get_notification_preferences(user) -> Dict[str, bool]:
        """Récupérer préférences de notification d'un utilisateur"""
        return {
            'sms': getattr(user, 'sms_notifications', True),
            'email': getattr(user, 'email_notifications', True),
            'push': getattr(user, 'push_notifications', True),
        }


# =============================================================================
# HELPERS CALCULS MÉTIER
# =============================================================================

class BusinessCalculator:
    """Calculateurs pour logique métier SmartQueue"""
    
    @staticmethod
    def calculate_queue_capacity(organization_type: str, base_capacity: int = 50) -> int:
        """Calculer capacité recommandée selon type d'organisation"""
        multipliers = {
            'bank': 1.5,
            'hospital': 2.0,
            'clinic': 1.2,
            'prefecture': 2.5,
            'post_office': 1.3,
        }
        
        multiplier = multipliers.get(organization_type, 1.0)
        return int(base_capacity * multiplier)
    
    @staticmethod
    def calculate_service_priority(service_type: str, customer_type: str = 'normal') -> int:
        """Calculer priorité d'un service"""
        # Priorités de base par service
        service_priorities = {
            'emergency': 5,
            'urgent': 4,
            'vip': 4,
            'appointment': 3,
            'normal': 2,
            'information': 1,
        }
        
        # Bonus selon type de client
        customer_bonus = {
            'vip': 2,
            'elderly': 1,
            'disabled': 1,
            'pregnant': 1,
            'normal': 0,
        }
        
        base_priority = service_priorities.get(service_type, 2)
        bonus = customer_bonus.get(customer_type, 0)
        
        return min(base_priority + bonus, 5)  # Max 5
    
    @staticmethod
    def calculate_subscription_limits(plan: str) -> Dict[str, int]:
        """Calculer limites selon plan d'abonnement"""
        from .constants import SubscriptionPlans
        
        base_limits = {
            'daily_tickets': SubscriptionPlans.LIMITS.get(plan, 50),
            'concurrent_queues': {
                'free': 2,
                'starter': 5,
                'business': 15,
                'enterprise': 50,
            }.get(plan, 2),
            'monthly_sms': {
                'free': 100,
                'starter': 1000,
                'business': 5000,
                'enterprise': 20000,
            }.get(plan, 100),
            'staff_users': {
                'free': 3,
                'starter': 10,
                'business': 50,
                'enterprise': 200,
            }.get(plan, 3),
        }
        
        return base_limits


# =============================================================================
# HELPERS SÉCURITÉ
# =============================================================================

class SecurityHelper:
    """Helpers pour sécurité"""
    
    @staticmethod
    def mask_phone_number(phone: str) -> str:
        """Masquer numéro de téléphone pour logs"""
        if len(phone) < 8:
            return '*' * len(phone)
        return phone[:4] + '*' * (len(phone) - 8) + phone[-4:]
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Masquer email pour logs"""
        if '@' not in email:
            return '*' * len(email)
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def generate_csrf_token() -> str:
        """Générer token CSRF personnalisé"""
        return TokenGenerator.generate_secure_token(32)
    
    @staticmethod
    def hash_sensitive_data(data: str, salt: str = None) -> str:
        """Hasher données sensibles"""
        if not salt:
            salt = secrets.token_hex(16)
        
        return hashlib.pbkdf2_hmac(
            'sha256',
            data.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        ).hex()


# =============================================================================
# HELPERS CACHE
# =============================================================================

class CacheHelper:
    """Helpers pour gestion du cache"""
    
    @staticmethod
    def get_cache_key(model_name: str, obj_id: int, action: str = 'detail') -> str:
        """Générer clé de cache standardisée"""
        return f"smartqueue:{model_name}:{obj_id}:{action}"
    
    @staticmethod
    def invalidate_related_cache(model_name: str, obj_id: int):
        """Invalider caches liés à un objet"""
        patterns = [
            f"smartqueue:{model_name}:{obj_id}:*",
            f"smartqueue:{model_name}:list:*",
            f"smartqueue:analytics:*",
        ]
        
        for pattern in patterns:
            cache.delete_pattern(pattern)
    
    @staticmethod
    def cache_with_timeout(key: str, value: Any, timeout: int = 300):
        """Mettre en cache avec timeout par défaut"""
        cache.set(key, value, timeout)


# =============================================================================
# HELPERS GÉNÉRAUX
# =============================================================================

def get_client_ip(request) -> str:
    """Obtenir IP réelle du client"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def generate_unique_slug(model_class, title: str, slug_field: str = 'slug') -> str:
    """Générer slug unique pour un modèle"""
    from django.utils.text import slugify
    
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    
    while model_class.objects.filter(**{slug_field: slug}).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug


def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """Tronquer texte intelligemment"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)].rstrip() + suffix


def clean_phone_input(phone: str) -> str:
    """Nettoyer entrée téléphone utilisateur"""
    if not phone:
        return ''
    
    # Supprimer caractères non-numériques sauf +
    cleaned = re.sub(r'[^\d\+]', '', phone)
    
    # Normaliser
    normalized = SenegalValidators.normalize_phone_number(cleaned)
    return normalized or cleaned