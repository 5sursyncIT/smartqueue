#!/usr/bin/env python3
"""
Script simplifié pour compléter les données démo
Version qui marche avec les modèles existants
"""

import os
import sys
import django
from django.utils import timezone
from datetime import timedelta

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.business.models import Organization, Service
from apps.queue_management.models import Queue, Ticket

User = get_user_model()

def simple_demo_completion():
    """Ajouter quelques données supplémentaires pour démo live"""

    print("🎯 Ajout données pour démo LIVE...")

    # Récupérer données existantes
    users = list(User.objects.filter(user_type='customer'))
    organizations = list(Organization.objects.all())

    if not users or not organizations:
        print("❌ Erreur: Exécutez d'abord create_demo_data.py")
        return

    # Ajouter plus d'utilisateurs pour la démo live
    additional_users = [
        {'username': 'cheikh', 'phone': '+221781111111', 'first_name': 'Cheikh', 'last_name': 'Sy'},
        {'username': 'aida', 'phone': '+221772222222', 'first_name': 'Aida', 'last_name': 'Kane'},
    ]

    for user_data in additional_users:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'phone_number': user_data['phone'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'user_type': 'customer',
                'is_phone_verified': True
            }
        )
        user.set_password('demo123')
        user.save()
        if created:
            print(f"✅ Client démo live: {user.get_full_name()}")

    print(f"\n📊 ÉTAT FINAL DÉMO:")
    print(f"👥 Utilisateurs: {User.objects.count()}")
    print(f"🏢 Organisations: {Organization.objects.count()}")
    print(f"🛎️ Services: {Service.objects.count()}")
    print(f"📋 Files d'attente: {Queue.objects.count()}")
    print(f"🎫 Tickets: {Ticket.objects.count()}")

    print(f"\n🎭 SCÉNARIO DÉMO LIVE PRÊT !")
    print("✅ Tu peux maintenant créer devant ton supérieur :")
    print("  1. Nouvelle organisation")
    print("  2. Nouveau service")
    print("  3. Nouvelle file d'attente")
    print("  4. Nouveaux tickets")
    print("  5. Actions agent (appeler, servir)")

if __name__ == '__main__':
    simple_demo_completion()