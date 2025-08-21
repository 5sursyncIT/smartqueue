# apps/notifications/urls.py
"""
URLs pour les notifications SmartQueue
APIs REST pour SMS, Push, Email sénégalais
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationTemplateViewSet, NotificationViewSet, NotificationPreferenceView,
    SMSProviderViewSet, send_notification, bulk_notification,
    unread_count, mark_all_as_read
)

# Router principal pour les ViewSets
router = DefaultRouter()

# Enregistrer les ViewSets
router.register(
    r'notification-templates', 
    NotificationTemplateViewSet, 
    basename='notificationtemplate'
)

router.register(
    r'notifications', 
    NotificationViewSet, 
    basename='notification'
)

router.register(
    r'sms-providers', 
    SMSProviderViewSet, 
    basename='smsprovider'
)

# Configuration des URLs
urlpatterns = [
    # === URLS PRINCIPALES ===
    # Toutes les URLs des ViewSets (CRUD + actions personnalisées)
    path('', include(router.urls)),
    
    # === PRÉFÉRENCES UTILISATEUR ===
    path('notification-preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
    
    # === ACTIONS NOTIFICATIONS ===
    path('notifications/send/', send_notification, name='send-notification'),
    path('notifications/bulk/', bulk_notification, name='bulk-notification'),
    path('notifications/unread-count/', unread_count, name='unread-count'),
    path('notifications/mark-all-read/', mark_all_as_read, name='mark-all-read'),
]

"""
=== ENDPOINTS DISPONIBLES ===

📋 TEMPLATES DE NOTIFICATION (NotificationTemplate)
├── GET    /api/notification-templates/              → Liste des templates
├── POST   /api/notification-templates/              → Créer un template (admin)
├── GET    /api/notification-templates/{id}/         → Détails d'un template
├── PUT    /api/notification-templates/{id}/         → Modifier un template (admin)
└── DELETE /api/notification-templates/{id}/         → Supprimer un template (admin)

🔔 NOTIFICATIONS (Notification)
├── GET    /api/notifications/                       → Mes notifications
├── GET    /api/notifications/{id}/                  → Détails d'une notification
├── GET    /api/notifications/stats/                 → Statistiques des notifications
├── POST   /api/notifications/{id}/mark_as_read/     → Marquer comme lue
└── GET    /api/notifications/{id}/logs/             → Historique d'envoi

⚙️  PRÉFÉRENCES (NotificationPreference)
├── GET    /api/notification-preferences/            → Mes préférences
└── PUT    /api/notification-preferences/            → Modifier mes préférences

🏭 FOURNISSEURS SMS (SMSProvider) - Admin seulement
├── GET    /api/sms-providers/                       → Liste des fournisseurs
├── POST   /api/sms-providers/                       → Ajouter un fournisseur
├── GET    /api/sms-providers/{id}/                  → Détails d'un fournisseur
├── PUT    /api/sms-providers/{id}/                  → Modifier un fournisseur
└── DELETE /api/sms-providers/{id}/                  → Supprimer un fournisseur

🚀 ACTIONS SPÉCIALES
├── POST   /api/notifications/send/                  → Envoyer notification manuelle
├── POST   /api/notifications/bulk/                  → Notifications en masse (admin)
├── GET    /api/notifications/unread-count/          → Compter non lues
└── POST   /api/notifications/mark-all-read/         → Marquer toutes comme lues

=== PERMISSIONS ===
🔓 Public (pas d'authentification) :
   - Aucun endpoint public

🔐 Connecté (authentification requise) :
   - GET /api/notification-templates/ (voir templates)
   - GET /api/notifications/ (ses notifications)
   - GET/PUT /api/notification-preferences/ (ses préférences)
   - POST /api/notifications/send/ (envoyer notification)
   - Toutes les actions sur ses propres notifications

👨‍💼 Admin seulement :
   - POST/PUT/DELETE /api/notification-templates/
   - GET/POST/PUT/DELETE /api/sms-providers/
   - POST /api/notifications/bulk/

👤 Filtrage automatique selon le type d'utilisateur :
   - CUSTOMER : voit seulement ses notifications
   - STAFF/ADMIN : voit les notifications de son organisation
   - SUPER_ADMIN : voit toutes les notifications

=== EXEMPLES D'UTILISATION ===

1. Voir mes notifications non lues :
   GET /api/notifications/?status=sent&read_at__isnull=true

2. Créer un template SMS (admin) :
   POST /api/notification-templates/
   {
     "name": "SMS Ticket Appelé",
     "category": "ticket_called",
     "notification_type": "sms",
     "message_fr": "Votre ticket {ticket_number} est appelé au guichet {window_number}. Merci de vous présenter.",
     "message_wo": "Sa ticket {ticket_number} wax na guichet {window_number}. Jox ko jekk."
   }

3. Configurer mes préférences :
   PUT /api/notification-preferences/
   {
     "prefer_sms": true,
     "prefer_email": false,
     "language": "fr",
     "notify_ticket_called": true,
     "quiet_hours_start": "22:00",
     "quiet_hours_end": "07:00"
   }

4. Envoyer notification manuelle :
   POST /api/notifications/send/
   {
     "template_id": 1,
     "recipient_ids": [123, 456],
     "custom_variables": {
       "ticket_number": "T001",
       "window_number": "G3"
     },
     "priority": "high"
   }

5. Notifications en masse pour tous les clients BHS :
   POST /api/notifications/bulk/
   {
     "template_id": 2,
     "user_type": "customer",
     "organization_ids": [1],
     "custom_variables": {
       "message": "Maintenance système prévue dimanche 9h-12h"
     },
     "dry_run": true
   }

6. Marquer une notification comme lue :
   POST /api/notifications/123/mark_as_read/

7. Voir l'historique d'envoi :
   GET /api/notifications/123/logs/

8. Statistiques des notifications :
   GET /api/notifications/stats/

=== INTÉGRATION AVEC LES AUTRES APPS ===

🎫 Avec Tickets :
   - Notification automatique quand ticket appelé
   - SMS de position dans la file d'attente
   - Notification de fin de service

📅 Avec Appointments :
   - Confirmation de RDV par SMS/Email
   - Rappels automatiques 24h avant
   - Notifications d'annulation/report

🏢 Avec Organizations :
   - Filtrage des notifications par organisation
   - Templates spécifiques par organisation
   - Notifications de maintenance/fermeture

👥 Avec Accounts :
   - Préférences liées au profil utilisateur
   - Notifications d'activation de compte
   - Messages de bienvenue
"""