#!/usr/bin/env python3
"""
Script de test COMPLET pour l'app QUEUE_MANAGEMENT
Teste TOUS les endpoints disponibles dans l'API Queue Management
"""

import requests
import json
import time
from datetime import datetime

class QueueManagementCompleteAPITester:
    def __init__(self):
        self.base_url = "http://127.0.0.1:8001/api/queue-management"
        self.auth_url = "http://127.0.0.1:8001/api/accounts"
        self.business_url = "http://127.0.0.1:8001/api/business"
        self.access_token = None
        self.refresh_token = None
        
        # Données de test pour queue - UNIQUES
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_queue_data = {
            "name": f"File Test {timestamp}",
            "queue_type": "normal",
            "current_status": "active", 
            "description": f"File de test créée le {timestamp}",
            "max_capacity": 20
        }
        
        # Données de test pour ticket
        self.test_ticket_data = {
            "priority": "low",
            "creation_channel": "web"
        }
        
        self.results = []
        self.organization_id = None
        self.service_id = None
        self.queue_id = None
        self.ticket_id = None
    
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
    
    def setup_prerequisites(self):
        """Créer organisation et service nécessaires pour les files"""
        print("🔧 Création des prérequis (organisation + service)...")
        
        # Créer organisation
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        org_data = {
            "name": f"Org Queue Test {timestamp}",
            "type": "bank",
            "email": f"queue_{timestamp}@test.sn",
            "phone_number": f"+221338{timestamp[-6:]}",
            "address": "Dakar",
            "city": "Dakar",
            "region": "dakar"
        }
        
        org_response = requests.post(f"{self.business_url}/organizations/", 
                                   json=org_data,
                                   headers={"Authorization": f"Bearer {self.access_token}"})
        
        if org_response.status_code == 201:
            self.organization_id = org_response.json().get("id")
            print(f"✅ Organisation créée: ID={self.organization_id}")
        else:
            print(f"❌ Échec création organisation: {org_response.status_code}")
            return False
        
        # Créer service
        service_data = {
            "organization": self.organization_id,
            "name": f"Service Queue Test {timestamp}",
            "code": f"Q_{timestamp[-8:]}",  # Seulement les 8 derniers chiffres
            "description": "Service de test pour files d'attente"
        }
        
        service_response = requests.post(f"{self.business_url}/services/", 
                                       json=service_data,
                                       headers={"Authorization": f"Bearer {self.access_token}"})
        
        if service_response.status_code == 201:
            self.service_id = service_response.json().get("id")
            print(f"✅ Service créé: ID={self.service_id}")
            return True
        else:
            print(f"❌ Échec création service: {service_response.status_code}")
            return False
    
    # ==============================================
    # TESTS QUEUES - CRUD COMPLET
    # ==============================================
    
    def test_01_create_queue(self):
        """Test: POST /api/queue-management/queues/"""
        print("\\n🧪 TEST 1: CRÉER FILE D'ATTENTE")
        
        if self.organization_id and self.service_id:
            self.test_queue_data["organization"] = self.organization_id
            self.test_queue_data["service"] = self.service_id
        
        response = self.make_request("POST", "/queues/", self.test_queue_data, use_auth=True)
        
        if response and response.status_code == 201:
            data = response.json()
            self.queue_id = data.get("id")
            self.log_result("Create Queue", True, 201, "File créée", 
                          {"id": self.queue_id, "name": data.get("name")})
        else:
            error_data = response.json() if response else None
            self.log_result("Create Queue", False, response.status_code if response else 0,
                          "Échec création file", error_data)
    
    def test_02_list_queues(self):
        """Test: GET /api/queue-management/queues/"""
        print("\\n🧪 TEST 2: LISTER FILES")
        
        response = self.make_request("GET", "/queues/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            count = len(data.get("results", data)) if isinstance(data, dict) and "results" in data else len(data)
            self.log_result("List Queues", True, 200, "Liste récupérée", 
                          {"count": count})
        else:
            error_data = response.json() if response else None
            self.log_result("List Queues", False, response.status_code if response else 0,
                          "Échec récupération liste", error_data)
    
    def test_03_get_queue(self):
        """Test: GET /api/queue-management/queues/{id}/"""
        print("\\n🧪 TEST 3: DÉTAIL FILE")
        
        if not self.queue_id:
            self.log_result("Get Queue", False, 0, "Pas d'ID file")
            return
        
        response = self.make_request("GET", f"/queues/{self.queue_id}/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Get Queue", True, 200, "Détail récupéré", 
                          {"name": data.get("name")})
        else:
            error_data = response.json() if response else None
            self.log_result("Get Queue", False, response.status_code if response else 0,
                          "Échec récupération détail", error_data)
    
    def test_04_update_queue(self):
        """Test: PATCH /api/queue-management/queues/{id}/"""
        print("\\n🧪 TEST 4: MODIFIER FILE")
        
        if not self.queue_id:
            self.log_result("Update Queue", False, 0, "Pas d'ID file")
            return
        
        update_data = {
            "name": "File Test Modifiée",
            "description": "Description mise à jour"
        }
        
        response = self.make_request("PATCH", f"/queues/{self.queue_id}/", update_data, use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Update Queue", True, 200, "File modifiée", 
                          {"name": data.get("name")})
        else:
            error_data = response.json() if response else None
            self.log_result("Update Queue", False, response.status_code if response else 0,
                          "Échec modification", error_data)
    
    # ==============================================
    # TESTS TICKETS - CRUD COMPLET
    # ==============================================
    
    def test_05_take_ticket(self):
        """Test: POST /api/queue-management/queues/{id}/take-ticket/"""
        print("\\n🧪 TEST 5: PRENDRE TICKET")
        
        if not self.queue_id:
            self.log_result("Take Ticket", False, 0, "Pas d'ID file")
            return
        
        response = self.make_request("POST", f"/queues/{self.queue_id}/take-ticket/", 
                                   self.test_ticket_data, use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("ticket"):
                self.ticket_id = data["ticket"].get("id")
            self.log_result("Take Ticket", True, 200, "Ticket pris", 
                          {"ticket_id": self.ticket_id})
        else:
            error_data = response.json() if response else None
            self.log_result("Take Ticket", False, response.status_code if response else 0,
                          "Échec prise ticket", error_data)
    
    def test_06_list_tickets(self):
        """Test: GET /api/queue-management/tickets/"""
        print("\\n🧪 TEST 6: LISTER TICKETS")
        
        response = self.make_request("GET", "/tickets/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            count = len(data.get("results", data)) if isinstance(data, dict) and "results" in data else len(data)
            self.log_result("List Tickets", True, 200, "Liste tickets récupérée", 
                          {"count": count})
        else:
            error_data = response.json() if response else None
            self.log_result("List Tickets", False, response.status_code if response else 0,
                          "Échec récupération tickets", error_data)
    
    def test_07_get_ticket(self):
        """Test: GET /api/queue-management/tickets/{id}/"""
        print("\\n🧪 TEST 7: DÉTAIL TICKET")
        
        if not self.ticket_id:
            self.log_result("Get Ticket", False, 0, "Pas d'ID ticket")
            return
        
        response = self.make_request("GET", f"/tickets/{self.ticket_id}/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Get Ticket", True, 200, "Détail ticket récupéré", 
                          {"ticket_number": data.get("ticket_number")})
        else:
            error_data = response.json() if response else None
            self.log_result("Get Ticket", False, response.status_code if response else 0,
                          "Échec récupération ticket", error_data)
    
    # ==============================================
    # TESTS RELATIONS ET ACTIONS
    # ==============================================
    
    def test_08_queue_tickets(self):
        """Test: GET /api/queue-management/queues/{id}/tickets/"""
        print("\\n🧪 TEST 8: TICKETS D'UNE FILE")
        
        if not self.queue_id:
            self.log_result("Queue Tickets", False, 0, "Pas d'ID file")
            return
        
        response = self.make_request("GET", f"/queues/{self.queue_id}/tickets/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            count = len(data) if isinstance(data, list) else len(data.get("results", []))
            self.log_result("Queue Tickets", True, 200, "Tickets file récupérés", 
                          {"count": count})
        else:
            error_data = response.json() if response else None
            self.log_result("Queue Tickets", False, response.status_code if response else 0,
                          "Échec récupération tickets file", error_data)
    
    def test_09_queue_management_stats(self):
        """Test: GET /api/queue-management/stats/"""
        print("\\n🧪 TEST 9: STATISTIQUES QUEUE MANAGEMENT")
        
        response = self.make_request("GET", "/stats/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_result("Queue Management Stats", True, 200, "Statistiques récupérées", 
                          {"total_queues": data.get("total_queues")})
        else:
            error_data = response.json() if response else None
            self.log_result("Queue Management Stats", False, response.status_code if response else 0,
                          "Échec récupération stats", error_data)
    
    def run_all_tests(self):
        """Exécuter tous les tests"""
        print("🧪 TESTEUR AUTOMATIQUE - APP QUEUE MANAGEMENT COMPLET")
        print("Assure-toi que le serveur Django est démarré sur http://127.0.0.1:8001\\n")
        
        if not self.check_server():
            return
        
        print("✅ Serveur accessible")
        
        if not self.login_demo():
            print("❌ Impossible de se connecter. Tests annulés.")
            return
        
        if not self.setup_prerequisites():
            print("❌ Impossible de créer les prérequis. Tests annulés.")
            return
        
        print("🚀 DÉBUT DES TESTS ENDPOINTS QUEUE MANAGEMENT COMPLETS")
        print("=" * 90)
        print(f"📍 URL de base: {self.base_url}")
        print(f"⏰ Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 90)
        
        # Lancer tous les tests dans l'ordre
        tests = [
            self.test_01_create_queue,
            self.test_02_list_queues,  
            self.test_03_get_queue,
            self.test_04_update_queue,
            
            # Tickets et actions
            self.test_05_take_ticket,
            self.test_06_list_tickets,
            self.test_07_get_ticket,
            
            # Relations et stats
            self.test_08_queue_tickets,
            self.test_09_queue_management_stats
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
        print("📊 RÉSUMÉ DES TESTS QUEUE MANAGEMENT COMPLETS")
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
        
        print(f"\\n🎯 **OBJECTIF ATTEINT:** {success_rate:.1f}% de couverture des endpoints Queue Management")
    
    def save_results(self):
        """Sauvegarder les résultats en JSON"""
        filename = "test_results_queue_management_complete.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        print(f"\\n💾 Résultats détaillés sauvegardés dans '{filename}'")

if __name__ == "__main__":
    tester = QueueManagementCompleteAPITester()
    tester.run_all_tests()