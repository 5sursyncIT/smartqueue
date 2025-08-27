# SmartQueue - Checklist de déploiement production

## 1. Prérequis système ✅
- [ ] Ubuntu/Debian 20.04+
- [ ] Python 3.8+
- [ ] PostgreSQL 13+
- [ ] Redis 6+
- [ ] Nginx 1.18+
- [ ] Supervisor ou systemd

## 2. Configuration base de données
- [ ] Créer DB PostgreSQL: `smartqueue_db`
- [ ] Créer utilisateur: `smartqueue_user`
- [ ] Configurer mot de passe sécurisé
- [ ] Tester connexion DB

## 3. Variables d'environnement
- [ ] Copier .env.production
- [ ] Configurer SECRET_KEY sécurisée
- [ ] Configurer DATABASE_URL
- [ ] Configurer REDIS_URL
- [ ] Ajouter GOOGLE_MAPS_API_KEY
- [ ] Configurer ALLOWED_HOSTS

## 4. Géolocalisation intelligente
- [ ] Clé API Google Maps configurée
- [ ] APIs OpenStreetMap configurées (optionnel)
- [ ] Test calcul de trajet Pikine->Diamniadio
- [ ] Vérification facteurs de trafic Dakar

## 5. Installation Python
```bash
# Environnement virtuel
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Dépendances géolocalisation
pip install geopy googlemaps openrouteservice

# Production
pip install gunicorn uvicorn psycopg2-binary
```

## 6. Migrations Django
```bash
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py load_senegal_data
```

## 7. Tests fonctionnels
```bash
python manage.py test_intelligent_geolocation
python manage.py check --deploy
```

## 8. Services
- [ ] Nginx configuré et démarré
- [ ] Redis démarré: `sudo systemctl start redis`
- [ ] PostgreSQL démarré: `sudo systemctl start postgresql`
- [ ] Services Celery configurés (Supervisor/systemd)
- [ ] Django/ASGI démarré avec WebSockets

## 9. SSL/HTTPS
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 10. Monitoring
- [ ] Logs configurés: /var/log/smartqueue/
- [ ] Monitoring Celery tasks
- [ ] Monitoring WebSockets connexions
- [ ] Alertes trafic API quotas

## 11. Tests production
- [ ] Test prise de ticket client
- [ ] Test géolocalisation temps réel  
- [ ] Test calcul intelligent temps trajet
- [ ] Test réorganisation automatique files
- [ ] Test notifications départ
- [ ] Test WebSockets temps réel

## 12. Sécurité
- [ ] Firewall configuré (ports 80, 443, 22)
- [ ] Utilisateur www-data configuré
- [ ] Permissions fichiers vérifiées
- [ ] Base de données accessible uniquement en local
- [ ] Redis protégé par mot de passe
- [ ] Clés API sécurisées

## 13. Performance
- [ ] Cache Redis configuré
- [ ] Static files CDN (optionnel)
- [ ] Database indexing optimisé
- [ ] Celery workers dimensionnés (4+ workers)

## 14. Sauvegarde
- [ ] Sauvegarde quotidienne PostgreSQL
- [ ] Sauvegarde fichiers media
- [ ] Plan de restauration testé

## 15. Documentation
- [ ] URLs API documentées
- [ ] WebSockets endpoints documentés
- [ ] Guide utilisateur géolocalisation
- [ ] Procédures d'urgence

## Commandes utiles production

### Supervision services
```bash
sudo supervisorctl status smartqueue:*
sudo systemctl status smartqueue-*
```

### Monitoring Celery
```bash
celery -A config inspect active
celery -A config flower  # Interface web monitoring
```

### Logs
```bash
tail -f /var/log/smartqueue/celery-worker.log
tail -f /var/log/nginx/access.log
```

### Base de données
```bash
sudo -u postgres psql smartqueue_db
```

🎯 **Objectif**: Système SmartQueue avec géolocalisation intelligente opérationnel 24/7
📍 **Cas d'usage**: Client Pikine -> Banque Diamniadio avec réorganisation automatique
🚀 **Performance**: <3s temps de réponse, 99.9% uptime
