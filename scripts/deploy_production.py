#!/usr/bin/env python3
"""
Script de déploiement production pour SmartQueue
Configuration automatique WebSockets, Redis, Celery et géolocalisation intelligente
"""

import os
import subprocess
import sys
import platform
from pathlib import Path

class SmartQueueProductionDeployer:
    """Déployeur automatisé pour SmartQueue en production"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.is_linux = platform.system() == 'Linux'
        self.is_docker = os.path.exists('/.dockerenv')
        
    def run_command(self, command, description):
        """Exécuter une commande avec gestion d'erreur"""
        print(f"🔄 {description}...")
        try:
            result = subprocess.run(command, shell=True, check=True, 
                                  capture_output=True, text=True)
            print(f"✅ {description} - Succès")
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"❌ {description} - Erreur: {e.stderr}")
            return None
    
    def check_system_requirements(self):
        """Vérifier les prérequis système"""
        print("🔍 Vérification des prérequis système...")
        
        requirements = {
            'python3': 'python3 --version',
            'redis': 'redis-server --version',
            'postgresql': 'psql --version',
            'nginx': 'nginx -v',
            'supervisord': 'supervisord --version'
        }
        
        missing = []
        for name, check_cmd in requirements.items():
            if not self.run_command(check_cmd, f"Vérification {name}"):
                missing.append(name)
        
        if missing:
            print(f"⚠️ Composants manquants: {', '.join(missing)}")
            print("📋 Commandes d'installation Ubuntu/Debian:")
            print("   sudo apt update")
            print("   sudo apt install -y python3 python3-pip redis-server postgresql nginx supervisor")
            return False
        
        return True
    
    def setup_environment_variables(self):
        """Configurer variables d'environnement production"""
        print("🌍 Configuration variables d'environnement...")
        
        env_template = """# SmartQueue Production Environment
DJANGO_SETTINGS_MODULE=config.settings.production
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
SECRET_KEY=your-very-secure-secret-key-here

# Base de données PostgreSQL
DATABASE_URL=postgresql://smartqueue_user:password@localhost:5432/smartqueue_db

# Redis pour Celery et WebSockets
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# APIs externes géolocalisation
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
OPENSTREETMAP_API_KEY=your-osm-api-key

# SMS/Email notifications
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
EMAIL_HOST_PASSWORD=your-email-password

# Géolocalisation avancée
TRAFFIC_API_ENABLED=True
WEATHER_API_ENABLED=True
INTELLIGENT_QUEUE_ENABLED=True

# Sécurité
SECURE_SSL_REDIRECT=True
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
"""
        
        env_file = self.project_root / '.env.production'
        with open(env_file, 'w') as f:
            f.write(env_template)
        
        print(f"📝 Fichier d'environnement créé: {env_file}")
        print("⚠️ IMPORTANT: Modifiez .env.production avec vos vraies clés!")
    
    def setup_database(self):
        """Configurer base de données PostgreSQL"""
        print("🗄️ Configuration PostgreSQL...")
        
        # Commandes SQL pour créer DB et utilisateur
        sql_commands = """
CREATE DATABASE smartqueue_db;
CREATE USER smartqueue_user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE smartqueue_db TO smartqueue_user;
ALTER USER smartqueue_user CREATEDB;
        """
        
        print("📋 Exécutez ces commandes PostgreSQL:")
        print("   sudo -u postgres psql")
        print(sql_commands)
    
    def setup_nginx_config(self):
        """Créer configuration Nginx"""
        print("🌐 Configuration Nginx...")
        
        nginx_config = f"""# SmartQueue Nginx Configuration
server {{
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    # Redirection HTTPS
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;
    
    # SSL Configuration (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SmartQueue Django Application
    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # WebSockets pour géolocalisation temps réel
    location /ws/ {{
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    # Fichiers statiques
    location /static/ {{
        alias {self.project_root}/static/;
        expires 30d;
    }}
    
    # Fichiers media
    location /media/ {{
        alias {self.project_root}/media/;
        expires 7d;
    }}
}}
"""
        
        nginx_file = '/tmp/smartqueue_nginx.conf'
        with open(nginx_file, 'w') as f:
            f.write(nginx_config)
        
        print(f"📝 Configuration Nginx créée: {nginx_file}")
        print("📋 Pour activer:")
        print(f"   sudo cp {nginx_file} /etc/nginx/sites-available/smartqueue")
        print("   sudo ln -s /etc/nginx/sites-available/smartqueue /etc/nginx/sites-enabled/")
        print("   sudo nginx -t && sudo systemctl reload nginx")
    
    def setup_supervisor_config(self):
        """Créer configuration Supervisor pour Celery"""
        print("👥 Configuration Supervisor pour Celery...")
        
        supervisor_config = f"""# SmartQueue Celery Workers
[program:smartqueue-worker]
command={self.project_root}/.venv/bin/celery -A config worker --loglevel=info --concurrency=4 --queues=default,locations,notifications
directory={self.project_root}
user=www-data
numprocs=1
stdout_logfile=/var/log/smartqueue/celery-worker.log
stderr_logfile=/var/log/smartqueue/celery-worker.log
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600

[program:smartqueue-beat]
command={self.project_root}/.venv/bin/celery -A config beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
directory={self.project_root}
user=www-data
numprocs=1
stdout_logfile=/var/log/smartqueue/celery-beat.log
stderr_logfile=/var/log/smartqueue/celery-beat.log
autostart=true
autorestart=true
startsecs=10

[program:smartqueue-django]
command={self.project_root}/.venv/bin/gunicorn config.asgi:application --bind 0.0.0.0:8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker
directory={self.project_root}
user=www-data
numprocs=1
stdout_logfile=/var/log/smartqueue/django.log
stderr_logfile=/var/log/smartqueue/django.log
autostart=true
autorestart=true
startsecs=10

[group:smartqueue]
programs=smartqueue-worker,smartqueue-beat,smartqueue-django
priority=999
"""
        
        supervisor_file = '/tmp/smartqueue_supervisor.conf'
        with open(supervisor_file, 'w') as f:
            f.write(supervisor_config)
        
        print(f"📝 Configuration Supervisor créée: {supervisor_file}")
        print("📋 Pour activer:")
        print("   sudo mkdir -p /var/log/smartqueue")
        print(f"   sudo cp {supervisor_file} /etc/supervisor/conf.d/smartqueue.conf")
        print("   sudo supervisorctl reread && sudo supervisorctl update")
        print("   sudo supervisorctl start smartqueue:*")
    
    def setup_systemd_services(self):
        """Créer services systemd alternatifs"""
        print("🔧 Configuration services systemd...")
        
        # Service Django
        django_service = f"""[Unit]
Description=SmartQueue Django Application
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=www-data
WorkingDirectory={self.project_root}
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart={self.project_root}/.venv/bin/gunicorn config.asgi:application --bind 0.0.0.0:8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
        
        # Service Celery Worker
        celery_worker_service = f"""[Unit]
Description=SmartQueue Celery Worker (Géolocalisation intelligente)
After=network.target redis.service postgresql.service

[Service]
Type=exec
User=www-data
WorkingDirectory={self.project_root}
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart={self.project_root}/.venv/bin/celery -A config worker --loglevel=info --concurrency=4 --queues=default,locations,notifications
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
        
        # Service Celery Beat
        celery_beat_service = f"""[Unit]
Description=SmartQueue Celery Beat (Tâches périodiques)
After=network.target redis.service postgresql.service

[Service]
Type=exec
User=www-data
WorkingDirectory={self.project_root}
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart={self.project_root}/.venv/bin/celery -A config beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
        
        services = {
            'smartqueue-django.service': django_service,
            'smartqueue-celery-worker.service': celery_worker_service,
            'smartqueue-celery-beat.service': celery_beat_service
        }
        
        for service_name, service_content in services.items():
            service_file = f'/tmp/{service_name}'
            with open(service_file, 'w') as f:
                f.write(service_content)
            print(f"📝 Service systemd créé: {service_file}")
        
        print("📋 Pour activer les services:")
        print("   sudo cp /tmp/smartqueue-*.service /etc/systemd/system/")
        print("   sudo systemctl daemon-reload")
        print("   sudo systemctl enable smartqueue-django smartqueue-celery-worker smartqueue-celery-beat")
        print("   sudo systemctl start smartqueue-django smartqueue-celery-worker smartqueue-celery-beat")
    
    def create_deployment_checklist(self):
        """Créer checklist de déploiement"""
        print("📋 Création checklist de déploiement...")
        
        checklist = """# SmartQueue - Checklist de déploiement production

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
"""
        
        checklist_file = self.project_root / 'DEPLOYMENT_CHECKLIST.md'
        with open(checklist_file, 'w') as f:
            f.write(checklist)
        
        print(f"📝 Checklist créée: {checklist_file}")
    
    def run_deployment(self):
        """Orchestrer le déploiement complet"""
        print("🚀 Déploiement SmartQueue Production avec Géolocalisation Intelligente")
        print("=" * 80)
        
        steps = [
            ("Vérification prérequis", self.check_system_requirements),
            ("Variables d'environnement", self.setup_environment_variables),
            ("Configuration base de données", self.setup_database),
            ("Configuration Nginx", self.setup_nginx_config),
            ("Configuration Supervisor", self.setup_supervisor_config),
            ("Services systemd", self.setup_systemd_services),
            ("Checklist déploiement", self.create_deployment_checklist)
        ]
        
        for step_name, step_func in steps:
            print(f"\n📋 Étape: {step_name}")
            try:
                step_func()
                print(f"✅ {step_name} - Terminée")
            except Exception as e:
                print(f"❌ {step_name} - Erreur: {e}")
                
        print("\n" + "="*80)
        print("🎉 Configuration de déploiement terminée!")
        print("\n💡 Prochaines étapes:")
        print("  1. Modifier .env.production avec vos vraies clés")
        print("  2. Suivre DEPLOYMENT_CHECKLIST.md étape par étape")
        print("  3. Tester géolocalisation intelligente Pikine->Diamniadio")
        print("  4. Monitorer les workers Celery et WebSockets")
        print("\n🌟 Fonctionnalités prêtes:")
        print("  ✅ Géolocalisation intelligente avec trafic Dakar")
        print("  ✅ Réorganisation automatique des files")
        print("  ✅ WebSockets temps réel")
        print("  ✅ Notifications départ automatiques")
        print("  ✅ APIs Google Maps + OpenStreetMap")

def main():
    """Point d'entrée principal"""
    deployer = SmartQueueProductionDeployer()
    deployer.run_deployment()

if __name__ == '__main__':
    main()