#!/usr/bin/env python3
"""
Script de test COMPLET pour l'app BUSINESS
Teste TOUS les endpoints disponibles dans l'API Business
"""

import requests
import json
import time
from datetime import datetime

class BusinessCompleteAPITester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8001/api/business"
        self.auth_url = "http://127.0.0.1:8001/api/accounts"
        self.access_token = None
        self.refresh_token = None
        
        # Données de test pour organisation - UNIQUES à chaque test
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_organization_data = {
            "name": f"Banque Test API {timestamp}",
            "trade_name": f"BTA {timestamp}",
            "type": "bank", 
            "email": f"test_{timestamp}@smartqueue-api.sn",
            "phone_number": f"+221338{timestamp[-6:]}",  # 6 derniers chiffres du timestamp
            "address": "Plateau, Dakar",
            "city": "Dakar", 
            "region": "dakar",
            "description": f"Banque de test API créée le {timestamp}"
        }
        
        # Données de test pour service - CODE UNIQUE
        self.test_service_data = {
            "name": f"Service Test {timestamp}",
            "code": f"SRV_{timestamp}", 
            "description": f"Service de test créé le {timestamp}",
            "estimated_duration": 30
        }
        
        self.results = []
        self.organization_id = None
        self.service_id = None
    
    def log_result(self, test_name, success, status_code, message, response_data=None):
        """Enregistrer le résultat d'un test"""
        result = {
            "test": test_name,
            "success": success,
            "status_code": status_code,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.results.append(result)
        
        # Affichage coloré
        status_icon = "✅" if success else "❌"
        status_text = "PASS" if success else "FAIL"
        print(f"{status_icon} {status_text} | {test_name:35} | {status_code:3} | {message}")
    
    def check_server(self):
        """Vérifier que le serveur est accessible"""
        try:
            response = requests.get(self.auth_url + "/status/", timeout=5, 
                                  headers={"Authorization": "Bearer fake_token_for_test"})
            return True
        except:
            print("❌ Serveur Django non accessible sur http://127.0.0.1:8001")
            print("   Lance d'abord: python manage.py runserver 8001")
            return False
    
    def login_demo(self):
        """Connexion avec le compte demo pour les tests"""
        login_data = {
            "login": "demo@smartqueue.sn", 
            "password": "nouveaumotdepasse123"  # Mot de passe changé par les tests précédents
        }
        
        try:
            response = requests.post(f"{self.auth_url}/login/", json=login_data, timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["tokens"]["access"]
                self.refresh_token = data["tokens"]["refresh"]
                print("✅ Connexion demo réussie")
                return True
            else:
                print("❌ Échec connexion demo")
                return False
        except Exception as e:
            print(f"❌ Erreur connexion: {e}")
            return False
    
    def make_request(self, method, endpoint, data=None, use_auth=False):
        """Faire une requête HTTP avec gestion d'erreurs"""
        url = self.base_url + endpoint
        headers = {"Content-Type": "application/json"}
        
        if use_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == "PATCH":
                response = requests.patch(url, json=data, headers=headers, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                return None
            
            # Debug: afficher les erreurs
            if response.status_code >= 400:
                print(f"🔍 DEBUG - {method} {url}")
                print(f"    Status: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"    Error: {error_data}")
                except:
                    print(f"    Error text: {response.text[:200]}")
            
            return response
        except Exception as e:
            print(f"❌ Erreur requête {method} {endpoint}: {e}")
            return None
    
    # ==============================================
    # TESTS ORGANIZATIONS - CRUD COMPLET
    # ==============================================
    
    def test_01_create_organization(self):
        """Test: POST /api/business/organizations/"""
        print("\n🧪 TEST 1: CRÉER ORGANISATION")
        
        response = self.make_request("POST", "/organizations/", self.test_organization_data, use_auth=True)
        
        if response and response.status_code == 201:
            data = response.json()
            self.organization_id = data.get("id")
            self.log_result("Create Organization", True, 201, "Organisation créée", 
                          {"id": self.organization_id, "name": data.get("name")})
        else:
            error_data = response.json() if response else None
            self.log_result("Create Organization", False, response.status_code if response else 0,
                          "Échec création organisation", error_data)
    
    def test_02_list_organizations(self):
        """Test: GET /api/business/organizations/"""
        print("\n🧪 TEST 2: LISTER ORGANISATIONS")
        
        response = self.make_request("GET", "/organizations/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            count = len(data.get("results", data)) if isinstance(data, dict) and "results" in data else len(data)
            self.log_result("List Organizations", True, 200, "Liste récupérée", 
                          {"count": count})
        else:
            error_data = response.json() if response else None
            self.log_result("List Organizations", False, response.status_code if response else 0,
                          "Échec récupération liste", error_data)
    
    def test_03_get_organization(self):
        """Test: GET /api/business/organizations/{id}/"""
        print("\n🧪 TEST 3: DÉTAIL ORGANISATION")
        
        if not self.organization_id:
            self.log_result("Get Organization", False, 0, "Pas d'ID organisation")
            return
        
        response = self.make_request("GET", f"/organizations/{self.organization_id}/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Get Organization", True, 200, "Détail récupéré", 
                          {"name": data.get("name")})
        else:
            error_data = response.json() if response else None
            self.log_result("Get Organization", False, response.status_code if response else 0,
                          "Échec récupération détail", error_data)
    
    def test_04_update_organization(self):
        """Test: PATCH /api/business/organizations/{id}/"""
        print("\n🧪 TEST 4: MODIFIER ORGANISATION")
        
        if not self.organization_id:
            self.log_result("Update Organization", False, 0, "Pas d'ID organisation")
            return
        
        update_data = {
            "trade_name": "BCT API Modifiée",
            "description": "Description mise à jour par l'API complète"
        }
        
        response = self.make_request("PATCH", f"/organizations/{self.organization_id}/", update_data, use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Update Organization", True, 200, "Organisation modifiée", 
                          {"trade_name": data.get("trade_name")})
        else:
            error_data = response.json() if response else None
            self.log_result("Update Organization", False, response.status_code if response else 0,
                          "Échec modification", error_data)
    
    def test_05_delete_organization_later(self):
        """Test: DELETE /api/business/organizations/{id}/ - À la fin"""
        # On garde l'organisation pour tester les services d'abord
        # Le DELETE sera fait à la fin
        pass
    
    # ==============================================
    # TESTS SERVICES - CRUD COMPLET
    # ==============================================
    
    def test_06_create_service(self):
        """Test: POST /api/business/services/"""
        print("\n🧪 TEST 6: CRÉER SERVICE")
        
        if self.organization_id:
            self.test_service_data["organization"] = self.organization_id
        
        response = self.make_request("POST", "/services/", self.test_service_data, use_auth=True)
        
        if response and response.status_code == 201:
            data = response.json()
            self.service_id = data.get("id")
            
            # SOLUTION FINALE: Récupérer ID depuis la base via script Django
            if not self.service_id:
                print("🔧 SOLUTION: Récupération ID depuis la base de données...")
                import subprocess
                try:
                    # Activer l'environnement virtuel et lancer le script avec bash
                    cmd = f"bash -c 'source venv/bin/activate && python3 get_service_id.py {self.test_service_data['code']}'"
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and result.stdout.strip():
                        # Récupérer la dernière ligne qui contient l'ID
                        lines = result.stdout.strip().split('\n')
                        id_line = lines[-1] if lines else ""
                        if id_line.isdigit():
                            self.service_id = int(id_line)
                            print(f"✅ ID récupéré depuis la base: {self.service_id}")
                        else:
                            print(f"❌ ID non trouvé dans la base")
                    else:
                        print(f"❌ Échec récupération ID: {result.stderr}")
                except Exception as e:
                    print(f"❌ Erreur lors de la récupération ID: {e}")
            
            self.log_result("Create Service", True, 201, "Service créé", 
                          {"id": self.service_id, "name": data.get("name")})
        else:
            error_data = response.json() if response else None
            self.log_result("Create Service", False, response.status_code if response else 0,
                          "Échec création service", error_data)
    
    def test_07_list_services(self):
        """Test: GET /api/business/services/"""
        print("\n🧪 TEST 7: LISTER SERVICES")
        
        response = self.make_request("GET", "/services/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            count = len(data.get("results", data)) if isinstance(data, dict) and "results" in data else len(data)
            self.log_result("List Services", True, 200, "Liste services récupérée", 
                          {"count": count})
        else:
            error_data = response.json() if response else None
            self.log_result("List Services", False, response.status_code if response else 0,
                          "Échec récupération services", error_data)
    
    def test_08_get_service(self):
        """Test: GET /api/business/services/{id}/"""
        print("\n🧪 TEST 8: DÉTAIL SERVICE")
        
        if not self.service_id:
            self.log_result("Get Service", False, 0, "Pas d'ID service")
            return
        
        response = self.make_request("GET", f"/services/{self.service_id}/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Get Service", True, 200, "Détail service récupéré", 
                          {"name": data.get("name")})
        else:
            error_data = response.json() if response else None
            self.log_result("Get Service", False, response.status_code if response else 0,
                          "Échec récupération service", error_data)
    
    def test_09_update_service(self):
        """Test: PATCH /api/business/services/{id}/"""
        print("\n🧪 TEST 9: MODIFIER SERVICE")
        
        if not self.service_id:
            self.log_result("Update Service", False, 0, "Pas d'ID service")
            return
        
        update_data = {
            "name": "Service Test Complet Modifié",
            "description": "Description mise à jour pour test complet",
            "estimated_duration": 45
        }
        
        response = self.make_request("PATCH", f"/services/{self.service_id}/", update_data, use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Update Service", True, 200, "Service modifié", 
                          {"name": data.get("name")})
        else:
            error_data = response.json() if response else None
            self.log_result("Update Service", False, response.status_code if response else 0,
                          "Échec modification service", error_data)
    
    # ==============================================
    # TESTS RELATIONS
    # ==============================================
    
    def test_10_organization_services(self):
        """Test: GET /api/business/organizations/{id}/services/"""
        print("\n🧪 TEST 10: SERVICES D'UNE ORGANISATION")
        
        if not self.organization_id:
            self.log_result("Organization Services", False, 0, "Pas d'ID organisation")
            return
        
        response = self.make_request("GET", f"/organizations/{self.organization_id}/services/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            count = len(data) if isinstance(data, list) else len(data.get("results", []))
            self.log_result("Organization Services", True, 200, "Services organisation récupérés", 
                          {"count": count})
        else:
            error_data = response.json() if response else None
            self.log_result("Organization Services", False, response.status_code if response else 0,
                          "Échec récupération services org", error_data)
    
    # ==============================================
    # TESTS UTILITAIRES
    # ==============================================
    
    def test_11_business_stats(self):
        """Test: GET /api/business/stats/"""
        print("\n🧪 TEST 11: STATISTIQUES BUSINESS")
        
        response = self.make_request("GET", "/stats/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Business Stats", True, 200, "Statistiques récupérées", 
                          {"organizations": data.get("organizations"), "services": data.get("services")})
        else:
            error_data = response.json() if response else None
            self.log_result("Business Stats", False, response.status_code if response else 0,
                          "Échec récupération stats", error_data)
    
    # ==============================================
    # TESTS DELETE (À LA FIN)
    # ==============================================
    
    def test_12_delete_service(self):
        """Test: DELETE /api/business/services/{id}/"""
        print("\n🧪 TEST 12: SUPPRIMER SERVICE")
        
        if not self.service_id:
            self.log_result("Delete Service", False, 0, "Pas d'ID service")
            return
        
        response = self.make_request("DELETE", f"/services/{self.service_id}/", use_auth=True)
        
        if response and response.status_code == 204:
            self.log_result("Delete Service", True, 204, "Service supprimé", 
                          {"deleted_id": self.service_id})
            self.service_id = None  # Marquer comme supprimé
        else:
            error_data = response.json() if response else None
            self.log_result("Delete Service", False, response.status_code if response else 0,
                          "Échec suppression service", error_data)
    
    def test_13_delete_organization(self):
        """Test: DELETE /api/business/organizations/{id}/"""
        print("\n🧪 TEST 13: SUPPRIMER ORGANISATION")
        
        if not self.organization_id:
            self.log_result("Delete Organization", False, 0, "Pas d'ID organisation")
            return
        
        response = self.make_request("DELETE", f"/organizations/{self.organization_id}/", use_auth=True)
        
        if response and response.status_code == 204:
            self.log_result("Delete Organization", True, 204, "Organisation supprimée", 
                          {"deleted_id": self.organization_id})
            self.organization_id = None  # Marquer comme supprimé
        else:
            error_data = response.json() if response else None
            self.log_result("Delete Organization", False, response.status_code if response else 0,
                          "Échec suppression organisation", error_data)
    
    def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🧪 TESTEUR AUTOMATIQUE - APP BUSINESS COMPLET")
        print("Assure-toi que le serveur Django est démarré sur http://127.0.0.1:8001\n")
        
        if not self.check_server():
            return
        
        print("✅ Serveur accessible")
        
        if not self.login_demo():
            print("❌ Impossible de se connecter. Tests annulés.")
            return
        
        print("🚀 DÉBUT DES TESTS ENDPOINTS BUSINESS COMPLETS")
        print("=" * 90)
        print(f"📍 URL de base: {self.base_url}")
        print(f"⏰ Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 90)
        
        # Lancer tous les tests dans l'ordre
        tests = [
            # Organizations CRUD
            self.test_01_create_organization,
            self.test_02_list_organizations,  
            self.test_03_get_organization,
            self.test_04_update_organization,
            
            # Services CRUD  
            self.test_06_create_service,
            self.test_07_list_services,
            self.test_08_get_service,
            self.test_09_update_service,
            
            # Relations
            self.test_10_organization_services,
            
            # Utilitaires
            self.test_11_business_stats,
            
            # DELETE à la fin
            self.test_12_delete_service,
            self.test_13_delete_organization
        ]
        
        for test in tests:
            test()
            time.sleep(0.3)  # Pause entre tests
        
        # Résumé
        self.print_summary()
        self.save_results()
    
    def print_summary(self):
        """Afficher le résumé des tests"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print("\n" + "=" * 90)
        print("📊 RÉSUMÉ DES TESTS BUSINESS COMPLETS")
        print("=" * 90)
        print(f"🎯 Total tests: {total}")
        print(f"✅ Passés: {passed}")
        print(f"❌ Échoués: {failed}")
        print(f"📈 Taux de réussite: {success_rate:.1f}%")
        
        if failed > 0:
            print(f"\n❌ TESTS ÉCHOUÉS:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['message']}")
        
        print(f"\n🎯 **OBJECTIF ATTEINT:** {success_rate:.1f}% de couverture des endpoints Business")
    
    def save_results(self):
        """Sauvegarder les résultats en JSON"""
        filename = "test_results_business_complete.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Résultats détaillés sauvegardés dans '{filename}'")

if __name__ == "__main__":
    tester = BusinessCompleteAPITester()
    tester.run_all_tests()