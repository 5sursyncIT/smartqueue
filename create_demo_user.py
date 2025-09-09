#!/usr/bin/env python3
"""
Script pour créer l'utilisateur DEMO pour les tests API
"""

import os
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.accounts.models import User

def create_demo_user():
    """Créer ou mettre à jour l'utilisateur demo"""
    
    demo_data = {
        "username": "demo",
        "email": "demo@smartqueue.sn",
        "phone_number": "+221701111111",
        "first_name": "Demo",
        "last_name": "User",
        "user_type": "customer",
        "is_active": True
    }
    
    try:
        # Vérifier si l'utilisateur demo existe
        user, created = User.objects.get_or_create(
            email="demo@smartqueue.sn",
            defaults=demo_data
        )
        
        if created:
            user.set_password("demo123")
            user.save()
            print("✅ Utilisateur demo créé:")
        else:
            # Mettre à jour le mot de passe
            user.set_password("demo123")  
            user.save()
            print("✅ Utilisateur demo mis à jour:")
        
        print(f"   - Email: {user.email}")
        print(f"   - Phone: {user.phone_number}")
        print(f"   - Password: demo123")
        print(f"   - Name: {user.get_full_name()}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    print("👤 CRÉATION UTILISATEUR DEMO")
    print("=" * 40)
    create_demo_user()