#!/usr/bin/env python
"""
Vérifier le statut de la queue
"""

import os
import django
import sys

# Configuration Django
sys.path.append('/home/aicha/projects/smartqueue_backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.queue_management.models import Queue

def check_queue_status():
    print("=== STATUT DE LA QUEUE ===")
    
    try:
        queue = Queue.objects.get(id=1)
        print(f"✅ Queue trouvée:")
        print(f"   - ID: {queue.id}")
        print(f"   - Nom: {queue.name}")
        print(f"   - Current Status: {queue.current_status}")
        print(f"   - Is Active: {queue.is_active}")
        
        # Corriger le statut si nécessaire
        if queue.current_status != 'active':
            print(f"🔧 CORRECTION: Changement de '{queue.current_status}' vers 'active'")
            queue.current_status = 'active'
            queue.save()
            print("✅ Queue mise à jour!")
        else:
            print("✅ Queue déjà active!")
            
    except Queue.DoesNotExist:
        print("❌ ERREUR: Queue ID=1 n'existe pas!")

if __name__ == "__main__":
    check_queue_status()