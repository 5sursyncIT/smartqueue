"""
Django management command pour charger les données géographiques du Sénégal
"""

from django.core.management.base import BaseCommand
from decimal import Decimal
from apps.locations.models import Region, Commune
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Charge les données géographiques du Sénégal (régions, communes, organisations)'
    
    def handle(self, *args, **options):
        """Fonction principale du command"""
        self.stdout.write(self.style.SUCCESS('🚀 Chargement des données géographiques du Sénégal'))
        self.stdout.write('=' * 60)
        
        try:
            # Créer régions et communes
            self.create_regions_and_communes()
            
            # Créer organisations d'exemple
            self.create_sample_organizations()
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('🎉 Chargement terminé avec succès!'))
            self.stdout.write('')
            self.stdout.write('💡 Exemple d\'utilisation:')
            self.stdout.write('   - Client à Pikine -> Banque à Diamniadio')
            self.stdout.write('   - Distance: ~37 km')
            self.stdout.write('   - Temps estimé: 45-90 min selon trafic')
            self.stdout.write('   - Réorganisation automatique des files')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erreur lors du chargement: {e}'))
    
    def create_regions_and_communes(self):
        """Créer les régions et communes du Sénégal"""
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
        
        self.stdout.write('🌍 Chargement des données géographiques du Sénégal...')
        
        # Obtenir un utilisateur admin pour created_by
        admin_user = User.objects.filter(user_type='super_admin').first()
        if not admin_user:
            self.stdout.write(self.style.WARNING('⚠️ Aucun super admin trouvé, création sans created_by'))
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
                self.stdout.write(f'✅ Région créée: {region.name}')
            else:
                self.stdout.write(f'🔄 Région mise à jour: {region.name}')
            
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
                    self.stdout.write(f'  ✅ Commune créée: {commune.name}')
                else:
                    self.stdout.write(f'  🔄 Commune mise à jour: {commune.name}')
        
        self.stdout.write('')
        self.stdout.write('📊 Résumé:')
        self.stdout.write(f'   - {regions_created} nouvelles régions créées')
        self.stdout.write(f'   - {communes_created} nouvelles communes créées')
        self.stdout.write(f'   - Total: {Region.objects.count()} régions, {Commune.objects.count()} communes')
    
    def create_sample_organizations(self):
        """Créer des organisations d'exemple à Diamniadio"""
        self.stdout.write('')
        self.stdout.write('🏢 Création d\'organisations d\'exemple...')
        
        # Trouver Diamniadio
        try:
            diamniadio = Commune.objects.get(name='Diamniadio')
            admin_user = User.objects.filter(user_type='super_admin').first()
            
            # Organisations d'exemple à Diamniadio (destination du superviseur)
            sample_orgs = [
                {
                    'name': 'Banque Atlantique Diamniadio',
                    'type': 'bank',
                    'address': 'Centre commercial Diamniadio',
                    'city': 'Diamniadio',
                    'region': 'dakar',
                    'latitude': Decimal('14.7206'),
                    'longitude': Decimal('-17.1842'),
                    'phone_number': '+221331234567',
                    'email': 'diamniadio@atlantique.sn'
                },
                {
                    'name': 'CBAO Agence Diamniadio',
                    'type': 'bank', 
                    'address': 'Rond-point Diamniadio',
                    'city': 'Diamniadio',
                    'region': 'dakar',
                    'latitude': Decimal('14.7200'),
                    'longitude': Decimal('-17.1850'),
                    'phone_number': '+221337654321',
                    'email': 'diamniadio@cbao.sn'
                },
                {
                    'name': 'Centre de Santé Diamniadio',
                    'type': 'hospital',
                    'address': 'Avenue Cheikh Anta Diop',
                    'city': 'Diamniadio',
                    'region': 'dakar',
                    'latitude': Decimal('14.7210'),
                    'longitude': Decimal('-17.1835'),
                    'phone_number': '+221339876543',
                    'email': 'contact@sante-diamniadio.sn'
                }
            ]
            
            orgs_created = 0
            for org_data in sample_orgs:
                org, created = Organization.objects.update_or_create(
                    name=org_data['name'],
                    defaults={
                        'type': org_data['type'],
                        'address': org_data['address'],
                        'city': org_data['city'],
                        'region': org_data['region'],
                        'latitude': org_data['latitude'],
                        'longitude': org_data['longitude'],
                        'phone_number': org_data['phone_number'],
                        'email': org_data['email'],
                        'status': 'active'
                    }
                )
                
                if created:
                    orgs_created += 1
                    self.stdout.write(f'  ✅ Organisation créée: {org.name}')
                else:
                    self.stdout.write(f'  🔄 Organisation mise à jour: {org.name}')
            
            self.stdout.write(f'📊 {orgs_created} nouvelles organisations créées à Diamniadio')
            
        except Commune.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ Commune Diamniadio non trouvée'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Erreur création organisations: {e}'))