# config/settings/base.py
"""
Configuration de base pour SmartQueue Sénégal
Ces paramètres sont communs à tous les environnements (dev, staging, production)
"""

import os
from pathlib import Path
from datetime import timedelta
import environ

# ==============================================
# CHEMINS DE BASE
# ==============================================

# Chemin vers la racine du projet (où se trouve manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Configuration des variables d'environnement (.env)
env = environ.Env(
    # Valeurs par défaut si les variables ne sont pas définies
    DEBUG=(bool, False),
    SECRET_KEY=(str, 'your-secret-key-here'),
    ALLOWED_HOSTS=(list, []),
)

# Lecture du fichier .env s'il existe
environ.Env.read_env(BASE_DIR / '.env')

# ==============================================
# APPLICATIONS DJANGO
# ==============================================

# Applications Django par défaut (obligatoires)
DJANGO_APPS = [
    'django.contrib.admin',        # Interface d'administration
    'django.contrib.auth',         # Système d'authentification
    'django.contrib.contenttypes', # Types de contenu
    'django.contrib.sessions',     # Sessions utilisateur
    'django.contrib.messages',     # Messages flash
    'django.contrib.staticfiles',  # Fichiers statiques (CSS, JS, images)
    'django.contrib.gis',         # Géolocalisation (pour le Sénégal)
]

# Applications tierces (packages externes)
THIRD_PARTY_APPS = [
    # API REST
    'rest_framework',              # Django REST Framework
    'rest_framework_simplejwt',    # Authentification JWT
    'drf_spectacular',             # Documentation API automatique
    'django_filters',              # Filtrage des données
    
    # CORS pour React
    'corsheaders',                 # Permet à React de communiquer avec Django
    
    # Temps réel (désactivé pour test)
    # 'channels',                    # WebSockets pour notifications instantanées
    
    # Tâches asynchrones (désactivé pour test)
    # 'django_celery_beat',          # Tâches programmées
    # 'django_celery_results',       # Stockage résultats Celery
    
    # Multilingue (désactivé pour test)
    # 'rosetta',                     # Interface de traduction
    # 'modeltranslation',            # Traduction des modèles
    
    # Développement (désactivé pour test)
    # 'django_extensions',           # Outils utiles pour le développement
]

# NOS applications SmartQueue (Architecture restructurée ✅)
LOCAL_APPS = [
    'apps.core',              # Utilitaires communs
    'apps.accounts',          # Utilisateurs et authentification  
    'apps.business',          # Organizations + Services unifiés ✅
    'apps.queue_management',  # Queues + Tickets unifiés ✅
    # À réactiver après correction des dépendances (prochaine étape)
    # 'apps.locations',         # Géolocalisation intelligente
    # 'apps.appointments',      # Système de rendez-vous
    # 'apps.notifications',     # SMS, Push, Email
    # 'apps.payments',         # Orange Money, Wave, Free Money
    # 'apps.analytics',        # Statistiques et rapports
    
    # === ANCIENNES APPS (REMPLACÉES) ===
    # 'apps.organizations',  # REMPLACÉE par apps.business
    # 'apps.services',       # REMPLACÉE par apps.business
    # 'apps.queues',        # REMPLACÉE par apps.queue_management
    # 'apps.tickets',       # REMPLACÉE par apps.queue_management
]

# Toutes les applications ensemble
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ==============================================
# MIDDLEWARE (Couches de traitement des requêtes)
# ATTENTION : L'ORDRE EST TRÈS IMPORTANT !
# ==============================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',     # Sécurité
    'corsheaders.middleware.CorsMiddleware',             # CORS (doit être en haut)
    'django.contrib.sessions.middleware.SessionMiddleware', # Sessions
    'django.middleware.locale.LocaleMiddleware',         # Français/Wolof
    'django.middleware.common.CommonMiddleware',         # Fonctionnalités communes
    'django.middleware.csrf.CsrfViewMiddleware',        # Protection CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware', # Authentification
    'django.contrib.messages.middleware.MessageMiddleware',    # Messages
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Protection clickjacking
]

# ==============================================
# CONFIGURATION URLS ET WSGI
# ==============================================

ROOT_URLCONF = 'config.urls'           # Fichier principal des URLs
WSGI_APPLICATION = 'config.wsgi.application'  # Pour serveur web classique
ASGI_APPLICATION = 'config.asgi.application'  # Pour WebSockets

# ==============================================
# TEMPLATES (Pages HTML)
# ==============================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Dossier des templates
        'APP_DIRS': True,                  # Chercher dans chaque app
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.i18n',  # Pour multilingue
            ],
        },
    },
]

# ==============================================
# MODÈLE UTILISATEUR PERSONNALISÉ
# ==============================================

# Utiliser NOTRE modèle User au lieu de celui par défaut
AUTH_USER_MODEL = 'accounts.User'

# ==============================================
# CONFIGURATION API REST
# ==============================================

REST_FRAMEWORK = {
    # Comment s'authentifier
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',  # JWT principal
        'rest_framework.authentication.SessionAuthentication',        # Session pour admin
    ],
    
    # Permissions par défaut (il faut être connecté)
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    
    # Format des réponses
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',           # JSON
        'rest_framework.renderers.BrowsableAPIRenderer',   # Interface web
    ],
    
    # Pagination (20 éléments par page)
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    
    # Filtrage et recherche
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    
    # Documentation automatique
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ==============================================
# CONFIGURATION JWT (Tokens d'authentification)
# ==============================================

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=24),    # Token valable 24h
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # Refresh token 7 jours
    'ROTATE_REFRESH_TOKENS': True,                   # Nouveau token à chaque refresh
    'BLACKLIST_AFTER_ROTATION': True,               # Invalider l'ancien token
    'UPDATE_LAST_LOGIN': True,                       # Mettre à jour dernière connexion
    
    'ALGORITHM': 'HS256',                            # Algorithme de chiffrement
    'SIGNING_KEY': env('SECRET_KEY'),                # Clé de signature
    
    'AUTH_HEADER_TYPES': ('Bearer',),               # Type d'en-tête: Bearer TOKEN
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',       # Nom de l'en-tête
}

# ==============================================
# DOCUMENTATION API
# ==============================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'SmartQueue Sénégal API',
    'DESCRIPTION': 'API de gestion des files d\'attente virtuelles pour le Sénégal',
    'VERSION': '1.0.0',
    'CONTACT': {
        'name': 'Équipe SmartQueue',
        'email': 'dev@smartqueue.sn',
    },
}

# ==============================================
# MULTILINGUE - CONFIGURATION SÉNÉGAL
# ==============================================

LANGUAGE_CODE = 'fr'                    # Français par défaut
TIME_ZONE = 'Africa/Dakar'              # Fuseau horaire du Sénégal

USE_I18N = True                         # Activer internationalisation
USE_L10N = True                         # Activer localisation
USE_TZ = True                           # Support des fuseaux horaires

# Langues supportées dans SmartQueue
LANGUAGES = [
    ('fr', 'Français'),                 # Langue officielle
    ('wo', 'Wolof'),                    # Langue nationale principale
    ('en', 'English'),                  # Pour expansion internationale
]

# Dossier des traductions
LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Formats de date/heure pour le Sénégal
DATE_FORMAT = 'd/m/Y'                   # 15/08/2025
TIME_FORMAT = 'H:i'                     # 14:30
DATETIME_FORMAT = 'd/m/Y H:i'           # 15/08/2025 14:30

# ==============================================
# FICHIERS STATIQUES ET MEDIA
# ==============================================

STATIC_URL = '/static/'                 # URL pour fichiers CSS/JS
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Dossier final pour production
STATICFILES_DIRS = [                    # Dossiers source
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'                   # URL pour fichiers uploadés
MEDIA_ROOT = BASE_DIR / 'media'         # Dossier des fichiers uploadés

# ==============================================
# SÉCURITÉ DES MOTS DE PASSE
# ==============================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,             # Minimum 8 caractères
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==============================================
# WEBSOCKETS (Notifications temps réel)
# ==============================================

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],  # Redis local
        },
    },
}

# ==============================================
# CELERY (Tâches asynchrones)
# ==============================================

CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# ==============================================
# CACHE (Stockage temporaire pour performance)
# ==============================================

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Utiliser Redis pour les sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ==============================================
# LOGGING (Journalisation)
# ==============================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'smartqueue.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps': {  # Logs de nos applications SmartQueue
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Créer le dossier logs s'il n'existe pas
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# ==============================================
# SÉCURITÉ DE BASE
# ==============================================

SECURE_BROWSER_XSS_FILTER = True       # Protection XSS
SECURE_CONTENT_TYPE_NOSNIFF = True     # Protection MIME
X_FRAME_OPTIONS = 'DENY'               # Protection clickjacking

# Type de clé primaire par défaut
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'