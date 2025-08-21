# apps/appointments/urls.py
"""
URLs pour les rendez-vous SmartQueue
Gestion des RDV pour banques, hôpitaux, administrations sénégalaises
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentSlotViewSet, AppointmentViewSet, todays_appointments

# Router principal pour les ViewSets
router = DefaultRouter()

# Enregistrer les ViewSets avec leurs préfixes d'URL
router.register(
    r'appointment-slots', 
    AppointmentSlotViewSet, 
    basename='appointmentslot'
)

router.register(
    r'appointments', 
    AppointmentViewSet, 
    basename='appointment'
)

# Configuration des URLs
urlpatterns = [
    # === URLS PRINCIPALES ===
    # Toutes les URLs des ViewSets (CRUD + actions personnalisées)
    path('', include(router.urls)),
    
    # === URLS UTILITAIRES ===
    # RDV du jour pour le personnel
    path('today/', todays_appointments, name='todays-appointments'),
]

"""
=== ENDPOINTS DISPONIBLES ===

📅 CRÉNEAUX HORAIRES (AppointmentSlot)
├── GET    /api/appointment-slots/                    → Liste des créneaux
├── GET    /api/appointment-slots/{id}/               → Détails d'un créneau
└── GET    /api/appointment-slots/available/          → Créneaux disponibles
    ├── Paramètres: ?date=2025-08-20&service_id=1&organization_id=1
    └── Retour: Liste des créneaux libres avec horaires disponibles

🗓️  RENDEZ-VOUS (Appointment)
├── GET    /api/appointments/                         → Mes RDV (client) / RDV organisation (staff)
├── POST   /api/appointments/                         → Prendre un nouveau RDV
├── GET    /api/appointments/{id}/                    → Détails d'un RDV
├── PUT    /api/appointments/{id}/                    → Modifier un RDV (notes, priorité)
├── PATCH  /api/appointments/{id}/                    → Modification partielle
├── DELETE /api/appointments/{id}/                    → Annuler un RDV
├── GET    /api/appointments/stats/                   → Statistiques des RDV
├── POST   /api/appointments/{id}/confirm/            → Confirmer un RDV (staff)
├── POST   /api/appointments/{id}/cancel/             → Annuler un RDV
├── POST   /api/appointments/{id}/reschedule/         → Reporter un RDV
├── POST   /api/appointments/{id}/check_in/           → Check-in client (arrivée)
├── POST   /api/appointments/{id}/start_service/      → Commencer le service
├── POST   /api/appointments/{id}/complete/           → Terminer le service
└── GET    /api/appointments/{id}/history/            → Historique des modifications

🏥 UTILITAIRES
└── GET    /api/appointments/today/                   → RDV du jour (par type d'utilisateur)

=== PERMISSIONS ===
🔓 Public (pas d'authentification) :
   - GET /api/appointment-slots/ (voir disponibilités)
   - GET /api/appointment-slots/available/

🔐 Connecté (authentification requise) :
   - Toutes les autres URLs

👤 Filtrage automatique selon le type d'utilisateur :
   - CUSTOMER : voit seulement ses propres RDV
   - STAFF/ADMIN : voit les RDV de son organisation
   - SUPER_ADMIN : voit tous les RDV

=== EXEMPLES D'UTILISATION ===

1. Voir les créneaux disponibles demain pour BHS :
   GET /api/appointment-slots/available/?date=2025-08-20&organization_id=1

2. Prendre un RDV :
   POST /api/appointments/
   {
     "appointment_slot": 1,
     "scheduled_date": "2025-08-20", 
     "scheduled_time": "14:30",
     "priority": "medium",
     "customer_notes": "Ouverture compte épargne",
     "customer_phone": "+221701234567"
   }

3. Confirmer un RDV (staff seulement) :
   POST /api/appointments/123/confirm/
   {
     "reason": "Dossier complet et vérifié"
   }

4. Reporter un RDV :
   POST /api/appointments/123/reschedule/
   {
     "new_appointment_slot": 2,
     "new_scheduled_date": "2025-08-21",
     "new_scheduled_time": "10:00",
     "reason": "Client pas disponible mercredi"
   }

5. Voir mes RDV à venir :
   GET /api/appointments/?status=confirmed&scheduled_date__gte=2025-08-19

6. RDV du jour pour le personnel :
   GET /api/appointments/today/
"""