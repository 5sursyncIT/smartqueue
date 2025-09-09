# apps/notifications/urls.py
"""
URLs pour les notifications SmartQueue
APIs REST pour SMS, Push, Email sénégalais
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Nouvelles vues custom (SOLUTION ANTI-BUG)
    notification_template_list_create_view, notification_template_detail_view,
    send_notification_view, unread_count_view, mark_all_as_read_view,
    # Vues qui marchent encore
    NotificationViewSet, NotificationPreferenceView, SMSProviderViewSet, bulk_notification
)

# Router pour les ViewSets qui marchent encore
router = DefaultRouter()

# Notifications - ViewSet qui marche
router.register(
    r'notifications', 
    NotificationViewSet, 
    basename='notification'
)

# SMS Providers - ViewSet qui marche
router.register(
    r'sms-providers', 
    SMSProviderViewSet, 
    basename='smsprovider'
)

# Configuration des URLs
urlpatterns = [
    # === ViewSets qui marchent ===
    path('', include(router.urls)),
    
    # === TEMPLATES - VUES CUSTOM (SOLUTION ANTI-BUG) ===
    path('notification-templates/', notification_template_list_create_view, name='notification-templates'),
    path('notification-templates/<int:pk>/', notification_template_detail_view, name='notification-template-detail'),
    
    # === PRÉFÉRENCES UTILISATEUR ===
    path('notification-preferences/', NotificationPreferenceView.as_view(), name='notification-preferences'),
    
    # === ACTIONS NOTIFICATIONS - VUES CUSTOM (ROUTAGE SPÉCIAL) ===
    path('send-notification/', send_notification_view, name='send-notification'),
    path('bulk-notification/', bulk_notification, name='bulk-notification'),
    path('unread-count/', unread_count_view, name='unread-count'),
    path('mark-all-read/', mark_all_as_read_view, name='mark-all-read'),
]

"""
=== ENDPOINTS DISPONIBLES APRÈS CORRECTION BUGS ===

📋 TEMPLATES DE NOTIFICATION (VUES CUSTOM) ✅
├── GET    /api/notifications/notification-templates/        → Liste des templates
├── POST   /api/notifications/notification-templates/        → Créer un template (admin)
├── GET    /api/notifications/notification-templates/{id}/   → Détails d'un template
├── PUT    /api/notifications/notification-templates/{id}/   → Modifier un template (admin)
└── DELETE /api/notifications/notification-templates/{id}/   → Supprimer un template (admin)

🔔 NOTIFICATIONS (ViewSet)
├── GET    /api/notifications/notifications/                 → Mes notifications
├── GET    /api/notifications/notifications/{id}/            → Détails d'une notification
├── GET    /api/notifications/notifications/stats/          → Statistiques des notifications
├── POST   /api/notifications/notifications/{id}/mark_as_read/ → Marquer comme lue
└── GET    /api/notifications/notifications/{id}/logs/      → Historique d'envoi

⚙️  PRÉFÉRENCES (APIView)
├── GET    /api/notifications/notification-preferences/      → Mes préférences
└── PUT    /api/notifications/notification-preferences/      → Modifier mes préférences

🏭 FOURNISSEURS SMS (ViewSet) - Admin seulement
├── GET    /api/notifications/sms-providers/                 → Liste des fournisseurs
├── POST   /api/notifications/sms-providers/                 → Ajouter un fournisseur
├── GET    /api/notifications/sms-providers/{id}/            → Détails d'un fournisseur
├── PUT    /api/notifications/sms-providers/{id}/            → Modifier un fournisseur
└── DELETE /api/notifications/sms-providers/{id}/            → Supprimer un fournisseur

🚀 ACTIONS SPÉCIALES (VUES CUSTOM) ✅
├── POST   /api/notifications/notifications/send/            → Envoyer notification manuelle
├── POST   /api/notifications/notifications/bulk/           → Notifications en masse (admin)
├── GET    /api/notifications/notifications/unread-count/   → Compter non lues
└── POST   /api/notifications/notifications/mark-all-read/  → Marquer toutes comme lues

=== CORRECTIONS APPLIQUÉES ===
✅ Templates: ViewSet → Vues custom (évite bug Django REST Framework)
✅ Actions: API views → Vues custom (évite permissions et routing bugs) 
✅ Notifications: ViewSet conservé (marche bien)
✅ Préférences: APIView conservée (marche bien)
✅ SMS Providers: ViewSet conservé (marche bien)
"""