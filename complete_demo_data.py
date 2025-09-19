#!/usr/bin/env python3
"""
Script pour compléter les données de démonstration
Ajouter Notifications, Analytics, Appointments
"""

import os
import sys
import django
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta, datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.business.models import Organization, Service
from apps.queue_management.models import Queue, Ticket
from apps.notifications.models import Notification, NotificationTemplate
from apps.analytics.models import QueueMetrics, ServiceMetrics, OrganizationMetrics
from apps.appointments.models import Appointment

User = get_user_model()

def complete_demo_data():
    """Compléter les données pour toutes les apps"""

    print("🎯 Complétion des données démonstration...")

    # Récupérer données existantes
    users = list(User.objects.filter(user_type='customer')[:3])
    organizations = list(Organization.objects.all())
    queues = list(Queue.objects.all())
    services = list(Service.objects.all())

    if not users or not organizations:
        print("❌ Erreur: Exécutez d'abord create_demo_data.py")
        return

    # ==============================================
    # NOTIFICATIONS
    # ==============================================
    print("\n📢 Création notifications...")

    # Créer templates de notification
    templates_data = [
        {'name': 'Ticket appelé', 'notification_type': 'ticket_called', 'template_content': 'Votre ticket {ticket_number} a été appelé.'},
        {'name': 'Position file', 'notification_type': 'queue_position', 'template_content': 'Vous êtes {position}ème dans la file.'},
        {'name': 'Service terminé', 'notification_type': 'service_completed', 'template_content': 'Votre service a été traité avec succès.'},
        {'name': 'Paiement confirmé', 'notification_type': 'payment_confirmed', 'template_content': 'Paiement de {amount} FCFA confirmé.'},
    ]

    for template_data in templates_data:
        template, created = NotificationTemplate.objects.get_or_create(
            name=template_data['name'],
            defaults=template_data
        )
        if created:
            print(f"✅ Template créé: {template.name}")

    # Créer notifications de démonstration
    notifications_data = [
        {
            'user': users[0],
            'title': 'Ticket appelé',
            'message': 'Votre ticket A001 a été appelé. Veuillez vous présenter au guichet.',
            'notification_type': 'ticket_called',
            'is_read': False
        },
        {
            'user': users[1],
            'title': 'Position dans la file',
            'message': 'Vous êtes maintenant 2ème dans la file d\'attente.',
            'notification_type': 'queue_position',
            'is_read': True
        },
        {
            'user': users[2],
            'title': 'Service terminé',
            'message': 'Votre demande d\'acte de naissance a été traitée avec succès.',
            'notification_type': 'service_completed',
            'is_read': False
        },
        {
            'user': users[0],
            'title': 'Paiement confirmé',
            'message': 'Votre paiement de 5000 FCFA via Wave a été confirmé.',
            'notification_type': 'payment_confirmed',
            'is_read': True
        }
    ]

    for notif_data in notifications_data:
        notification, created = Notification.objects.get_or_create(
            user=notif_data['user'],
            title=notif_data['title'],
            defaults=notif_data
        )
        if created:
            print(f"✅ Notification: {notification.title}")

    # ==============================================
    # ANALYTICS
    # ==============================================
    print("\n📊 Création analytics...")

    # Métriques des files d'attente
    for queue in queues:
        today = timezone.now().date()

        metrics_data = {
            'queue': queue,
            'date': today,
            'total_tickets': 12 + queue.id,
            'served_tickets': 9 + queue.id,
            'cancelled_tickets': 2,
            'no_show_tickets': 1,
            'average_wait_time': 18 + (queue.id * 3),
            'average_service_time': 12 + queue.id,
            'peak_hour_start': 14,
            'peak_hour_end': 16,
            'customer_satisfaction_score': 4.2 + (queue.id * 0.1)
        }

        queue_metrics, created = QueueMetrics.objects.get_or_create(
            queue=queue,
            date=today,
            defaults=metrics_data
        )
        if created:
            print(f"✅ Métriques file: {queue.name}")

    # Métriques des services
    for service in services:
        today = timezone.now().date()

        service_metrics_data = {
            'service': service,
            'date': today,
            'total_requests': 25 + service.id,
            'completed_requests': 20 + service.id,
            'average_duration': service.estimated_duration + 5,
            'revenue_generated': Decimal(str(50000 + (service.id * 15000))),
            'customer_rating': 4.0 + (service.id * 0.2)
        }

        service_metrics, created = ServiceMetrics.objects.get_or_create(
            service=service,
            date=today,
            defaults=service_metrics_data
        )
        if created:
            print(f"✅ Métriques service: {service.name}")

    # Métriques organisations
    for i, org in enumerate(organizations):
        today = timezone.now().date()

        org_metrics_data = {
            'organization': org,
            'date': today,
            'total_customers': 150 + (i * 50),
            'new_customers': 12 + i,
            'total_revenue': Decimal(str(500000 + (i * 200000))),
            'total_tickets': 89 + (i * 25),
            'average_satisfaction': 4.1 + (i * 0.2)
        }

        org_metrics, created = OrganizationMetrics.objects.get_or_create(
            organization=org,
            date=today,
            defaults=org_metrics_data
        )
        if created:
            print(f"✅ Métriques organisation: {org.name}")

    # ==============================================
    # APPOINTMENTS (Rendez-vous)
    # ==============================================
    print("\n📅 Création appointments...")

    appointments_data = [
        {
            'user': users[0],
            'service': services[1],  # Crédit immobilier
            'organization': services[1].organization,
            'scheduled_datetime': timezone.now() + timedelta(days=2, hours=10),
            'status': 'confirmed',
            'notes': 'Apporter relevés bancaires des 3 derniers mois',
            'duration_minutes': 60
        },
        {
            'user': users[1],
            'service': services[2],  # Consultation
            'organization': services[2].organization,
            'scheduled_datetime': timezone.now() + timedelta(days=1, hours=14, minutes=30),
            'status': 'pending',
            'notes': 'Consultation de suivi',
            'duration_minutes': 30
        },
        {
            'user': users[2],
            'service': services[0],  # Ouverture compte
            'organization': services[0].organization,
            'scheduled_datetime': timezone.now() + timedelta(days=3, hours=9),
            'status': 'confirmed',
            'notes': 'Première ouverture de compte',
            'duration_minutes': 45
        },
        {
            'user': users[0],
            'service': services[2],  # Consultation
            'organization': services[2].organization,
            'scheduled_datetime': timezone.now() - timedelta(days=1, hours=2),
            'status': 'completed',
            'notes': 'Consultation terminée',
            'duration_minutes': 25
        }
    ]

    for appt_data in appointments_data:
        # Générer numéro de rendez-vous unique
        appointment_number = f"RDV{timezone.now().strftime('%Y%m%d')}{appt_data['user'].id:03d}"

        appointment, created = Appointment.objects.get_or_create(
            appointment_number=appointment_number,
            defaults={**appt_data, 'appointment_number': appointment_number}
        )
        if created:
            print(f"✅ RDV: {appointment.appointment_number} - {appointment.user.get_full_name()}")

    # ==============================================
    # RÉSUMÉ FINAL
    # ==============================================
    print("\n🎯 TOUTES LES DONNÉES CRÉÉES !")
    print("\n📊 Résumé complet:")
    print(f"👥 Utilisateurs: {User.objects.count()}")
    print(f"🏢 Organisations: {Organization.objects.count()}")
    print(f"🛎️ Services: {Service.objects.count()}")
    print(f"📋 Files d'attente: {Queue.objects.count()}")
    print(f"🎫 Tickets: {Ticket.objects.count()}")
    print(f"📢 Notifications: {Notification.objects.count()}")
    print(f"📊 Métriques files: {QueueMetrics.objects.count()}")
    print(f"📊 Métriques services: {ServiceMetrics.objects.count()}")
    print(f"📊 Métriques organisations: {OrganizationMetrics.objects.count()}")
    print(f"📅 Rendez-vous: {Appointment.objects.count()}")

    print("\n🔗 URLs admin COMPLÈTES:")
    print("http://localhost:8000/admin/notifications/notification/")
    print("http://localhost:8000/admin/analytics/queuemetrics/")
    print("http://localhost:8000/admin/analytics/servicemetrics/")
    print("http://localhost:8000/admin/analytics/organizationmetrics/")
    print("http://localhost:8000/admin/appointments/appointment/")

if __name__ == '__main__':
    complete_demo_data()