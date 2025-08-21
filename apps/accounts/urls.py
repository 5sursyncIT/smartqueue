# apps/accounts/urls.py
"""
Routes pour les APIs d'authentification SmartQueue
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView, UserLoginView, CustomTokenObtainPairView,
    UserProfileView, ChangePasswordView, PhoneVerificationView,
    SendVerificationCodeView, RequestPasswordResetView, PasswordResetView,
    LogoutView, auth_status, delete_account
)

urlpatterns = [
    # ========================================
    # AUTHENTIFICATION
    # ========================================
    
    # Inscription et connexion
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', LogoutView.as_view(), name='user-logout'),
    
    # JWT Tokens
    path('token/', CustomTokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # ========================================
    # GESTION DE PROFIL
    # ========================================
    
    # Profil utilisateur
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('delete-account/', delete_account, name='delete-account'),
    
    # ========================================
    # VÉRIFICATION TÉLÉPHONE
    # ========================================
    
    # Vérification SMS
    path('verify-phone/', PhoneVerificationView.as_view(), name='verify-phone'),
    path('send-verification-code/', SendVerificationCodeView.as_view(), name='send-verification-code'),
    
    # ========================================
    # RÉINITIALISATION MOT DE PASSE
    # ========================================
    
    # Reset password par SMS
    path('password-reset-request/', RequestPasswordResetView.as_view(), name='password-reset-request'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    
    # ========================================
    # UTILITAIRES
    # ========================================
    
    # Statut de connexion
    path('status/', auth_status, name='auth-status'),
]