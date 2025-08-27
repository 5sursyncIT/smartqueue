# apps/core/constants.py
"""
Constantes globales SmartQueue
Centralisé pour éviter la duplication et faciliter la maintenance
"""

from django.utils.translation import gettext_lazy as _


# =============================================================================
# LANGUES ET LOCALISATION
# =============================================================================

class Languages:
    """Langues supportées par SmartQueue"""
    FRENCH = 'fr'
    WOLOF = 'wo'
    
    CHOICES = [
        (FRENCH, _('Français')),
        (WOLOF, _('Wolof')),
    ]
    
    DEFAULT = FRENCH


# =============================================================================
# TYPES D'UTILISATEURS ET RÔLES
# =============================================================================

class UserTypes:
    """Types d'utilisateurs dans le système"""
    CUSTOMER = 'customer'
    STAFF = 'staff'
    ADMIN = 'admin'
    SUPER_ADMIN = 'super_admin'
    
    CHOICES = [
        (CUSTOMER, _('Client')),
        (STAFF, _('Personnel')),
        (ADMIN, _('Administrateur')),
        (SUPER_ADMIN, _('Super Administrateur')),
    ]
    
    # Hiérarchie des permissions (du plus bas au plus haut)
    HIERARCHY = [CUSTOMER, STAFF, ADMIN, SUPER_ADMIN]
    
    @classmethod
    def has_higher_permission(cls, user_type1, user_type2):
        """Vérifier si user_type1 a des permissions >= user_type2"""
        try:
            return cls.HIERARCHY.index(user_type1) >= cls.HIERARCHY.index(user_type2)
        except ValueError:
            return False


class Genders:
    """Genres pour profils utilisateurs"""
    MALE = 'M'
    FEMALE = 'F'
    OTHER = 'O'
    PREFER_NOT_SAY = 'N'
    
    CHOICES = [
        (MALE, _('Homme')),
        (FEMALE, _('Femme')),
        (OTHER, _('Autre')),
        (PREFER_NOT_SAY, _('Préfère ne pas dire')),
    ]


# =============================================================================
# TYPES D'ORGANISATIONS
# =============================================================================

class OrganizationTypes:
    """Types d'établissements supportés"""
    BANK = 'bank'
    HOSPITAL = 'hospital'
    CLINIC = 'clinic'
    PHARMACY = 'pharmacy'
    PREFECTURE = 'prefecture'
    MAIRIE = 'mairie'
    POST_OFFICE = 'post_office'
    TELECOM = 'telecom'
    INSURANCE = 'insurance'
    GOVERNMENT = 'government'
    UNIVERSITY = 'university'
    SCHOOL = 'school'
    RESTAURANT = 'restaurant'
    RETAIL = 'retail'
    OTHER = 'other'
    
    CHOICES = [
        (BANK, _('Banque')),
        (HOSPITAL, _('Hôpital')),
        (CLINIC, _('Clinique')),
        (PHARMACY, _('Pharmacie')),
        (PREFECTURE, _('Préfecture')),
        (MAIRIE, _('Mairie')),
        (POST_OFFICE, _('Bureau de Poste')),
        (TELECOM, _('Opérateur Télécom')),
        (INSURANCE, _('Assurance')),
        (GOVERNMENT, _('Administration')),
        (UNIVERSITY, _('Université')),
        (SCHOOL, _('École')),
        (RESTAURANT, _('Restaurant')),
        (RETAIL, _('Commerce')),
        (OTHER, _('Autre')),
    ]


# =============================================================================
# PLANS D'ABONNEMENT
# =============================================================================

class SubscriptionPlans:
    """Plans d'abonnement SmartQueue"""
    FREE = 'free'
    STARTER = 'starter'
    BUSINESS = 'business'
    ENTERPRISE = 'enterprise'
    
    CHOICES = [
        (FREE, _('Gratuit')),
        (STARTER, _('Starter')),
        (BUSINESS, _('Business')),
        (ENTERPRISE, _('Enterprise')),
    ]
    
    # Limites par plan (tickets/jour)
    LIMITS = {
        FREE: 50,
        STARTER: 200,
        BUSINESS: 1000,
        ENTERPRISE: float('inf'),  # Illimité
    }
    
    # Prix mensuel en FCFA
    PRICES = {
        FREE: 0,
        STARTER: 15000,    # ~25 USD
        BUSINESS: 50000,   # ~85 USD  
        ENTERPRISE: 150000, # ~250 USD
    }


# =============================================================================
# STATUTS GÉNÉRIQUES
# =============================================================================

class CommonStatus:
    """Statuts communs utilisés partout"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    FAILED = 'failed'
    EXPIRED = 'expired'
    DRAFT = 'draft'
    PUBLISHED = 'published'
    ARCHIVED = 'archived'
    
    CHOICES = [
        (ACTIVE, _('Actif')),
        (INACTIVE, _('Inactif')),
        (PENDING, _('En attente')),
        (PROCESSING, _('En cours')),
        (COMPLETED, _('Terminé')),
        (CANCELLED, _('Annulé')),
        (FAILED, _('Échoué')),
        (EXPIRED, _('Expiré')),
        (DRAFT, _('Brouillon')),
        (PUBLISHED, _('Publié')),
        (ARCHIVED, _('Archivé')),
    ]


# =============================================================================
# STATUTS SPÉCIFIQUES
# =============================================================================

class TicketStatus:
    """Statuts spécifiques aux tickets"""
    WAITING = 'waiting'
    CALLED = 'called'
    SERVING = 'serving'
    SERVED = 'served'
    NO_SHOW = 'no_show'
    CANCELLED = 'cancelled'
    EXPIRED = 'expired'
    
    CHOICES = [
        (WAITING, _('En attente')),
        (CALLED, _('Appelé')),
        (SERVING, _('En cours de service')),
        (SERVED, _('Servi')),
        (NO_SHOW, _('Absent')),
        (CANCELLED, _('Annulé')),
        (EXPIRED, _('Expiré')),
    ]


class AppointmentStatus:
    """Statuts des rendez-vous"""
    REQUESTED = 'requested'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'
    NO_SHOW = 'no_show'
    RESCHEDULED = 'rescheduled'
    
    CHOICES = [
        (REQUESTED, _('Demandé')),
        (CONFIRMED, _('Confirmé')),
        (CANCELLED, _('Annulé')),
        (COMPLETED, _('Terminé')),
        (NO_SHOW, _('Absent')),
        (RESCHEDULED, _('Reporté')),
    ]


class PaymentStatus:
    """Statuts des paiements"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    SUCCESS = 'success'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'
    EXPIRED = 'expired'
    
    CHOICES = [
        (PENDING, _('En attente')),
        (PROCESSING, _('En cours')),
        (SUCCESS, _('Réussi')),
        (FAILED, _('Échoué')),
        (CANCELLED, _('Annulé')),
        (REFUNDED, _('Remboursé')),
        (EXPIRED, _('Expiré')),
    ]


class QueueStatus:
    """Statuts des files d'attente"""
    OPEN = 'open'
    CLOSED = 'closed'
    PAUSED = 'paused'
    FULL = 'full'
    MAINTENANCE = 'maintenance'
    
    CHOICES = [
        (OPEN, _('Ouverte')),
        (CLOSED, _('Fermée')),
        (PAUSED, _('En pause')),
        (FULL, _('Complète')),
        (MAINTENANCE, _('Maintenance')),
    ]


# =============================================================================
# PRIORITÉS
# =============================================================================

class Priority:
    """Niveaux de priorité"""
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'
    URGENT = 'urgent'
    VIP = 'vip'
    
    CHOICES = [
        (LOW, _('Basse')),
        (NORMAL, _('Normale')),
        (HIGH, _('Haute')),
        (URGENT, _('Urgente')),
        (VIP, _('VIP')),
    ]
    
    # Valeurs numériques pour tri
    VALUES = {
        LOW: 1,
        NORMAL: 2,
        HIGH: 3,
        URGENT: 4,
        VIP: 5,
    }


# =============================================================================
# MOYENS DE PAIEMENT
# =============================================================================

class PaymentMethods:
    """Moyens de paiement au Sénégal"""
    WAVE = 'wave'
    ORANGE_MONEY = 'orange_money'
    FREE_MONEY = 'free_money'
    CASH = 'cash'
    CARD = 'card'
    BANK_TRANSFER = 'bank_transfer'
    
    CHOICES = [
        (WAVE, _('Wave')),
        (ORANGE_MONEY, _('Orange Money')),
        (FREE_MONEY, _('Free Money')),
        (CASH, _('Espèces')),
        (CARD, _('Carte bancaire')),
        (BANK_TRANSFER, _('Virement bancaire')),
    ]
    
    # APIs de paiement mobile
    MOBILE_METHODS = [WAVE, ORANGE_MONEY, FREE_MONEY]


# =============================================================================
# TYPES DE NOTIFICATIONS
# =============================================================================

class NotificationTypes:
    """Types de notifications"""
    SMS = 'sms'
    EMAIL = 'email'
    PUSH = 'push'
    IN_APP = 'in_app'
    
    CHOICES = [
        (SMS, _('SMS')),
        (EMAIL, _('Email')),
        (PUSH, _('Notification Push')),
        (IN_APP, _('Notification in-app')),
    ]


class NotificationCategories:
    """Catégories de notifications"""
    APPOINTMENT = 'appointment'
    TICKET = 'ticket'
    PAYMENT = 'payment'
    QUEUE = 'queue'
    SYSTEM = 'system'
    MARKETING = 'marketing'
    
    CHOICES = [
        (APPOINTMENT, _('Rendez-vous')),
        (TICKET, _('Ticket')),
        (PAYMENT, _('Paiement')),
        (QUEUE, _('File d\'attente')),
        (SYSTEM, _('Système')),
        (MARKETING, _('Marketing')),
    ]


# =============================================================================
# RÉGIONS DU SÉNÉGAL
# =============================================================================

class SenegalRegions:
    """Régions administratives du Sénégal"""
    DAKAR = 'dakar'
    THIES = 'thies'
    SAINT_LOUIS = 'saint-louis'
    DIOURBEL = 'diourbel'
    LOUGA = 'louga'
    FATICK = 'fatick'
    KAOLACK = 'kaolack'
    KAFFRINE = 'kaffrine'
    TAMBACOUNDA = 'tambacounda'
    KEDOUGOU = 'kedougou'
    KOLDA = 'kolda'
    SEDHIOU = 'sedhiou'
    ZIGUINCHOR = 'ziguinchor'
    MATAM = 'matam'
    
    CHOICES = [
        (DAKAR, _('Dakar')),
        (THIES, _('Thiès')),
        (SAINT_LOUIS, _('Saint-Louis')),
        (DIOURBEL, _('Diourbel')),
        (LOUGA, _('Louga')),
        (FATICK, _('Fatick')),
        (KAOLACK, _('Kaolack')),
        (KAFFRINE, _('Kaffrine')),
        (TAMBACOUNDA, _('Tambacounda')),
        (KEDOUGOU, _('Kédougou')),
        (KOLDA, _('Kolda')),
        (SEDHIOU, _('Sédhiou')),
        (ZIGUINCHOR, _('Ziguinchor')),
        (MATAM, _('Matam')),
    ]


# =============================================================================
# CONFIGURATIONS SYSTÈME
# =============================================================================

class SystemSettings:
    """Paramètres système par défaut"""
    
    # Durées par défaut (minutes)
    DEFAULT_TICKET_EXPIRY = 30
    DEFAULT_APPOINTMENT_DURATION = 30
    DEFAULT_QUEUE_SERVICE_TIME = 5
    
    # Limites par défaut
    MAX_TICKETS_PER_USER_PER_DAY = 5
    MAX_APPOINTMENTS_PER_USER_PER_DAY = 3
    MAX_QUEUE_CAPACITY = 100
    
    # Formats téléphone
    SENEGAL_PHONE_REGEX = r'^\+221[0-9]{9}$'
    PHONE_FORMAT_HELP = '+221XXXXXXXXX'
    
    # Codes pays
    SENEGAL_COUNTRY_CODE = '+221'
    
    # Devises
    LOCAL_CURRENCY = 'FCFA'
    USD_CURRENCY = 'USD'
    EUR_CURRENCY = 'EUR'


# =============================================================================
# MESSAGES D'ERREUR STANDARDS
# =============================================================================

class ErrorMessages:
    """Messages d'erreur standardisés"""
    
    # Authentification
    INVALID_CREDENTIALS = _('Identifiants invalides')
    TOKEN_EXPIRED = _('Token expiré')
    ACCESS_DENIED = _('Accès refusé')
    PERMISSION_DENIED = _('Permission insuffisante')
    
    # Validation
    REQUIRED_FIELD = _('Ce champ est obligatoire')
    INVALID_PHONE = _('Numéro de téléphone invalide')
    INVALID_EMAIL = _('Adresse email invalide')
    INVALID_DATE = _('Date invalide')
    
    # Ressources
    NOT_FOUND = _('Ressource non trouvée')
    ALREADY_EXISTS = _('Cette ressource existe déjà')
    CANNOT_DELETE = _('Impossible de supprimer cette ressource')
    
    # Système
    SERVER_ERROR = _('Erreur serveur interne')
    SERVICE_UNAVAILABLE = _('Service temporairement indisponible')
    MAINTENANCE_MODE = _('Système en maintenance')
    
    # Métier
    QUEUE_FULL = _('File d\'attente complète')
    TICKET_EXPIRED = _('Ticket expiré')
    APPOINTMENT_CONFLICT = _('Conflit de rendez-vous')
    PAYMENT_FAILED = _('Paiement échoué')


# =============================================================================
# MESSAGES DE SUCCÈS
# =============================================================================

class SuccessMessages:
    """Messages de succès standardisés"""
    
    CREATED = _('Créé avec succès')
    UPDATED = _('Modifié avec succès')
    DELETED = _('Supprimé avec succès')
    SENT = _('Envoyé avec succès')
    SAVED = _('Sauvegardé avec succès')
    
    # Métier spécifique
    TICKET_CREATED = _('Ticket créé avec succès')
    APPOINTMENT_BOOKED = _('Rendez-vous réservé avec succès')
    PAYMENT_SUCCESS = _('Paiement effectué avec succès')
    SMS_SENT = _('SMS envoyé avec succès')


# =============================================================================
# TEMPLATES DE MESSAGES
# =============================================================================

class MessageTemplates:
    """Templates de messages pour notifications"""
    
    # SMS Templates (français)
    SMS_TICKET_CREATED_FR = "SmartQueue: Votre ticket #{ticket_number} pour {service} est créé. Position: {position}. Temps estimé: {estimated_time}min."
    SMS_TICKET_CALLED_FR = "SmartQueue: C'est votre tour! Présentez-vous au guichet {counter} avec votre ticket #{ticket_number}."
    SMS_APPOINTMENT_CONFIRMED_FR = "SmartQueue: RDV confirmé le {date} à {time} pour {service} chez {organization}."
    
    # SMS Templates (wolof)
    SMS_TICKET_CREATED_WO = "SmartQueue: Sa ticket #{ticket_number} ci {service} dafay am. Position: {position}. Teereu: {estimated_time}min."
    SMS_TICKET_CALLED_WO = "SmartQueue: Sa tour la! Dem ci guichet {counter} ak sa ticket #{ticket_number}."
    SMS_APPOINTMENT_CONFIRMED_WO = "SmartQueue: RDV bi okk na ci {date} ci {time} ngir {service} ci {organization}."
    
    # Email Templates
    EMAIL_APPOINTMENT_REMINDER = """
    Bonjour {customer_name},
    
    Ceci est un rappel pour votre rendez-vous:
    - Date: {date}
    - Heure: {time} 
    - Service: {service}
    - Organisation: {organization}
    - Adresse: {address}
    
    Cordialement,
    Équipe SmartQueue
    """


# =============================================================================
# API ET ENDPOINTS
# =============================================================================

class APIVersions:
    """Versions d'API supportées"""
    V1 = 'v1'
    # V2 = 'v2'  # Future version
    
    SUPPORTED = [V1]
    DEFAULT = V1


class HTTPStatusCodes:
    """Codes HTTP standards utilisés"""
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    CONFLICT = 409
    RATE_LIMITED = 429
    SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503


# =============================================================================
# UTILITAIRES
# =============================================================================

def get_choice_display(choices, value):
    """Helper pour obtenir le display d'une choice"""
    choice_dict = dict(choices)
    return choice_dict.get(value, value)


def get_all_status_choices():
    """Retourne tous les choix de statut combinés"""
    all_choices = []
    all_choices.extend(CommonStatus.CHOICES)
    all_choices.extend(TicketStatus.CHOICES)
    all_choices.extend(AppointmentStatus.CHOICES)
    all_choices.extend(PaymentStatus.CHOICES)
    all_choices.extend(QueueStatus.CHOICES)
    
    # Enlever les doublons en gardant l'ordre
    seen = set()
    unique_choices = []
    for choice in all_choices:
        if choice[0] not in seen:
            unique_choices.append(choice)
            seen.add(choice[0])
    
    return unique_choices