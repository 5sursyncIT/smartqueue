#!/usr/bin/env python3
"""
Script de création de données de démonstration SmartQueue
Pour présentation visuelle du backend via Admin Django
"""

import os
import sys
import django
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.business.models import Organization, Service, ServiceCategory
from apps.queue_management.models import Queue, Ticket
from apps.payments.models import PaymentProvider

User = get_user_model()

def create_demo_data():
    """Créer données complètes pour démo Admin Django"""

    print("🎯 Création données démonstration SmartQueue...")

    # 1. Créer superuser pour admin
    if not User.objects.filter(username='admin').exists():
        admin = User.objects.create_superuser(
            username='admin',
            phone_number='+221761111111',
            password='admin123',
            first_name='Administrateur',
            last_name='SmartQueue'
        )
        print(f"✅ Admin créé: {admin.username}")

    # 2. Créer clients test
    clients = []
    clients_data = [
        {'username': 'aminata', 'phone': '+221781234567', 'first_name': 'Aminata', 'last_name': 'Diop'},
        {'username': 'ibrahima', 'phone': '+221771234567', 'first_name': 'Ibrahima', 'last_name': 'Fall'},
        {'username': 'fatou', 'phone': '+221761234567', 'first_name': 'Fatou', 'last_name': 'Sall'},
        {'username': 'moussa', 'phone': '+221701234567', 'first_name': 'Moussa', 'last_name': 'Diallo'},
    ]

    for data in clients_data:
        user, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'phone_number': data['phone'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'user_type': 'customer',
                'is_phone_verified': True
            }
        )
        user.set_password('demo123')
        user.save()
        clients.append(user)
        if created:
            print(f"✅ Client créé: {user.get_full_name()}")

    # 3. Créer agents
    agents = []
    agents_data = [
        {'username': 'agent1', 'phone': '+221331111111', 'first_name': 'Cheikh', 'last_name': 'Ndiaye'},
        {'username': 'agent2', 'phone': '+221332222222', 'first_name': 'Aissatou', 'last_name': 'Ba'},
    ]

    for data in agents_data:
        agent, created = User.objects.get_or_create(
            username=data['username'],
            defaults={
                'phone_number': data['phone'],
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'user_type': 'staff',
                'is_staff': True
            }
        )
        agent.set_password('demo123')
        agent.save()
        agents.append(agent)
        if created:
            print(f"✅ Agent créé: {agent.get_full_name()}")

    # 4. Créer catégories de services
    categories_data = [
        {'name': 'Bancaire', 'color': '#28a745', 'icon': 'credit-card'},
        {'name': 'Santé', 'color': '#dc3545', 'icon': 'heart'},
        {'name': 'Administration', 'color': '#007bff', 'icon': 'building'},
    ]

    categories = {}
    for i, cat_data in enumerate(categories_data):
        category, created = ServiceCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'color': cat_data['color'],
                'icon': cat_data['icon'],
                'display_order': i + 1
            }
        )
        categories[cat_data['name'].lower()] = category
        if created:
            print(f"✅ Catégorie créée: {category.name}")

    # 5. Créer organisations
    orgs_data = [
        {
            'name': 'BHS Dakar',
            'trade_name': 'Banque de l\'Habitat du Sénégal',
            'type': 'bank',
            'phone_number': '+221338501000',
            'email': 'contact@bhs.sn',
            'region': 'dakar',
            'city': 'Dakar',
            'address': 'Avenue Léopold Sédar Senghor, Dakar'
        },
        {
            'name': 'Hôpital Aristide Le Dantec',
            'trade_name': 'CHU Le Dantec',
            'type': 'hospital',
            'phone_number': '+221338216464',
            'email': 'info@ledantec.sn',
            'region': 'dakar',
            'city': 'Dakar',
            'address': 'Avenue Pasteur, Dakar'
        },
        {
            'name': 'Mairie de Dakar',
            'trade_name': 'Ville de Dakar',
            'type': 'government',
            'phone_number': '+221338235656',
            'email': 'contact@villededakar.sn',
            'region': 'dakar',
            'city': 'Dakar',
            'address': 'Place de l\'Indépendance, Dakar'
        }
    ]

    organizations = []
    for org_data in orgs_data:
        org, created = Organization.objects.get_or_create(
            name=org_data['name'],
            defaults=org_data
        )
        organizations.append(org)
        if created:
            print(f"✅ Organisation créée: {org.trade_name}")

    # 6. Créer services
    services_data = [
        {
            'org_idx': 0,  # BHS
            'name': 'Ouverture de compte',
            'category': 'bancaire',
            'description': 'Ouverture de compte bancaire personnel',
            'estimated_duration': 30,
            'price': Decimal('5000.00')
        },
        {
            'org_idx': 0,  # BHS
            'name': 'Crédit immobilier',
            'category': 'bancaire',
            'description': 'Demande de crédit pour logement',
            'estimated_duration': 45,
            'price': Decimal('10000.00')
        },
        {
            'org_idx': 1,  # Hôpital
            'name': 'Consultation générale',
            'category': 'santé',
            'description': 'Consultation médicale générale',
            'estimated_duration': 20,
            'price': Decimal('15000.00')
        },
        {
            'org_idx': 1,  # Hôpital
            'name': 'Analyses de laboratoire',
            'category': 'santé',
            'description': 'Prélèvements et analyses',
            'estimated_duration': 15,
            'price': Decimal('25000.00')
        },
        {
            'org_idx': 2,  # Mairie
            'name': 'Acte de naissance',
            'category': 'administration',
            'description': 'Demande d\'acte de naissance',
            'estimated_duration': 25,
            'price': Decimal('2000.00')
        }
    ]

    services = []
    for svc_data in services_data:
        org = organizations[svc_data['org_idx']]
        category = categories[svc_data['category']]

        # Générer code unique pour éviter contrainte
        service_code = f"{org.name[:3].upper()}_{svc_data['name'][:10].replace(' ', '_').upper()}"

        service, created = Service.objects.get_or_create(
            organization=org,
            name=svc_data['name'],
            defaults={
                'code': service_code,
                'category': category,
                'description': svc_data['description'],
                'estimated_duration': svc_data['estimated_duration'],
                'cost': svc_data['price']
            }
        )
        services.append(service)
        if created:
            print(f"✅ Service créé: {service.name} - {org.trade_name}")

    # 7. Créer files d'attente
    queues_data = [
        {
            'service_idx': 0,  # Ouverture compte BHS
            'name': 'File Ouverture Compte - Guichet A',
            'queue_type': 'normal',
            'current_status': 'active',
            'max_capacity': 30,
            'estimated_wait_time_per_person': 15
        },
        {
            'service_idx': 1,  # Crédit BHS
            'name': 'File Crédit Immobilier - Conseiller',
            'queue_type': 'appointment',
            'current_status': 'active',
            'max_capacity': 10,
            'estimated_wait_time_per_person': 45
        },
        {
            'service_idx': 2,  # Consultation hôpital
            'name': 'File Consultation - Médecin 1',
            'queue_type': 'priority',
            'current_status': 'active',
            'max_capacity': 25,
            'estimated_wait_time_per_person': 20
        },
        {
            'service_idx': 4,  # Acte naissance mairie
            'name': 'File État Civil',
            'queue_type': 'normal',
            'current_status': 'active',
            'max_capacity': 40,
            'estimated_wait_time_per_person': 25
        }
    ]

    queues = []
    for queue_data in queues_data:
        service = services[queue_data['service_idx']]

        queue, created = Queue.objects.get_or_create(
            service=service,
            name=queue_data['name'],
            defaults={
                'organization': service.organization,
                'queue_type': queue_data['queue_type'],
                'current_status': queue_data['current_status'],
                'max_capacity': queue_data['max_capacity'],
                'max_wait_time': queue_data['estimated_wait_time_per_person']
            }
        )
        queues.append(queue)
        if created:
            print(f"✅ File créée: {queue.name}")

    # 8. Créer tickets de démonstration
    tickets_data = [
        {'queue_idx': 0, 'client_idx': 0, 'status': 'waiting', 'priority': 'low', 'position': 1},
        {'queue_idx': 0, 'client_idx': 1, 'status': 'waiting', 'priority': 'medium', 'position': 2},
        {'queue_idx': 0, 'client_idx': 2, 'status': 'called', 'priority': 'low', 'position': 3},
        {'queue_idx': 1, 'client_idx': 3, 'status': 'waiting', 'priority': 'high', 'position': 1},
        {'queue_idx': 2, 'client_idx': 0, 'status': 'serving', 'priority': 'urgent', 'position': 1},
        {'queue_idx': 3, 'client_idx': 1, 'status': 'waiting', 'priority': 'low', 'position': 1},
        {'queue_idx': 3, 'client_idx': 2, 'status': 'waiting', 'priority': 'low', 'position': 2},
    ]

    for i, ticket_data in enumerate(tickets_data):
        queue = queues[ticket_data['queue_idx']]
        client = clients[ticket_data['client_idx']]

        # Générer numéro ticket unique
        ticket_number = f"{queue.queue_type[0].upper()}{str(i+1).zfill(3)}"

        ticket, created = Ticket.objects.get_or_create(
            ticket_number=ticket_number,
            defaults={
                'queue': queue,
                'service': queue.service,
                'customer': client,
                'status': ticket_data['status'],
                'priority': ticket_data['priority'],
                'queue_position': ticket_data['position'],
                'creation_channel': 'mobile',
                'created_at': timezone.now() - timedelta(minutes=(7-i)*10),
                'expires_at': timezone.now() + timedelta(hours=2)
            }
        )

        # Ajouter timestamps selon statut
        if ticket.status == 'called':
            ticket.called_at = timezone.now() - timedelta(minutes=5)
        elif ticket.status == 'serving':
            ticket.called_at = timezone.now() - timedelta(minutes=10)
            ticket.service_started_at = timezone.now() - timedelta(minutes=5)

        ticket.save()

        if created:
            print(f"✅ Ticket créé: {ticket.ticket_number} - {client.get_full_name()} ({ticket.status})")

    # 9. Créer providers de paiement
    providers_data = [
        {'name': 'Wave Sénégal', 'provider_type': 'wave', 'is_active': True},
        {'name': 'Orange Money', 'provider_type': 'orange_money', 'is_active': True},
        {'name': 'Free Money', 'provider_type': 'free_money', 'is_active': True},
    ]

    for provider_data in providers_data:
        provider, created = PaymentProvider.objects.get_or_create(
            name=provider_data['name'],
            defaults={
                'provider_type': provider_data['provider_type'],
                'is_active': provider_data['is_active']
            }
        )
        if created:
            print(f"✅ Provider créé: {provider.name}")

    print("\n🎯 DONNÉES DE DÉMONSTRATION CRÉÉES !")
    print("\n📊 Résumé:")
    print(f"👥 Utilisateurs: {User.objects.count()}")
    print(f"🏢 Organisations: {Organization.objects.count()}")
    print(f"🛎️ Services: {Service.objects.count()}")
    print(f"📋 Files d'attente: {Queue.objects.count()}")
    print(f"🎫 Tickets: {Ticket.objects.count()}")

    print("\n🔐 ACCÈS ADMIN:")
    print("URL: http://localhost:8000/admin/")
    print("Username: admin")
    print("Password: admin123")

    print("\n🎭 COMPTES TEST:")
    for client in clients[:2]:
        print(f"👤 {client.get_full_name()}: {client.username} / demo123")

    print("\n🚀 DÉMARRER SERVEUR:")
    print("python3 manage.py runserver")

if __name__ == '__main__':
    create_demo_data()