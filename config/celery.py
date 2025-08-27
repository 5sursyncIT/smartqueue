# config/celery.py
"""
Configuration Celery pour SmartQueue
Tâches asynchrones pour géolocalisation intelligente
"""

import os
from celery import Celery
from django.conf import settings

# Définir module settings Django pour Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Créer instance Celery
app = Celery('smartqueue')

# Configuration depuis Django settings avec préfixe CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-découverte des tâches dans les apps
app.autodiscover_tasks()

# Configuration des tâches périodiques (Celery Beat)
from celery.schedules import crontab

app.conf.beat_schedule = {
    # Géolocalisation - toutes les 5 minutes
    'update-user-locations': {
        'task': 'apps.locations.tasks.update_user_locations',
        'schedule': 300.0,  # 5 minutes
    },
    
    # Calcul temps de trajet - toutes les 10 minutes
    'calculate-travel-estimates': {
        'task': 'apps.locations.tasks.calculate_travel_estimates_for_active_tickets',
        'schedule': 600.0,  # 10 minutes
    },
    
    # Réorganisation files - toutes les 5 minutes
    'check-queue-reorganization': {
        'task': 'apps.locations.tasks.check_queue_reorganization',
        'schedule': 300.0,  # 5 minutes
    },
    
    # Notifications départ - chaque minute
    'send-departure-notifications': {
        'task': 'apps.locations.tasks.send_departure_notifications',
        'schedule': 60.0,  # 1 minute
    },
    
    # Mise à jour trafic - toutes les 15 minutes
    'update-traffic-conditions': {
        'task': 'apps.locations.tasks.update_traffic_conditions',
        'schedule': 900.0,  # 15 minutes
    },
    
    # Nettoyage - quotidien à 2h du matin
    'cleanup-old-location-data': {
        'task': 'apps.locations.tasks.cleanup_old_location_data',
        'schedule': crontab(hour=2, minute=0),
    },
}

# Timezone pour les tâches
app.conf.timezone = 'Africa/Dakar'

# Configuration avancée pour production
app.conf.update(
    # Sérialisation
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Résultats
    result_expires=3600,  # 1 heure
    result_backend_transport_options={
        'visibility_timeout': 43200,  # 12 heures
        'retry_policy': {
            'timeout': 5.0
        }
    },
    
    # Configuration worker
    worker_prefetch_multiplier=4,
    worker_concurrency=4,
    worker_max_tasks_per_child=1000,
    
    # Routage des tâches
    task_routes={
        # Tâches géolocalisation sur queue dédiée
        'apps.locations.tasks.*': {'queue': 'locations'},
        # Tâches notifications rapides
        'apps.notifications.tasks.*': {'queue': 'notifications'},
        # Autres tâches sur queue par défaut
        '*': {'queue': 'default'},
    },
)

@app.task(bind=True)
def debug_task(self):
    """Tâche de debug"""
    print(f'Request: {self.request!r}')

# Log démarrage
print("📍 Celery configuré pour SmartQueue avec géolocalisation intelligente")