#!/usr/bin/env python
"""
Script de test SIMPLE pour créer un service
SANS l'interface DRF compliquée
"""

import os
import django
import sys

# Configuration Django
sys.path.append('/home/aicha/projects/smartqueue_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.business.models import Organization, Service

def create_test_service():
    print("=== TEST DE CRÉATION DE SERVICE ===")
    
    # 1. Vérifier organisations existantes
    orgs = Organization.objects.all()
    print(f"Organisations disponibles: {orgs.count()}")
    
    if orgs.count() == 0:
        print("❌ ERREUR: Aucune organisation trouvée!")
        print("Va d'abord créer une organisation sur /api/business/organizations/")
        return
    
    # 2. Prendre la première organisation
    org = orgs.first()
    print(f"✅ Utilisation de l'organisation: {org.name} (ID: {org.id})")
    
    # 3. Créer le service avec SEULEMENT les champs essentiels
    try:
        service = Service.objects.create(
            organization=org,
            name="Service Test",
            code="TEST001",
            description="Service de test créé programmatiquement",
            estimated_duration=15,
            cost=0,
            default_priority='low',
            status='active',
            is_public=True,
            allows_appointments=True,
            requires_appointment=False,
            # Les champs JSON avec valeurs par défaut
            required_documents=[],
            optional_documents=[],
            service_hours={},
        )
        print(f"✅ SERVICE CRÉÉ AVEC SUCCÈS!")
        print(f"   - ID: {service.id}")
        print(f"   - Nom: {service.name}")
        print(f"   - Code: {service.code}")
        print(f"   - Organisation: {service.organization.name}")
        
    except Exception as e:
        print(f"❌ ERREUR lors de la création: {e}")

if __name__ == "__main__":
    create_test_service()