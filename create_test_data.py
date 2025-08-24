#!/usr/bin/env python3
"""
Script pour créer des données de test SmartQueue Sénégal
Crée des organisations, services, files d'attente et utilisateurs réalistes
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Configuration Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

# Imports des modèles
from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.services.models import Service, ServiceCategory
from apps.queues.models import Queue
from apps.tickets.models import Ticket
from apps.analytics.models import (
    OrganizationMetrics, ServiceMetrics, QueueMetrics, CustomerSatisfaction
)
from decimal import Decimal
import random

def create_analytics_data(organizations, services, queues, clients):
    """Crée des données analytics de test réalistes"""
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    last_week = today - timedelta(days=7)
    
    print("📊 Création des métriques d'organisations...")
    
    # Métriques d'organisations pour les 7 derniers jours
    for org in organizations:
        for i in range(7):
            date = today - timedelta(days=i)
            
            # Générer des données réalistes selon le type d'organisation
            if org.type == 'bank':
                tickets_issued = random.randint(30, 80)
                tickets_served = random.randint(25, tickets_issued)
                avg_wait = random.randint(15, 45)
                revenue = Decimal(random.uniform(50000, 150000))
            elif org.type == 'hospital':
                tickets_issued = random.randint(50, 120)
                tickets_served = random.randint(40, tickets_issued)
                avg_wait = random.randint(30, 90)
                revenue = Decimal(random.uniform(100000, 300000))
            else:  # government
                tickets_issued = random.randint(20, 60)
                tickets_served = random.randint(15, tickets_issued)
                avg_wait = random.randint(45, 120)
                revenue = Decimal(0)  # Pas de revenus pour administration
            
            metric, created = OrganizationMetrics.objects.get_or_create(
                organization=org,
                date=date,
                defaults={
                    'tickets_issued': tickets_issued,
                    'tickets_served': tickets_served,
                    'tickets_cancelled': random.randint(0, 5),
                    'tickets_expired': random.randint(0, 3),
                    'tickets_no_show': random.randint(0, 2),
                    'appointments_created': random.randint(10, 30) if org.type == 'hospital' else 0,
                    'appointments_completed': random.randint(8, 25) if org.type == 'hospital' else 0,
                    'appointments_cancelled': random.randint(0, 3) if org.type == 'hospital' else 0,
                    'avg_wait_time': avg_wait,
                    'max_wait_time': avg_wait + random.randint(10, 30),
                    'avg_service_time': random.randint(5, 20),
                    'total_ratings': random.randint(5, 20),
                    'avg_rating': Decimal(random.uniform(3.5, 4.8)),
                    'peak_hour_start': timezone.now().time().replace(hour=10, minute=0),
                    'peak_hour_end': timezone.now().time().replace(hour=12, minute=0),
                    'max_concurrent_customers': random.randint(15, 35),
                    'total_revenue': revenue
                }
            )
            if created:
                print(f"✅ Métrique {org.name} - {date}")
    
    print("📋 Création des métriques de services...")
    
    # Métriques de services
    for service in services:
        for i in range(7):
            date = today - timedelta(days=i)
            
            tickets = random.randint(10, 30)
            served = random.randint(8, tickets)
            
            metric, created = ServiceMetrics.objects.get_or_create(
                service=service,
                organization=service.organization,
                date=date,
                defaults={
                    'tickets_issued': tickets,
                    'tickets_served': served,
                    'tickets_cancelled': random.randint(0, 3),
                    'total_wait_time': served * random.randint(10, 40),
                    'total_service_time': served * random.randint(5, 15),
                    'revenue': Decimal(served * (service.cost or 0)),
                    'total_ratings': random.randint(2, 8),
                    'total_rating_score': random.randint(15, 35)
                }
            )
            if created:
                print(f"✅ Métrique service {service.name} - {date}")
    
    print("📊 Création des métriques de files d'attente...")
    
    # Métriques de files d'attente (horaires pour aujourd'hui)
    for queue in queues:
        for hour in range(8, 18):  # 8h à 18h
            timestamp = timezone.now().replace(hour=hour, minute=0, second=0, microsecond=0)
            
            metric, created = QueueMetrics.objects.get_or_create(
                queue=queue,
                timestamp=timestamp,
                defaults={
                    'waiting_customers': random.randint(0, 15),
                    'current_wait_time': random.randint(5, 60),
                    'tickets_issued_hour': random.randint(3, 12),
                    'tickets_served_hour': random.randint(2, 10),
                    'queue_status': random.choice(['active', 'busy', 'slow'])
                }
            )
            if created and hour % 2 == 0:  # Log seulement quelques heures pour éviter le spam
                print(f"✅ Métrique file {queue.name} - {hour}h")
    
    print("⭐ Création des évaluations de satisfaction...")
    
    # Évaluations de satisfaction
    for i in range(20):  # 20 évaluations
        client = random.choice(clients)
        service = random.choice(services)
        
        rating = random.choices([1, 2, 3, 4, 5], weights=[2, 3, 10, 30, 15])[0]  # Plus de bonnes notes
        
        comments = [
            "Service rapide et efficace",
            "Temps d'attente un peu long mais personnel aimable",
            "Très satisfait de l'accueil",
            "Pourrait être amélioré",
            "Excellent service, je recommande",
            "",  # Pas de commentaire
            "Personnel compétent et disponible"
        ]
        
        satisfaction, created = CustomerSatisfaction.objects.get_or_create(
            customer=client,
            organization=service.organization,
            service=service,
            defaults={
                'rating': rating,
                'comment': random.choice(comments),
                'wait_time_rating': random.randint(max(1, rating-1), min(5, rating+1)),
                'service_quality_rating': random.randint(max(1, rating-1), min(5, rating+1)),
                'staff_friendliness_rating': random.randint(max(1, rating-1), min(5, rating+1)),
                'created_at': timezone.now() - timedelta(days=random.randint(0, 7))
            }
        )
        if created:
            print(f"✅ Évaluation {rating}/5 par {client.first_name}")
    
    print(f"📊 Données analytics créées :")
    print(f"   - {OrganizationMetrics.objects.count()} métriques d'organisations")
    print(f"   - {ServiceMetrics.objects.count()} métriques de services")
    print(f"   - {QueueMetrics.objects.count()} métriques de files")
    print(f"   - {CustomerSatisfaction.objects.count()} évaluations de satisfaction")


def create_test_data():
    """Crée des données de test réalistes pour SmartQueue Sénégal"""
    
    print("🚀 Création des données de test SmartQueue Sénégal...")
    
    # ==========================================
    # 1. CRÉER DES UTILISATEURS
    # ==========================================
    print("\n👥 Création des utilisateurs...")
    
    # Super Admin SmartQueue
    super_admin, created = User.objects.get_or_create(
        phone_number='+221770001234',
        defaults={
            'username': 'admin_smartqueue',
            'first_name': 'Admin',
            'last_name': 'SmartQueue',
            'email': 'admin@smartqueue.sn',
            'user_type': 'super_admin',
            'is_active': True,
            'preferred_language': 'fr'
        }
    )
    if created:
        super_admin.set_password('admin123')
        super_admin.save()
        print(f"✅ Super Admin créé: {super_admin.get_full_name()}")
    
    # Clients
    clients_data = [
        {'first_name': 'Aminata', 'last_name': 'Diop', 'phone': '+221770123456'},
        {'first_name': 'Moussa', 'last_name': 'Fall', 'phone': '+221775234567'},
        {'first_name': 'Fatou', 'last_name': 'Ndiaye', 'phone': '+221776345678'},
        {'first_name': 'Omar', 'last_name': 'Seck', 'phone': '+221777456789'},
        {'first_name': 'Aissatou', 'last_name': 'Ba', 'phone': '+221778567890'},
    ]
    
    clients = []
    for client_data in clients_data:
        client, created = User.objects.get_or_create(
            phone_number=client_data['phone'],
            defaults={
                'username': f"{client_data['first_name'].lower()}_{client_data['last_name'].lower()}",
                'first_name': client_data['first_name'],
                'last_name': client_data['last_name'],
                'email': f"{client_data['first_name'].lower()}@example.sn",
                'user_type': 'customer',
                'is_active': True,
                'preferred_language': 'fr'
            }
        )
        if created:
            client.set_password('client123')
            client.save()
        clients.append(client)
        print(f"✅ Client créé: {client.get_full_name()}")
    
    # ==========================================
    # 2. CRÉER DES ORGANISATIONS
    # ==========================================
    print("\n🏢 Création des organisations...")
    
    # BHS - Banque de l'Habitat du Sénégal
    bhs, created = Organization.objects.get_or_create(
        name="Banque de l'Habitat du Sénégal",
        defaults={
            'trade_name': 'BHS',
            'type': 'bank',
            'email': 'contact@bhs.sn',
            'phone_number': '+221338234567',
            'address': 'Avenue Léopold Sédar Senghor, Dakar',
            'city': 'Dakar',
            'region': 'dakar',
            'latitude': 14.6928,
            'longitude': -17.4441,
            'subscription_plan': 'business',
            'status': 'active',
            'is_active': True,
            'supported_languages': ['fr', 'wo'],
            'default_language': 'fr'
        }
    )
    if created:
        print(f"✅ Banque créée: {bhs.name}")
    
    # Hôpital Principal de Dakar
    hopital, created = Organization.objects.get_or_create(
        name="Hôpital Principal de Dakar",
        defaults={
            'trade_name': 'HPD',
            'type': 'hospital',
            'email': 'contact@hopital-dakar.sn',
            'phone_number': '+221338567890',
            'address': 'Avenue Nelson Mandela, Dakar',
            'city': 'Dakar', 
            'region': 'dakar',
            'latitude': 14.7167,
            'longitude': -17.4677,
            'subscription_plan': 'business',
            'status': 'active',
            'is_active': True,
            'supported_languages': ['fr', 'wo'],
            'default_language': 'fr'
        }
    )
    if created:
        print(f"✅ Hôpital créé: {hopital.name}")
    
    # Préfecture de Thiès
    prefecture, created = Organization.objects.get_or_create(
        name="Préfecture de Thiès",
        defaults={
            'trade_name': 'Préfecture Thiès',
            'type': 'government',
            'email': 'contact@prefecture-thies.sn',
            'phone_number': '+221339123456',
            'address': 'Centre-ville, Thiès',
            'city': 'Thiès',
            'region': 'thies',
            'latitude': 14.7886,
            'longitude': -16.9246,
            'subscription_plan': 'starter',
            'status': 'active',
            'is_active': True,
            'supported_languages': ['fr', 'wo'],
            'default_language': 'fr'
        }
    )
    if created:
        print(f"✅ Préfecture créée: {prefecture.name}")
    
    # ==========================================
    # 3. CRÉER DES CATÉGORIES DE SERVICES
    # ==========================================
    print("\n⚙️ Création des catégories de services...")
    
    categories_data = [
        {'name': 'Comptes bancaires', 'icon': 'account_balance', 'color': '#2E7D32'},
        {'name': 'Opérations courantes', 'icon': 'payment', 'color': '#1976D2'},
        {'name': 'Consultations', 'icon': 'local_hospital', 'color': '#D32F2F'},
        {'name': 'État civil', 'icon': 'description', 'color': '#7B1FA2'},
    ]
    
    categories = {}
    for cat_data in categories_data:
        category, created = ServiceCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'description': f"Services de {cat_data['name'].lower()}",
                'icon': cat_data['icon'],
                'color': cat_data['color'],
                'is_active': True
            }
        )
        categories[cat_data['name']] = category
        if created:
            print(f"✅ Catégorie créée: {category.name}")
    
    # ==========================================
    # 4. CRÉER DES SERVICES
    # ==========================================
    print("\n📋 Création des services...")
    
    # Services BHS
    services_bhs = [
        {
            'name': 'Ouverture compte épargne',
            'code': 'OUVCPT',
            'category': 'Comptes bancaires',
            'description': 'Ouvrir un nouveau compte épargne BHS',
            'estimated_duration': 15,
            'cost': 5000,
            'required_documents': ['CNI', 'Justificatif domicile'],
            'allows_appointments': True
        },
        {
            'name': 'Dépôt espèces',
            'code': 'DEPOT',
            'category': 'Opérations courantes',
            'description': 'Effectuer un dépôt d\'espèces',
            'estimated_duration': 5,
            'cost': 0,
            'required_documents': [],
            'allows_appointments': False
        },
        {
            'name': 'Retrait espèces',
            'code': 'RETRAIT',
            'category': 'Opérations courantes', 
            'description': 'Effectuer un retrait d\'espèces',
            'estimated_duration': 3,
            'cost': 500,
            'required_documents': ['CNI', 'Carte bancaire'],
            'allows_appointments': False
        },
        {
            'name': 'Demande de chéquier',
            'code': 'CHEQUE',
            'category': 'Opérations courantes',
            'description': 'Commander un nouveau chéquier',
            'estimated_duration': 10,
            'cost': 2500,
            'required_documents': ['CNI'],
            'allows_appointments': True
        }
    ]
    
    bhs_services = []
    for service_data in services_bhs:
        service, created = Service.objects.get_or_create(
            organization=bhs,
            code=service_data['code'],
            defaults={
                'name': service_data['name'],
                'category': categories[service_data['category']],
                'description': service_data['description'],
                'estimated_duration': service_data['estimated_duration'],
                'cost': service_data.get('cost'),
                'required_documents': service_data['required_documents'],
                'allows_appointments': service_data['allows_appointments'],
                'status': 'active',
                'is_public': True
            }
        )
        bhs_services.append(service)
        if created:
            print(f"✅ Service BHS créé: {service.name}")
    
    # Services Hôpital
    services_hopital = [
        {
            'name': 'Consultation générale',
            'code': 'CONSGEN',
            'category': 'Consultations',
            'description': 'Consultation médicale générale',
            'estimated_duration': 20,
            'cost': 3000,
            'allows_appointments': True
        },
        {
            'name': 'Consultation cardiologie',
            'code': 'CARDIO',
            'category': 'Consultations',
            'description': 'Consultation spécialisée cardiologie',
            'estimated_duration': 30,
            'cost': 8000,
            'allows_appointments': True,
            'requires_appointment': True
        }
    ]
    
    hopital_services = []
    for service_data in services_hopital:
        service, created = Service.objects.get_or_create(
            organization=hopital,
            code=service_data['code'],
            defaults={
                'name': service_data['name'],
                'category': categories[service_data['category']],
                'description': service_data['description'],
                'estimated_duration': service_data['estimated_duration'],
                'cost': service_data.get('cost'),
                'allows_appointments': service_data['allows_appointments'],
                'requires_appointment': service_data.get('requires_appointment', False),
                'status': 'active',
                'is_public': True
            }
        )
        hopital_services.append(service)
        if created:
            print(f"✅ Service Hôpital créé: {service.name}")
    
    # ==========================================
    # 5. CRÉER DES FILES D'ATTENTE
    # ==========================================
    print("\n📋 Création des files d'attente...")
    
    queues = []
    
    # Files d'attente BHS
    for service in bhs_services:
        queue, created = Queue.objects.get_or_create(
            service=service,
            organization=bhs,
            queue_type='normal',
            defaults={
                'name': f"BHS Dakar - {service.name}",
                'description': f"File d'attente pour {service.name}",
                'processing_strategy': 'fifo',
                'max_capacity': 50,
                'max_wait_time': 120,
                'ticket_expiry_time': 30,
                'current_status': 'active',
                'is_active': True
            }
        )
        queues.append(queue)
        if created:
            print(f"✅ File d'attente créée: {queue.name}")
    
    # Files d'attente Hôpital
    for service in hopital_services:
        queue_type = 'appointment' if service.requires_appointment else 'normal'
        queue, created = Queue.objects.get_or_create(
            service=service,
            organization=hopital,
            queue_type=queue_type,
            defaults={
                'name': f"HPD - {service.name}",
                'description': f"File d'attente pour {service.name}",
                'processing_strategy': 'appointment_first' if service.requires_appointment else 'fifo',
                'max_capacity': 30,
                'max_wait_time': 180,
                'ticket_expiry_time': 45,
                'current_status': 'active',
                'is_active': True
            }
        )
        queues.append(queue)
        if created:
            print(f"✅ File d'attente créée: {queue.name}")
    
    # ==========================================
    # 6. CRÉER DES TICKETS D'EXEMPLE
    # ==========================================
    print("\n🎫 Création de tickets d'exemple...")
    
    # Quelques tickets pour la BHS
    bhs_queue = queues[0]  # File "Ouverture compte épargne"
    
    for i, client in enumerate(clients[:3]):
        ticket, created = Ticket.objects.get_or_create(
            customer=client,
            queue=bhs_queue,
            service=bhs_queue.service,
            defaults={
                'priority': 'low',
                'creation_channel': 'mobile',
                'customer_notes': f'Demande d\'ouverture de compte par {client.first_name}',
                'documents_brought': ['CNI', 'Justificatif domicile'],
                'status': 'waiting',
                'queue_position': i + 1,
                'expires_at': timezone.now() + timedelta(minutes=30)
            }
        )
        if created:
            # Mettre à jour les compteurs de la file
            bhs_queue.waiting_tickets_count += 1
            bhs_queue.daily_tickets_issued += 1
            bhs_queue.last_ticket_number += 1
            print(f"✅ Ticket créé: {ticket.ticket_number} pour {client.get_full_name()}")
    
    bhs_queue.save()
    
    print(f"\n🎉 Données de test créées avec succès !")
    print(f"📊 Résumé :")
    print(f"   - {User.objects.count()} utilisateurs")
    print(f"   - {Organization.objects.count()} organisations") 
    print(f"   - {ServiceCategory.objects.count()} catégories de services")
    print(f"   - {Service.objects.count()} services")
    print(f"   - {Queue.objects.count()} files d'attente")
    print(f"   - {Ticket.objects.count()} tickets")
    
    # ==========================================
    # 7. CRÉER DES DONNÉES ANALYTICS
    # ==========================================
    print("\n📊 Création des données analytics...")
    
    create_analytics_data([bhs, hopital, prefecture], bhs_services + hopital_services, queues, clients)
    
    print(f"\n🚀 Testez maintenant :")
    print(f"   - Interface API: http://localhost:8000/api/docs/")
    print(f"   - Organisations: http://localhost:8000/api/organizations/")
    print(f"   - Services: http://localhost:8000/api/services/")
    print(f"   - Files d'attente: http://localhost:8000/api/queues/")
    print(f"   - Analytics Dashboard: http://localhost:8000/api/analytics/api/dashboard/")
    print(f"   - Métriques temps réel: http://localhost:8000/api/analytics/api/realtime/")

if __name__ == '__main__':
    create_test_data()