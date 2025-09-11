# SmartQueue Backend - Sénégal 🇸🇳

## Vue d'ensemble
Backend Django REST API pour système de gestion des files d'attente virtuelles au Sénégal.

**Status Global** : ✅ 89.7% Fonctionnel | **Prêt pour révision superviseur**

## 🚀 Fonctionnalités Principales

- **Authentification JWT** - Login/Register sécurisés
- **Files d'Attente Virtuelles** - Système tickets digitaux complet
- **Rendez-vous** - 240 créneaux automatiques (Lun-Ven 9h-17h)
- **WebSocket Temps Réel** - Notifications instantanées  
- **Géolocalisation Sénégal** - Calcul trajets intelligents
- **Mock SMS/Paiements** - Simulation pour développement

## 🔧 Technologies

- **Framework** : Django 4.2 + Django REST Framework
- **Authentification** : JWT tokens
- **Temps réel** : Django Channels + WebSocket  
- **Cache** : Redis (prod) / InMemory (dev)
- **Base** : SQLite (dev) → PostgreSQL (prod)

## 🛠️ Installation Rapide

```bash
# Setup
git clone <repo>
cd smartqueue_backend
python -m venv venv
source venv/bin/activate

# Installation
pip install -r requirements.txt
python manage.py migrate

# Données de test
python tests/scripts/create_appointment_slots.py

# Démarrer
python manage.py runserver
```

## 📊 État Endpoints

### ✅ Production Ready (89.7%)
- **Core** : Auth, Users, Organizations, Services (100%)
- **Queue Management** : Files + Tickets (100%)  
- **Appointments** : Rendez-vous (100%) *récemment fixé*
- **WebSocket** : Notifications temps réel (100%) *nouveau*
- **Géolocalisation** : Trajet + communes Sénégal (85%)

### 🟡 En Développement  
- **Notifications** : Mock SMS (70%)
- **Paiements** : Orange Money/Wave simulés (60%)
- **Analytics** : Données simulées (80%)

**Détails** : Voir [BACKEND_STATUS.md](BACKEND_STATUS.md)

## 🔌 WebSocket Temps Réel

### URLs Disponibles
```
ws://localhost:8000/ws/notifications/user/{user_id}/
ws://localhost:8000/ws/queue/{queue_id}/
ws://localhost:8000/ws/admin/dashboard/
```

**Test** : Ouvrir `tests/test_websocket.html` dans navigateur

## 📚 Documentation

- **API Complète** : [ENDPOINTS.md](ENDPOINTS.md)
- **Swagger UI** : http://localhost:8000/api/schema/swagger-ui/
- **État Technique** : [BACKEND_STATUS.md](BACKEND_STATUS.md)

## 📁 Structure

```
apps/
├── core/              # WebSocket + utilitaires
├── accounts/          # Auth + utilisateurs
├── business/          # Orgs + services  
├── queue_management/  # Files + tickets
├── appointments/      # Rendez-vous
├── locations/         # Géolocalisation Sénégal
├── notifications/     # SMS + push
├── payments/          # Orange Money + Wave
└── analytics/         # Stats + rapports

config/
├── settings/          # Par environnement
├── asgi.py           # WebSocket
└── celery.py         # Tâches async

tests/
├── scripts/          # Génération données
└── test_websocket.html
```

## 🌍 Spécificités Sénégal

- **Fuseau** : Africa/Dakar
- **Langues** : FR/Wolof/EN
- **Paiements** : Orange Money, Wave, Free Money
- **SMS** : Orange/Expresso APIs

## 🧪 Test Rapides

```bash
# Test auth
curl -X POST http://localhost:8000/api/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"login":"admin","password":"admin123"}'

# Test appointments (240 créneaux)
curl http://localhost:8000/api/appointments/appointment-slots/
```

## 🚀 Déploiement

### Dev → Production
1. SQLite → PostgreSQL
2. InMemory → Redis serveur
3. Mock SMS → APIs réelles
4. Gunicorn + Nginx

### Variables Env
```
DEBUG=False
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=production-key
```

## 📈 Récents Accomplissements  

- ✅ **Appointments fixés** : 28% → 100% 
- ✅ **WebSocket activé** : 0% → 100%
- ✅ **Mock providers** : Notifications opérationnelles
- ✅ **Architecture propre** : Apps restructurées

## 🔄 Prochaines Étapes

**Pour Production** :
1. Serveur Redis
2. APIs SMS réelles  
3. PostgreSQL
4. Déploiement cloud

---

**Version** : 1.0.0 | **Contact** : dev@smartqueue.sn  
**Dernière MàJ** : 11/09/2025