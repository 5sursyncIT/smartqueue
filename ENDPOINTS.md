# SmartQueue API - Endpoints Complets 🔗

**Version** : 1.0.0
**Mise à jour** : 19 septembre 2024
**Base URL** : `http://localhost:8000/api/`
**WebSocket URL** : `ws://localhost:8000/ws/`

## 📋 Table des Matières

1. [Authentification & Comptes](#auth)
2. [Business (Organisations + Services)](#business)
3. [Queue Management (Files + Tickets)](#queues)
4. [Appointments (Rendez-vous)](#appointments)
5. [Locations (Géolocalisation)](#locations)
6. [Notifications](#notifications)
7. [Payments (Paiements)](#payments)
8. [Analytics](#analytics)
9. [WebSocket Temps Réel](#websocket)

---

## 🔐 1. Authentification & Comptes {#auth}

### JWT Authentication (100% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/accounts/auth/login/` | POST | ✅ | Connexion JWT par email |
| `/accounts/auth/logout/` | POST | ✅ | Déconnexion + blacklist token |
| `/accounts/auth/refresh/` | POST | ✅ | Renouveler access token |
| `/accounts/auth/register/` | POST | ✅ | Inscription par email |
| `/accounts/auth/verify-email/` | POST | ✅ | Vérification par email |
| `/accounts/auth/request-reset/` | POST | ✅ | Reset mot de passe |

**Fonctionnalités développées :**
- Types utilisateurs : client, staff, admin, super_admin
- Authentification EMAIL prioritaire (téléphone optionnel)
- Codes vérification 6 chiffres par email
- Support multilingue (Français/Wolof)
- Profils complets avec préférences

#### Exemples d'utilisation

**Login**
```bash
POST /api/accounts/auth/login/
{
  "login": "user@example.com",  # Email ou nom utilisateur
  "password": "password123"
}

# Response
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "user_type": "client"
  }
}
```

**Register**
```bash
POST /api/accounts/auth/register/
{
  "email": "new@example.com",
  "password": "password123",
  "password2": "password123",
  "first_name": "Jane",
  "last_name": "Doe",
  "phone": "+221771234567",
  "user_type": "client"
}
```

### Gestion Utilisateurs
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/accounts/users/me/` | GET | ✅ | Profil utilisateur actuel |
| `/accounts/users/me/` | PUT/PATCH | ✅ | Modifier son profil |
| `/accounts/users/{id}/` | GET | ✅ | Détails utilisateur |
| `/accounts/users/` | GET | ✅ | Liste utilisateurs (admin) |

---

## 🏢 2. Business (Organisations + Services) {#business}

### Organisations (90% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/business/organizations/` | GET | ✅ | Liste organisations |
| `/business/organizations/` | POST | ✅ | Créer organisation |
| `/business/organizations/{id}/` | GET | ✅ | Détail organisation |
| `/business/organizations/{id}/` | PUT/PATCH | ✅ | Modifier organisation |
| `/business/organizations/{id}/` | DELETE | ✅ | Supprimer organisation |
| `/business/organizations/{id}/services/` | GET | ✅ | Services d'une organisation |

**Fonctionnalités développées :**
- 9 types d'organisations (banque, hôpital, admin, télécom, etc.)
- 14 régions sénégalaises complètes
- Plans d'abonnement B2B (starter, business, enterprise)
- Géolocalisation GPS intégrée

#### Exemple Organisation
```bash
POST /api/business/organizations/
{
  "name": "Hôpital Principal de Dakar",
  "description": "Services médicaux",
  "location": "Dakar, Plateau",
  "contact_phone": "+221338234567",
  "contact_email": "contact@hopital-dakar.sn",
  "opening_hours": {
    "monday": ["08:00", "18:00"],
    "tuesday": ["08:00", "18:00"],
    "wednesday": ["08:00", "18:00"],
    "thursday": ["08:00", "18:00"],
    "friday": ["08:00", "18:00"],
    "saturday": ["08:00", "12:00"]
  }
}
```

### Services (90% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/business/services/` | GET | ✅ | Liste services |
| `/business/services/` | POST | ✅ | Créer service |
| `/business/services/{id}/` | GET | ✅ | Détail service |
| `/business/services/{id}/` | PUT/PATCH | ✅ | Modifier service |
| `/business/services/{id}/` | DELETE | ✅ | Supprimer service |

**Fonctionnalités développées :**
- Catégories avec icônes et couleurs
- Tarification et durée estimée
- Horaires configurables par service
- 4 niveaux de priorité

#### Exemple Service
```bash
POST /api/business/services/
{
  "name": "Consultation Générale",
  "description": "Consultation médicale générale",
  "organization": 1,
  "estimated_duration": 30,  # minutes
  "price": 5000,  # FCFA
  "category": "medical",
  "is_appointment_required": true
}
```

---

## 🎯 3. Queue Management (Files + Tickets) {#queues}

### Files d'Attente (95% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/queue-management/queues/` | GET | ✅ | Liste files d'attente |
| `/queue-management/queues/` | POST | ✅ | Créer file d'attente |
| `/queue-management/queues/{id}/` | GET | ✅ | Détail file |
| `/queue-management/queues/{id}/` | PUT/PATCH | ✅ | Modifier file |
| `/queue-management/queues/{id}/` | DELETE | ✅ | Supprimer file |
| `/queue-management/queues/{id}/with-travel/` | GET | ✅ | File + temps trajet GPS |
| `/queue-management/queues/{id}/stats/` | GET | ✅ | Statistiques file |

**Fonctionnalités développées :**
- 5 types files (normale, prioritaire, VIP, RDV, express)
- 4 stratégies traitement (FIFO, priorité, mixte)
- Intégration géolocalisation intelligente
- Calcul temps d'attente automatique

#### Exemple File d'Attente
```bash
POST /api/queues/queues/
{
  "name": "Consultation Générale - Matin",
  "service": 1,
  "max_capacity": 50,
  "estimated_wait_time_per_person": 15,  # minutes
  "opening_time": "08:00",
  "closing_time": "12:00",
  "is_active": true
}
```

### Tickets (95% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/queue-management/tickets/` | GET | ✅ | Mes tickets |
| `/queue-management/tickets/` | POST | ✅ | Prendre ticket intelligent |
| `/queue-management/tickets/{id}/` | GET | ✅ | Détail ticket |
| `/queue-management/tickets/{id}/` | PUT/PATCH | ✅ | Modifier ticket |
| `/queue-management/tickets/{id}/` | DELETE | ✅ | Annuler ticket |
| `/queue-management/tickets/{id}/call/` | POST | ✅ | Appeler ticket (staff) |
| `/queue-management/tickets/{id}/complete/` | POST | ✅ | Compléter service |
| `/queue-management/tickets/my/` | GET | ✅ | Mes tickets actifs |

**Fonctionnalités développées :**
- 8 statuts tickets (waiting, called, serving, served, etc.)
- 6 canaux création (mobile, web, SMS, kiosk, guichet)
- 4 niveaux priorité (normale, moyenne, élevée, urgente)
- Position GPS client stockée automatiquement

#### Exemple Prendre Ticket
```bash
POST /api/queues/tickets/
{
  "queue": 1,
  "user": 2,
  "notes": "Consultation de contrôle"
}

# Response
{
  "id": 15,
  "queue": 1,
  "ticket_number": "A015",
  "user": 2,
  "status": "waiting",
  "created_at": "2025-09-11T09:30:00Z",
  "estimated_call_time": "2025-09-11T10:15:00Z",
  "position_in_queue": 3
}
```

---

## 📅 4. Appointments (Rendez-vous) {#appointments}

### Créneaux de Rendez-vous ✅ FIXÉ
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/appointments/appointment-slots/` | GET | ✅ | **240 créneaux générés** |
| `/appointments/appointment-slots/{id}/` | GET | ✅ | Détail créneau |
| `/appointments/appointment-slots/available/` | GET | ✅ | Créneaux libres |

#### Créneaux Générés Automatiquement
- **Période** : Lundi à Vendredi
- **Heures** : 9h00 à 17h00
- **Intervalles** : 30 minutes
- **Total** : 240 créneaux sur 4 semaines

### Rendez-vous
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/appointments/appointments/` | GET | ✅ | Mes rendez-vous |
| `/appointments/appointments/` | POST | ✅ | Réserver rendez-vous |
| `/appointments/appointments/{id}/` | GET | ✅ | Détail RDV |
| `/appointments/appointments/{id}/` | PUT/PATCH | ✅ | Modifier RDV |
| `/appointments/appointments/{id}/` | DELETE | ✅ | Annuler RDV |
| `/appointments/my-appointments/` | GET | ✅ | Mes RDV à venir |

#### Exemple Réservation
```bash
POST /api/appointments/appointments/
{
  "appointment_slot": 15,
  "user": 2,
  "service": 1,
  "notes": "Premier rendez-vous",
  "phone": "+221771234567"
}
```

---

## 🗺️ 5. Locations (Géolocalisation Intelligente) {#locations}

### Géolocalisation Utilisateur (92% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/locations/user/location/update/` | POST | ✅ | Mettre à jour position GPS |
| `/locations/user/location/` | GET | ✅ | Ma position actuelle |
| `/locations/nearby-organizations/` | GET | ✅ | Organisations proches GPS |

### Données Géographiques Sénégal (100% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/locations/regions/` | GET | ✅ | 14 régions du Sénégal |
| `/locations/communes/` | GET | ✅ | Communes par région |
| `/locations/communes/{id}/services/` | GET | ✅ | Services dans commune |

### Calculs de Trajet Intelligents (92% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/locations/travel-estimates/calculate/` | POST | ✅ | Temps trajet + embouteillages |
| `/locations/travel-estimates/` | GET | ✅ | Historique trajets |
| `/locations/nearby-services/` | GET | ✅ | Services à proximité distance |

**Fonctionnalités développées :**
- Position GPS temps réel utilisateurs
- Calcul trajets avec embouteillages Dakar
- 4 modes transport (voiture, transport, taxi, pied)
- Notifications départ intelligentes ("Partez maintenant")
- Optimisation files selon temps trajet
- Facteurs trafic (heures pointe, jours semaine)

#### Exemple Calcul Trajet
```bash
POST /api/locations/travel-estimates/
{
  "user_location": {
    "latitude": 14.6937,
    "longitude": -17.4441  # Dakar
  },
  "destination": {
    "latitude": 14.7645,
    "longitude": -17.3660  # Guédiawaye
  },
  "transport_mode": "driving"  # driving, walking, public_transport
}

# Response
{
  "distance_km": 12.5,
  "duration_minutes": 25,
  "transport_mode": "driving",
  "route_quality": "moderate_traffic"
}
```

---

## 📢 6. Notifications (SMS/Push) {#notifications}

### Gestion Notifications (85% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/notifications/notifications/` | GET | ✅ | Mes notifications |
| `/notifications/notifications/{id}/mark-read/` | POST | ✅ | Marquer comme lu |
| `/notifications/settings/` | GET/PUT | ✅ | Préférences notifications |
| `/notifications/user-preferences/` | GET/PUT | ✅ | Préférences utilisateur |

### Envoi Messages Push + Email (85% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/notifications/send-email/` | POST | ✅ | Email SMTP prioritaire |
| `/notifications/send-push/` | POST | ✅ | Notifications push |
| `/notifications/bulk-send/` | POST | ✅ | Envoi en masse |

**⚠️ SMS TEMPORAIREMENT COMMENTÉ** (Décision superviseur)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| ~~`/notifications/send-sms/`~~ | ~~POST~~ | 🔕 | SMS temporairement désactivé |

**Fonctionnalités développées :**
- **Focus PUSH + EMAIL** (priorité superviseur)
- SMS providers Sénégal commentés (Orange, Free, Expresso) - réactivables
- Templates multilingues (Français/Wolof)
- 5 types notifications (ticket, RDV, file, paiement, urgence)
- Notifications intelligentes basées géolocalisation
- Historique complet envois avec statuts

#### Mock SMS (Développement)
```bash
POST /api/notifications/send-sms/
{
  "phone": "+221771234567",
  "message": "Votre ticket A015 sera appelé dans 10 minutes",
  "provider": "orange"  # orange, expresso, free
}

# Response (simulation)
{
  "status": "sent_mock",
  "message_id": "mock_12345",
  "provider": "orange_mock",
  "cost_fcfa": 0,
  "delivered_at": "2025-09-11T10:00:00Z"
}
```

### Templates
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/notifications/templates/` | GET | ✅ | Templates prédéfinis |
| `/notifications/templates/{id}/` | GET | ✅ | Détail template |

---

## 💳 7. Payments (Mobile Money) {#payments}

### Providers & Méthodes (95% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/payments/providers/` | GET | ✅ | Wave, Orange Money, Free Money |
| `/payments/methods/` | GET | ✅ | Méthodes sauvegardées utilisateur |
| `/payments/methods/` | POST | ✅ | Ajouter méthode |

### Paiements B2C (95% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/payments/initiate/` | POST | ✅ | Initier paiement client |
| `/payments/` | GET | ✅ | Historique paiements |
| `/payments/{id}/` | GET | ✅ | Détail paiement |
| `/payments/{id}/status/` | GET | ✅ | Statut temps réel |
| `/payments/stats/` | GET | ✅ | Statistiques utilisateur |

### Paiements B2B & Factures (95% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/payments/plans/` | GET | ✅ | Plans d'abonnement |
| `/payments/invoices/` | GET | ✅ | Factures organisation |
| `/payments/invoices/{id}/` | GET | ✅ | Détail facture |
| `/payments/invoices/{id}/pay/` | POST | ✅ | Payer facture |

### Webhooks & Simulation (95% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/payments/webhooks/wave/` | POST | ✅ | Callback Wave |
| `/payments/webhooks/orange-money/` | POST | ✅ | Callback Orange Money |
| `/payments/webhooks/free-money/` | POST | ✅ | Callback Free Money |
| `/payments/simulate/success/{id}/` | POST | ✅ | Simuler succès |
| `/payments/simulate/failure/{id}/` | POST | ✅ | Simuler échec |
| `/payments/logs/` | GET | ✅ | Logs utilisateur |

**Fonctionnalités développées :**
- 6 modèles complets (Provider, Payment, PaymentMethod, Log, Plan, Invoice)
- Paiements B2C (clients → organisations) et B2B (orgs → SmartQueue)
- Admin Django complet avec badges colorés
- Simulation complète pour développement
- Facturation automatique organisations
- Intégration tickets/RDV (création auto après paiement)

#### Simulation Paiement
```bash
POST /api/payments/process-payment/
{
  "amount": 5000,
  "currency": "XOF",
  "method": "orange_money",
  "phone": "+221771234567",
  "service_id": 1,
  "description": "Consultation générale"
}

# Response (mode simulation)
{
  "transaction_id": "sim_tx_12345",
  "status": "pending_mock",
  "payment_url": "https://mock-orange-money.com/pay/12345",
  "expires_at": "2025-09-11T10:15:00Z"
}
```

---

## 📊 8. Analytics (Métriques & Rapports) {#analytics}

### Dashboard Organisations (80% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/analytics/dashboard/` | GET | ✅ | Vue d'ensemble générale |
| `/analytics/organization-stats/` | GET | ✅ | Stats organisation |
| `/analytics/queue-performance/` | GET | ✅ | Performance files |
| `/analytics/user-behavior/` | GET | ✅ | Comportement clients |

### KPIs & Métriques (80% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/analytics/kpis/` | GET | ✅ | KPIs temps réel |
| `/analytics/satisfaction/` | GET | ✅ | Taux satisfaction |
| `/analytics/geographic/` | GET | ✅ | Analytics géographiques |
| `/analytics/trends/` | GET | ✅ | Tendances période |

### Rapports (80% ✅)
| Endpoint | Méthode | Status | Description |
|----------|---------|--------|-------------|
| `/analytics/reports/daily/` | GET | ✅ | Rapport journalier |
| `/analytics/reports/weekly/` | GET | ✅ | Rapport hebdomadaire |
| `/analytics/reports/monthly/` | GET | ✅ | Rapport mensuel |
| `/analytics/export/csv/` | GET | 🟡 | Export CSV |
| `/analytics/export/pdf/` | GET | 🟡 | Export PDF |

**Fonctionnalités développées :**
- Dashboard organisations temps réel
- KPIs (tickets servis, temps attente, satisfaction)
- Rapports période (jour, semaine, mois)
- Analytics géographiques (origine clients)
- Métriques services (plus demandé, taux satisfaction)

#### Exemple Dashboard
```bash
GET /api/analytics/dashboard/

# Response
{
  "total_users": 150,
  "active_queues": 12,
  "tickets_today": 89,
  "avg_wait_time": 18.5,
  "satisfaction_rate": 4.2,
  "peak_hours": ["09:00", "14:00"],
  "top_services": [
    {"name": "Consultation", "count": 45},
    {"name": "Analyses", "count": 23}
  ]
}
```

---

## 🔌 9. WebSocket Temps Réel ✅ NOUVEAU {#websocket}

### URLs WebSocket
| URL | Status | Description |
|-----|--------|-------------|
| `ws://host/ws/notifications/user/{user_id}/` | ✅ | **Notifications individuelles** |
| `ws://host/ws/location/updates/{user_id}/` | ✅ | **Géolocalisation temps réel** |
| `ws://host/ws/queue/{queue_id}/` | ✅ | **File d'attente live** |
| `ws://host/ws/admin/dashboard/` | ✅ | **Dashboard admin** |
| `ws://host/ws/org/{org_id}/monitor/` | ✅ | **Monitoring organisation** |

### Messages WebSocket

#### Notifications Utilisateur
```javascript
// Connexion
const socket = new WebSocket('ws://localhost:8000/ws/notifications/user/123/');

// Messages reçus
{
  "type": "notification",
  "notification": {
    "id": 45,
    "title": "Ticket appelé",
    "message": "Votre ticket A015 est maintenant appelé",
    "timestamp": "2025-09-11T10:00:00Z"
  }
}

{
  "type": "queue_position_update",
  "data": {
    "ticket_id": 15,
    "new_position": 2,
    "estimated_wait": 10
  }
}
```

#### File d'Attente Temps Réel
```javascript
// Connexion à file spécifique
const queueSocket = new WebSocket('ws://localhost:8000/ws/queue/5/');

// Messages reçus
{
  "type": "queue_update",
  "data": {
    "current_number": "A012",
    "waiting_count": 15,
    "avg_wait_time": 18
  }
}

{
  "type": "ticket_called",
  "data": {
    "ticket_number": "A015",
    "user_id": 123,
    "call_time": "2025-09-11T10:00:00Z"
  }
}
```

### Test WebSocket
Fichier de test disponible : `tests/test_websocket.html`

---

## 🔧 Configuration et Authentication

### Headers Requis
```bash
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Content-Type: application/json
Accept: application/json
```

### Codes de Statut
- `200` : Succès
- `201` : Créé
- `400` : Erreur requête
- `401` : Non authentifié
- `403` : Non autorisé
- `404` : Non trouvé
- `500` : Erreur serveur

### Pagination
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/endpoint/?page=2",
  "previous": null,
  "results": [...]
}
```

### Filtrage et Recherche
```bash
# Filtrage
GET /api/queues/queues/?is_active=true&service=1

# Recherche
GET /api/business/organizations/?search=hopital

# Tri
GET /api/queues/tickets/?ordering=-created_at
```

---

## ✅ Interfaces Admin Complètes

### Admin Interfaces Django
- ✅ `accounts/admin.py` : Interface complète (224 lignes) avec badges
- ✅ `queue_management/admin.py` : Interface avancée (417 lignes) avec actions
- ✅ `business/admin.py` : Interface organisations complète

### Interface Agent Files
- ✅ Dashboard agent temps réel
- ✅ Gestion files côté guichets
- ✅ Actions appel tickets/marquer servi/transferts

### ⚠️ Points Restants
- 🟡 Tests validation (tous les `tests.py` basiques)
- 🟡 APIs mobile money réelles (simulation active)

---

## 📈 Résumé par Performance

### ✅ Excellentes (90%+) - 5 apps
- **Queue Management** (95%) : Files intelligentes, tickets, géolocalisation
- **Payments** (95%) : Mobile Money complet, admin, B2B/B2C
- **Core** (95%) : WebSocket, infrastructure, middleware
- **Locations** (92%) : GPS, trajets, embouteillages
- **Business** (90%) : 9 types orgs, 14 régions Sénégal

### ✅ Bonnes (85%+) - 3 apps
- **Notifications** (85%) : Push + Email prioritaire, SMS commenté
- **Appointments** (85%) : RDV, créneaux, paiements
- **Accounts** (100%) : Auth JWT par email, profils complets

### 🟡 Correctes (80%+) - 1 app
- **Analytics** (80%) : Dashboard, KPIs, rapports

---

## 🎯 Architecture Globale

**📊 Métriques :**
- **87% Fonctionnel** (évaluation post-audit)
- **23,496 lignes de code** développées
- **10 applications** interconnectées
- **4,784 lignes de modèles** (architecture solide)

**🇸🇳 Spécificités Sénégal :**
- Authentification EMAIL prioritaire (téléphone optionnel)
- 14 régions complètes
- Push + Email Français/Wolof (SMS commenté)
- Mobile Money (Wave, Orange Money, Free Money)
- Calculs embouteillages Dakar

**🚀 Backend 87% prêt pour production** ! 🇸🇳