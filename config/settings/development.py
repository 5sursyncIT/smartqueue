# config/settings/development.py
# Configuration pour l'environnement de développement

from .base import *

# ==============================================
# PARAMÈTRES DE DÉVELOPPEMENT
# ==============================================

# Clé secrète pour développement (pas grave si elle est simple)
SECRET_KEY = env('SECRET_KEY', default='django-insecure-dev-key-change-in-production')

# Mode debug activé (affiche les erreurs détaillées)
DEBUG = True

# Hôtes autorisés en développement
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', '34.31.49.122']

# ==============================================
# BASE DE DONNÉES - DÉVELOPPEMENT (POSTGRESQL)
# ==============================================

# SQLite pour développement et tests (plus simple)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_dev.sqlite3',
    }
}

# ==============================================
# CORS POUR REACT (Frontend)
# ==============================================

# En développement, on autorise React à communiquer avec Django
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
    "http://localhost:8080",  # Autre port possible
]

CORS_ALLOW_CREDENTIALS = True

# ==============================================
# OUTILS DE DÉVELOPPEMENT (désactivé pour test)
# ==============================================

# Ajouter la debug toolbar (outil pour développeurs) - DÉSACTIVÉ
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

# Configuration debug toolbar
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# ==============================================
# EMAIL EN DÉVELOPPEMENT
# ==============================================

# Afficher les emails dans la console (pas d'envoi réel)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ==============================================
# CACHE SIMPLIFIÉ
# ==============================================

# Cache en mémoire (simple pour développement)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# WebSockets en mémoire (désactivé pour test)
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels.layers.InMemoryChannelLayer'
#     }
# }

# ==============================================
# TÂCHES ASYNCHRONES SIMPLIFIÉES
# ==============================================

# Exécuter Celery en mode synchrone (pas besoin de Redis)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ==============================================
# LOGS PLUS DÉTAILLÉS
# ==============================================

LOGGING['handlers']['console']['level'] = 'DEBUG'
LOGGING['loggers']['apps']['level'] = 'DEBUG'

print("🚀 Configuration DÉVELOPPEMENT chargée")