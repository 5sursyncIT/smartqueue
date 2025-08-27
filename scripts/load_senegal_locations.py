#!/usr/bin/env python
"""
Script de chargement des données géographiques du Sénégal
Régions, communes et données de test pour SmartQueue

Utilisation: python manage.py shell < scripts/load_senegal_locations.py
"""

from decimal import Decimal
from apps.locations.models import Region, Commune
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model

User = get_user_model()

# Données géographiques du Sénégal
SENEGAL_REGIONS = {
    'dakar': {
        'name': 'Dakar',
        'center_latitude': Decimal('14.6928'),
        'center_longitude': Decimal('-17.4467'),
        'coverage_radius_km': 50,
        'communes': [
            # Communes de Dakar
            {
                'name': 'Dakar-Plateau',
                'locality_type': 'commune',
                'latitude': Decimal('14.6928'),
                'longitude': Decimal('-17.4467'),
                'population': 18773,
                'traffic_factor': 2.5  # Centre-ville très embouteillé
            },
            {
                'name': 'Medina',
                'locality_type': 'commune', 
                'latitude': Decimal('14.6792'),
                'longitude': Decimal('-17.4441'),
                'population': 90480,
                'traffic_factor': 2.2
            },
            {
                'name': 'Gueule Tapée-Fass-Colobane',
                'locality_type': 'commune',
                'latitude': Decimal('14.6850'),
                'longitude': Decimal('-17.4520'),
                'population': 131218,
                'traffic_factor': 2.0
            },
            {
                'name': 'Parcelles Assainies',
                'locality_type': 'commune',
                'latitude': Decimal('14.7644'),
                'longitude': Decimal('-17.4322'),
                'population': 353317,
                'traffic_factor': 1.8
            },
            {
                'name': 'Grand Yoff',
                'locality_type': 'commune',
                'latitude': Decimal('14.7500'),
                'longitude': Decimal('-17.4800'),
                'population': 144859,
                'traffic_factor': 1.7
            },
            {
                'name': 'Pikine',
                'locality_type': 'commune',
                'latitude': Decimal('14.7544'),
                'longitude': Decimal('-17.3942'),
                'population': 874062,
                'traffic_factor': 2.1  # Pikine -> exemple du superviseur
            },
            {
                'name': 'Guédiawaye', 
                'locality_type': 'commune',
                'latitude': Decimal('14.7692'),
                'longitude': Decimal('-17.4103'),
                'population': 311500,
                'traffic_factor': 1.9
            },
            # Rufisque
            {
                'name': 'Rufisque',
                'locality_type': 'commune',
                'latitude': Decimal('14.7167'),
                'longitude': Decimal('-17.2667'), 
                'population': 221166,
                'traffic_factor': 1.6
            },
            # Keur Massar
            {
                'name': 'Keur Massar',
                'locality_type': 'commune',
                'latitude': Decimal('14.7833'),
                'longitude': Decimal('-17.3167'),
                'population': 492675,
                'traffic_factor': 1.5
            },
            # Diamniadio - exemple destination du superviseur
            {
                'name': 'Diamniadio',
                'locality_type': 'commune',
                'latitude': Decimal('14.7206'),
                'longitude': Decimal('-17.1842'),
                'population': 35000,
                'traffic_factor': 1.2  # Ville nouvelle, moins d'embouteillages
            }
        ]
    },
    
    'thies': {
        'name': 'Thiès',
        'center_latitude': Decimal('14.7886'),
        'center_longitude': Decimal('-16.9317'),
        'coverage_radius_km': 80,
        'communes': [
            {
                'name': 'Thiès Nord',
                'locality_type': 'commune',
                'latitude': Decimal('14.7886'),
                'longitude': Decimal('-16.9317'),
                'population': 165249,
                'traffic_factor': 1.4
            },
            {
                'name': 'Thiès Sud',
                'locality_type': 'commune',
                'latitude': Decimal('14.7750'),
                'longitude': Decimal('-16.9300'),
                'population': 152745,
                'traffic_factor': 1.3
            },
            {
                'name': 'Tivaouane',
                'locality_type': 'commune',
                'latitude': Decimal('14.9500'),
                'longitude': Decimal('-16.8167'),
                'population': 43947,
                'traffic_factor': 1.1
            },
            {
                'name': 'Mbour',
                'locality_type': 'commune',
                'latitude': Decimal('14.4167'),
                'longitude': Decimal('-16.9667'),
                'population': 232777,
                'traffic_factor': 1.5
            }
        ]
    },
    
    'diourbel': {
        'name': 'Diourbel',
        'center_latitude': Decimal('14.6522'),
        'center_longitude': Decimal('-16.2317'),
        'coverage_radius_km': 60,
        'communes': [
            {
                'name': 'Diourbel',
                'locality_type': 'commune',
                'latitude': Decimal('14.6522'),
                'longitude': Decimal('-16.2317'),
                'population': 100445,
                'traffic_factor': 1.3
            },
            {
                'name': 'Touba',
                'locality_type': 'commune',
                'latitude': Decimal('14.8500'),
                'longitude': Decimal('-15.8833'),
                'population': 529176,
                'traffic_factor': 1.8  # Ville religieuse, beaucoup de trafic
            },
            {
                'name': 'Mbacké',
                'locality_type': 'commune',
                'latitude': Decimal('14.7967'),
                'longitude': Decimal('-15.9167'),
                'population': 78552,
                'traffic_factor': 1.2
            }
        ]
    }
}

def create_regions_and_communes():
    """Créer les régions et communes du Sénégal"""
    print("🌍 Chargement des données géographiques du Sénégal...")
    
    # Obtenir un utilisateur admin pour created_by
    admin_user = User.objects.filter(user_type='super_admin').first()
    if not admin_user:
        print("⚠️ Aucun super admin trouvé, création sans created_by")
        admin_user = None
    
    regions_created = 0
    communes_created = 0
    
    for region_code, region_data in SENEGAL_REGIONS.items():
        # Créer ou mettre à jour la région
        region, created = Region.objects.update_or_create(
            code=region_code,
            defaults={
                'name': region_data['name'],
                'center_latitude': region_data['center_latitude'],
                'center_longitude': region_data['center_longitude'],
                'coverage_radius_km': region_data['coverage_radius_km'],
                'created_by': admin_user,
                'is_active': True
            }
        )
        
        if created:
            regions_created += 1
            print(f"✅ Région créée: {region.name}")
        else:
            print(f"🔄 Région mise à jour: {region.name}")
        
        # Créer les communes de cette région
        for commune_data in region_data['communes']:
            commune, created = Commune.objects.update_or_create(
                region=region,
                name=commune_data['name'],
                defaults={
                    'locality_type': commune_data['locality_type'],
                    'latitude': commune_data['latitude'],
                    'longitude': commune_data['longitude'],
                    'population': commune_data['population'],
                    'traffic_factor': commune_data['traffic_factor'],
                    'created_by': admin_user,
                    'is_active': True
                }
            )
            
            if created:
                communes_created += 1
                print(f"  ✅ Commune créée: {commune.name}")
            else:
                print(f"  🔄 Commune mise à jour: {commune.name}")
    
    print(f"\n📊 Résumé:")
    print(f"   - {regions_created} nouvelles régions créées")
    print(f"   - {communes_created} nouvelles communes créées")
    print(f"   - Total: {Region.objects.count()} régions, {Commune.objects.count()} communes")

def create_sample_organizations():
    """Créer des organisations d'exemple à Diamniadio"""
    print("\n🏢 Création d'organisations d'exemple...")
    
    # Trouver Diamniadio
    try:
        diamniadio = Commune.objects.get(name='Diamniadio')
        admin_user = User.objects.filter(user_type='super_admin').first()
        
        # Organisations d'exemple à Diamniadio (destination du superviseur)
        sample_orgs = [
            {
                'name': 'Banque Atlantique Diamniadio',
                'organization_type': 'bank',
                'address': 'Centre commercial Diamniadio',
                'latitude': Decimal('14.7206'),
                'longitude': Decimal('-17.1842'),
                'phone': '+221 33 123 45 67'
            },
            {
                'name': 'CBAO Agence Diamniadio',
                'organization_type': 'bank', 
                'address': 'Rond-point Diamniadio',
                'latitude': Decimal('14.7200'),
                'longitude': Decimal('-17.1850'),
                'phone': '+221 33 765 43 21'
            },
            {
                'name': 'Centre de Santé Diamniadio',
                'organization_type': 'hospital',
                'address': 'Avenue Cheikh Anta Diop',
                'latitude': Decimal('14.7210'),
                'longitude': Decimal('-17.1835'),
                'phone': '+221 33 987 65 43'
            }
        ]
        
        orgs_created = 0
        for org_data in sample_orgs:
            org, created = Organization.objects.update_or_create(
                name=org_data['name'],
                defaults={
                    'organization_type': org_data['organization_type'],
                    'address': org_data['address'],
                    'latitude': org_data['latitude'],
                    'longitude': org_data['longitude'],
                    'phone': org_data['phone'],
                    'is_active': True,
                    'created_by': admin_user
                }
            )
            
            if created:
                orgs_created += 1
                print(f"  ✅ Organisation créée: {org.name}")
            else:
                print(f"  🔄 Organisation mise à jour: {org.name}")
        
        print(f"📊 {orgs_created} nouvelles organisations créées à Diamniadio")
        
    except Commune.DoesNotExist:
        print("❌ Commune Diamniadio non trouvée")
    except Exception as e:
        print(f"❌ Erreur création organisations: {e}")

def main():
    """Fonction principale"""
    print("🚀 Initialisation des données géographiques SmartQueue")
    print("=" * 60)
    
    try:
        # Créer régions et communes
        create_regions_and_communes()
        
        # Créer organisations d'exemple
        create_sample_organizations()
        
        print("\n🎉 Chargement terminé avec succès!")
        print("\n💡 Exemple d'utilisation:")
        print("   - Client à Pikine -> Banque à Diamniadio")
        print("   - Distance: ~37 km")
        print("   - Temps estimé: 45-90 min selon trafic")
        print("   - Réorganisation automatique des files")
        
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()