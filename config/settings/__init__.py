# config/settings/__init__.py
# Auto-détection de l'environnement

import os

# Détecter l'environnement depuis une variable d'environnement
environment = os.environ.get('DJANGO_ENVIRONMENT', 'development')

# Charger la configuration appropriée
if environment == 'production':
    from .production import *
elif environment == 'staging':
    # On peut créer un staging.py plus tard si besoin
    from .production import *
    DEBUG = True
else:
    # Par défaut = développement
    from .development import *

print(f"🌍 Environnement détecté: {environment}")