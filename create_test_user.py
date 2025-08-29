#!/usr/bin/env python
"""
Script pour créer un utilisateur test
"""

import os
import django
import sys

# Configuration Django
sys.path.append('/home/aicha/projects/smartqueue_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User

def create_test_user():
    print("=== CRÉATION D'UTILISATEUR TEST ===")
    
    # Vérifier s'il y a déjà des utilisateurs
    users = User.objects.all()
    print(f"Utilisateurs existants: {users.count()}")
    
    if users.count() > 0:
        user = users.first()
        print(f"✅ Utilisateur trouvé: {user.first_name} {user.last_name} (ID: {user.id})")
        return user.id
    
    # Créer un utilisateur test
    try:
        user = User.objects.create_user(
            username='testuser',
            first_name='Aminata',
            last_name='Diop',
            email='aminata@example.com',
            phone_number='+221771234567',
            password='testpass123'
        )
        print(f"✅ UTILISATEUR CRÉÉ!")
        print(f"   - ID: {user.id}")
        print(f"   - Nom: {user.first_name} {user.last_name}")
        print(f"   - Email: {user.email}")
        return user.id
        
    except Exception as e:
        print(f"❌ ERREUR lors de la création: {e}")
        return None

if __name__ == "__main__":
    user_id = create_test_user()
    if user_id:
        print(f"\n🎯 UTILISE customer: {user_id} dans tes tickets !")