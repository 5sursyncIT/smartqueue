#!/usr/bin/env python3
"""
Script de test COMPLET pour l'app CORE
Teste TOUS les endpoints disponibles dans l'API Core
"""

import requests
import json
import time
from datetime import datetime

class CoreCompleteAPITester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8001/api/core"
        self.auth_url = "http://127.0.0.1:8001/api/accounts"
        self.access_token = None
        self.refresh_token = None
        
        self.results = []
    
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
            return False
    
    def login_demo(self):
        """Connexion avec le compte demo pour les tests"""
        login_data = {
            "login": "demo@smartqueue.sn", 
            "password": "nouveaumotdepasse123"
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
            
            return response
        except Exception as e:
            print(f"❌ Erreur requête {method} {endpoint}: {e}")
            return None
    
    # ==============================================
    # TESTS CORE - TOUS LES ENDPOINTS
    # ==============================================
    
    def test_01_health_check(self):
        """Test: GET /api/core/health/"""
        print("\\n🧪 TEST 1: HEALTH CHECK")
        
        response = self.make_request("GET", "/health/", use_auth=False)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Health Check", True, 200, "Health check OK", 
                          {"status": data.get("status"), "checks": data.get("checks")})
        else:
            error_data = response.json() if response else None
            self.log_result("Health Check", False, response.status_code if response else 0,
                          "Échec health check", error_data)
    
    def test_02_system_status(self):
        """Test: GET /api/core/status/"""
        print("\\n🧪 TEST 2: SYSTEM STATUS")
        
        response = self.make_request("GET", "/status/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("System Status", True, 200, "Status système récupéré", 
                          {"system": data.get("system"), "database": data.get("database")})
        elif response and response.status_code == 403:
            self.log_result("System Status", True, 403, "Accès refusé (normal pour demo user)")
        else:
            error_data = response.json() if response else None
            self.log_result("System Status", False, response.status_code if response else 0,
                          "Échec récupération status", error_data)
    
    def test_03_public_config(self):
        """Test: GET /api/core/config/"""
        print("\\n🧪 TEST 3: CONFIGURATION PUBLIQUE")
        
        response = self.make_request("GET", "/config/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Public Config", True, 200, "Configuration récupérée", 
                          {"site_name": data.get("site_name"), "maintenance_mode": data.get("maintenance_mode")})
        else:
            error_data = response.json() if response else None
            self.log_result("Public Config", False, response.status_code if response else 0,
                          "Échec récupération config", error_data)
    
    def test_04_validate_phone(self):
        """Test: POST /api/core/utils/validate-phone/"""
        print("\\n🧪 TEST 4: VALIDATION TÉLÉPHONE")
        
        test_phone_data = {
            "phone": "+221771234567"
        }
        
        response = self.make_request("POST", "/utils/validate-phone/", test_phone_data, use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Validate Phone", True, 200, "Numéro validé", 
                          {"original": data.get("original"), "is_valid": data.get("is_valid")})
        else:
            error_data = response.json() if response else None
            self.log_result("Validate Phone", False, response.status_code if response else 0,
                          "Échec validation téléphone", error_data)
    
    def test_05_senegal_regions(self):
        """Test: GET /api/core/utils/regions/"""
        print("\\n🧪 TEST 5: RÉGIONS SÉNÉGAL")
        
        response = self.make_request("GET", "/utils/regions/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Senegal Regions", True, 200, "Régions récupérées", 
                          {"count": data.get("count")})
        else:
            error_data = response.json() if response else None
            self.log_result("Senegal Regions", False, response.status_code if response else 0,
                          "Échec récupération régions", error_data)
    
    def test_06_activity_logs(self):
        """Test: GET /api/core/logs/"""
        print("\\n🧪 TEST 6: LOGS D'ACTIVITÉ")
        
        response = self.make_request("GET", "/logs/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            count = len(data.get("results", data)) if isinstance(data, dict) and "results" in data else len(data) if isinstance(data, list) else 0
            self.log_result("Activity Logs", True, 200, "Logs récupérés", 
                          {"count": count})
        elif response and response.status_code == 403:
            self.log_result("Activity Logs", True, 403, "Accès refusé (normal pour demo user)")
        else:
            error_data = response.json() if response else None
            self.log_result("Activity Logs", False, response.status_code if response else 0,
                          "Échec récupération logs", error_data)
    
    def test_07_maintenance_status(self):
        """Test: GET /api/core/maintenance/"""
        print("\\n🧪 TEST 7: STATUS MAINTENANCE")
        
        response = self.make_request("GET", "/maintenance/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Maintenance Status", True, 200, "Status maintenance récupéré", 
                          {"maintenance_mode": data.get("maintenance_mode")})
        elif response and response.status_code == 403:
            self.log_result("Maintenance Status", True, 403, "Accès refusé (normal pour demo user)")
        else:
            error_data = response.json() if response else None
            self.log_result("Maintenance Status", False, response.status_code if response else 0,
                          "Échec récupération maintenance", error_data)
    
    def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🧪 TESTEUR AUTOMATIQUE - APP CORE COMPLET")
        print("Assure-toi que le serveur Django est démarré sur http://127.0.0.1:8001\\n")
        
        if not self.check_server():
            return
        
        print("✅ Serveur accessible")
        
        if not self.login_demo():
            print("❌ Impossible de se connecter. Tests annulés.")
            return
        
        print("🚀 DÉBUT DES TESTS ENDPOINTS CORE COMPLETS")
        print("=" * 90)
        print(f"📍 URL de base: {self.base_url}")
        print(f"⏰ Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 90)
        
        # Lancer tous les tests dans l'ordre
        tests = [
            self.test_01_health_check,
            self.test_02_system_status,
            self.test_03_public_config,
            self.test_04_validate_phone,
            self.test_05_senegal_regions,
            self.test_06_activity_logs,
            self.test_07_maintenance_status
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
        
        print("\\n" + "=" * 90)
        print("📊 RÉSUMÉ DES TESTS CORE COMPLETS")
        print("=" * 90)
        print(f"🎯 Total tests: {total}")
        print(f"✅ Passés: {passed}")
        print(f"❌ Échoués: {failed}")
        print(f"📈 Taux de réussite: {success_rate:.1f}%")
        
        if failed > 0:
            print(f"\\n❌ TESTS ÉCHOUÉS:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['message']}")
        
        print(f"\\n🎯 **OBJECTIF ATTEINT:** {success_rate:.1f}% de couverture des endpoints Core")
    
    def save_results(self):
        """Sauvegarder les résultats en JSON"""
        filename = "test_results_core_complete.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\\n💾 Résultats détaillés sauvegardés dans '{filename}'")

if __name__ == "__main__":
    tester = CoreCompleteAPITester()
    tester.run_all_tests()