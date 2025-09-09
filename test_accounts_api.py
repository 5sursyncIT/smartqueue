#!/usr/bin/env python3
"""
Script de test automatique pour tous les endpoints de l'app accounts
Tests tous les endpoints avec des vraies requêtes HTTP
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8001"
API_BASE = f"{BASE_URL}/api/accounts"

class AccountsAPITester:
    def __init__(self):
        self.access_token = None
        self.refresh_token = None
        
        # Utilisateur DEMO pour connexion (existe déjà)
        self.demo_user = {
            "login": "demo@smartqueue.sn",
            "password": "demo123"
        }
        
        # Utilisateur dynamique pour Register (unique à chaque test)
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        phone_suffix = timestamp[-6:]  # Les 6 derniers chiffres
        
        self.test_user_data = {
            "username": f"testuser_{timestamp}",
            "email": f"testuser_{timestamp}@smartqueue.sn", 
            "password": "testpass12345",
            "password_confirm": "testpass12345",
            "phone_number": f"+22170{phone_suffix}0",  # 9 chiffres
            "first_name": "TestUser",
            "last_name": "Auto"
        }
        self.results = []
        
    def log_result(self, test_name, success, status_code, message, response_data=None):
        """Enregistre le résultat d'un test"""
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
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name:<35} | {status_code} | {message}")
    
    def make_request(self, method, endpoint, data=None, use_auth=False):
        """Effectue une requête HTTP"""
        url = f"{API_BASE}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if use_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=headers)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Méthode HTTP non supportée: {method}")
                
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
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur de connexion: {e}")
            return None
    
    def test_01_register(self):
        """Test: POST /api/accounts/register/"""
        print("\n🧪 TEST 1: INSCRIPTION NOUVEAU COMPTE")
        
        response = self.make_request("POST", "/register/", self.test_user_data)
        
        if response and response.status_code == 201:
            data = response.json()
            if data.get("success") and "tokens" in data:
                self.access_token = data["tokens"]["access"]
                self.refresh_token = data["tokens"]["refresh"]
                self.log_result("Register", True, 201, "Inscription réussie", data)
            else:
                self.log_result("Register", False, 201, "Pas de tokens dans réponse", data)
        else:
            error_data = response.json() if response else None
            self.log_result("Register", False, response.status_code if response else 0, 
                          "Échec inscription", error_data)
    
    def test_02_login(self):
        """Test: POST /api/accounts/login/"""
        print("\n🧪 TEST 2: CONNEXION")
        
        # Utiliser l'utilisateur DEMO qui existe déjà
        login_data = self.demo_user
        
        response = self.make_request("POST", "/login/", login_data)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success") and "tokens" in data:
                self.access_token = data["tokens"]["access"]  # Nouveau token
                self.refresh_token = data["tokens"]["refresh"]
                self.log_result("Login", True, 200, "Connexion réussie", data)
            else:
                self.log_result("Login", False, 200, "Pas de tokens", data)
        else:
            error_data = response.json() if response else None
            self.log_result("Login", False, response.status_code if response else 0,
                          "Échec connexion", error_data)
    
    def test_03_profile_get(self):
        """Test: GET /api/accounts/profile/"""
        print("\n🧪 TEST 3: CONSULTER PROFIL")
        
        response = self.make_request("GET", "/profile/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            if "id" in data and "email" in data:
                self.log_result("Profile GET", True, 200, "Profil récupéré", 
                              {"user_id": data.get("id"), "email": data.get("email")})
            else:
                self.log_result("Profile GET", False, 200, "Données profil incomplètes", data)
        else:
            error_data = response.json() if response else None
            self.log_result("Profile GET", False, response.status_code if response else 0,
                          "Échec récupération profil", error_data)
    
    def test_04_profile_update(self):
        """Test: PUT /api/accounts/profile/"""
        print("\n🧪 TEST 4: MODIFIER PROFIL")
        
        update_data = {
            "first_name": "Test Modifié",
            "last_name": "API Modifié",
            "city": "Dakar",
            "address": "Plateau, Dakar, Sénégal",
            "preferred_language": "fr"
        }
        
        response = self.make_request("PUT", "/profile/", update_data, use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            user_data = data.get("user", data)  # Support both formats
            if user_data.get("first_name") == update_data["first_name"]:
                self.log_result("Profile UPDATE", True, 200, "Profil modifié avec succès", 
                              {"first_name": user_data.get("first_name")})
            else:
                self.log_result("Profile UPDATE", False, 200, "Modification non prise en compte", data)
        else:
            error_data = response.json() if response else None
            self.log_result("Profile UPDATE", False, response.status_code if response else 0,
                          "Échec modification profil", error_data)
    
    def test_05_refresh_token(self):
        """Test: POST /api/accounts/token/refresh/"""
        print("\n🧪 TEST 5: RENOUVELER TOKEN")
        
        if not self.refresh_token:
            self.log_result("Token REFRESH", False, 0, "Pas de refresh token disponible")
            return
        
        refresh_data = {"refresh": self.refresh_token}
        response = self.make_request("POST", "/token/refresh/", refresh_data)
        
        if response and response.status_code == 200:
            data = response.json()
            if "access" in data:
                old_token = self.access_token[:20] + "..."
                self.access_token = data["access"]  # Nouveau token
                new_token = self.access_token[:20] + "..."
                self.log_result("Token REFRESH", True, 200, "Token renouvelé", 
                              {"old": old_token, "new": new_token})
            else:
                self.log_result("Token REFRESH", False, 200, "Pas de nouveau token", data)
        else:
            error_data = response.json() if response else None
            self.log_result("Token REFRESH", False, response.status_code if response else 0,
                          "Échec renouvellement token", error_data)
    
    def test_06_change_password(self):
        """Test: POST /api/accounts/change-password/"""
        print("\n🧪 TEST 6: CHANGER MOT DE PASSE")
        
        new_password = "nouveaumotdepasse123"
        password_data = {
            "current_password": self.demo_user["password"],  # Mot de passe demo actuel
            "new_password": new_password,
            "new_password_confirm": new_password
        }
        
        response = self.make_request("POST", "/change-password/", password_data, use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("success"):
                # Mettre à jour le mot de passe demo pour les futurs tests
                self.demo_user["password"] = new_password
                self.log_result("Change Password", True, 200, "Mot de passe changé", data)
            else:
                self.log_result("Change Password", False, 200, "Changement non confirmé", data)
        else:
            error_data = response.json() if response else None
            self.log_result("Change Password", False, response.status_code if response else 0,
                          "Échec changement mot de passe", error_data)
    
    def test_07_status(self):
        """Test: GET /api/accounts/status/"""
        print("\n🧪 TEST 7: STATUT CONNEXION")
        
        response = self.make_request("GET", "/status/", use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            if data.get("authenticated") == True:
                self.log_result("Auth Status", True, 200, "Statut confirmé - connecté", data)
            else:
                self.log_result("Auth Status", False, 200, "Statut incorrect", data)
        else:
            error_data = response.json() if response else None
            self.log_result("Auth Status", False, response.status_code if response else 0,
                          "Échec vérification statut", error_data)
    
    def test_08_send_verification_code(self):
        """Test: POST /api/accounts/send-verification-code/"""
        print("\n🧪 TEST 8: ENVOYER CODE VÉRIFICATION SMS")
        
        response = self.make_request("POST", "/send-verification-code/", {}, use_auth=True)
        
        # Ce test peut échouer si SMS pas configuré, c'est normal
        if response:
            data = response.json() if response.content else {}
            success = response.status_code in [200, 201]
            message = "Code SMS envoyé" if success else f"SMS non configuré (normal) - {data}"
            self.log_result("Send SMS Code", success, response.status_code, message, data)
        else:
            self.log_result("Send SMS Code", False, 0, "Pas de réponse serveur")
    
    def test_09_verify_phone(self):
        """Test: POST /api/accounts/verify-phone/"""
        print("\n🧪 TEST 9: VÉRIFIER CODE SMS")
        
        verify_data = {"code": "123456"}  # Code bidon
        response = self.make_request("POST", "/verify-phone/", verify_data, use_auth=True)
        
        if response:
            data = response.json() if response.content else {}
            # Code bidon donc échec attendu
            if response.status_code == 400:
                self.log_result("Verify Phone", True, 400, "Code invalide (attendu)", data)
            elif response.status_code == 200:
                self.log_result("Verify Phone", True, 200, "Vérification réussie", data)
            else:
                self.log_result("Verify Phone", False, response.status_code, "Réponse inattendue", data)
        else:
            self.log_result("Verify Phone", False, 0, "Pas de réponse serveur")
    
    def test_10_logout(self):
        """Test: POST /api/accounts/logout/"""
        print("\n🧪 TEST 10: DÉCONNEXION")
        
        response = self.make_request("POST", "/logout/", {}, use_auth=True)
        
        if response and response.status_code == 200:
            data = response.json()
            self.access_token = None  # Token invalidé
            self.log_result("Logout", True, 200, "Déconnexion réussie", data)
        else:
            error_data = response.json() if response else None
            self.log_result("Logout", False, response.status_code if response else 0,
                          "Échec déconnexion", error_data)
    
    def test_11_password_reset_request(self):
        """Test: POST /api/accounts/password-reset-request/"""
        print("\n🧪 TEST 11: DEMANDER RESET MOT DE PASSE")
        
        reset_data = {"phone_number": self.test_user_data["phone_number"]}
        response = self.make_request("POST", "/password-reset-request/", reset_data)
        
        if response:
            data = response.json() if response.content else {}
            success = response.status_code in [200, 201]
            message = "Reset demandé" if success else f"SMS non configuré (normal) - {data}"
            self.log_result("Password Reset Request", success, response.status_code, message, data)
        else:
            self.log_result("Password Reset Request", False, 0, "Pas de réponse serveur")
    
    def test_12_password_reset(self):
        """Test: POST /api/accounts/password-reset/"""
        print("\n🧪 TEST 12: CONFIRMER RESET MOT DE PASSE")
        
        reset_data = {
            "phone_number": self.test_user_data["phone_number"],
            "code": "123456",  # Code bidon
            "new_password": "resetpassword123",
            "confirm_password": "resetpassword123"
        }
        
        response = self.make_request("POST", "/password-reset/", reset_data)
        
        if response:
            data = response.json() if response.content else {}
            # Code bidon donc échec attendu
            if response.status_code == 400:
                self.log_result("Password Reset", True, 400, "Code invalide (attendu)", data)
            elif response.status_code == 200:
                self.log_result("Password Reset", True, 200, "Reset confirmé", data)
            else:
                self.log_result("Password Reset", False, response.status_code, "Réponse inattendue", data)
        else:
            self.log_result("Password Reset", False, 0, "Pas de réponse serveur")
    
    def run_all_tests(self):
        """Lance tous les tests dans l'ordre"""
        print("🚀 DÉBUT DES TESTS ENDPOINTS ACCOUNTS")
        print("=" * 80)
        print(f"📍 URL de base: {API_BASE}")
        print(f"⏰ Heure: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # Ordre logique des tests
        test_methods = [
            self.test_01_register,
            self.test_02_login,
            self.test_03_profile_get,
            self.test_04_profile_update,
            self.test_05_refresh_token,
            self.test_06_change_password,
            self.test_07_status,
            self.test_08_send_verification_code,
            self.test_09_verify_phone,
            self.test_10_logout,
            self.test_11_password_reset_request,
            self.test_12_password_reset,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                test_name = test_method.__name__.replace("test_", "").replace("_", " ").title()
                self.log_result(test_name, False, 0, f"Exception: {str(e)}")
        
        self.print_summary()
    
    def print_summary(self):
        """Affiche le résumé des tests"""
        print("\n" + "=" * 80)
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 80)
        
        total = len(self.results)
        passed = len([r for r in self.results if r["success"]])
        failed = total - passed
        
        print(f"🎯 Total tests: {total}")
        print(f"✅ Passés: {passed}")
        print(f"❌ Échoués: {failed}")
        print(f"📈 Taux de réussite: {passed/total*100:.1f}%")
        
        if failed > 0:
            print("\n❌ TESTS ÉCHOUÉS:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['test']}: {result['message']}")
        
        print("\n💾 Résultats détaillés sauvegardés dans 'test_results.json'")
        
        # Sauvegarder les résultats
        with open('test_results_accounts.json', 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

def main():
    """Point d'entrée principal"""
    print("🧪 TESTEUR AUTOMATIQUE - APP ACCOUNTS")
    print("Assure-toi que le serveur Django est démarré sur http://127.0.0.1:8001")
    print()
    
    # Vérifier que le serveur est accessible
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Serveur accessible")
        else:
            print(f"⚠️ Serveur répond avec code {response.status_code}")
    except requests.exceptions.RequestException:
        print("❌ ERREUR: Serveur non accessible. Démarre le serveur avec:")
        print("   python manage.py runserver 8001")
        sys.exit(1)
    
    # Lancer les tests
    tester = AccountsAPITester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()