# apps/accounts/views.py
"""
Vues pour l'authentification SmartQueue
APIs REST pour la gestion des comptes utilisateurs
"""

from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiResponse
from django.contrib.auth import login
from django.utils import timezone
from datetime import timedelta
import random
import string
from .models import User
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, CustomTokenObtainPairSerializer,
    UserProfileSerializer, ChangePasswordSerializer, PhoneVerificationSerializer,
    RequestPasswordResetSerializer, PasswordResetSerializer
)


@extend_schema(
    summary="Inscription d'un nouvel utilisateur",
    description="Créer un nouveau compte SmartQueue avec validation sénégalaise",
    tags=["Authentication"],
    request=UserRegistrationSerializer,
    responses={
        201: OpenApiResponse(description="Inscription réussie avec tokens JWT"),
        400: OpenApiResponse(description="Erreurs de validation")
    }
)
class UserRegistrationView(APIView):
    """
    Inscription d'un nouvel utilisateur
    
    POST /api/auth/register/
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Générer des tokens JWT
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'success': True,
                'message': 'Compte créé avec succès!',
                'user': {
                    'id': user.id,
                    'phone_number': user.phone_number,
                    'full_name': user.get_full_name(),
                    'user_type': user.user_type,
                    'preferred_language': user.preferred_language
                },
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Connexion utilisateur",
    description="Connexion par numéro de téléphone ou email",
    tags=["Authentication"],
    request=UserLoginSerializer,
    responses={
        200: OpenApiResponse(description="Connexion réussie avec tokens JWT"),
        400: OpenApiResponse(description="Erreurs de validation")
    }
)
class UserLoginView(APIView):
    """
    Connexion utilisateur
    
    POST /api/auth/login/
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Mettre à jour la dernière connexion
            user.last_login = timezone.now()
            user.last_ip_address = request.META.get('REMOTE_ADDR')
            user.save()
            
            # Générer des tokens JWT
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'success': True,
                'message': 'Connexion réussie!',
                'user': {
                    'id': user.id,
                    'phone_number': user.phone_number,
                    'full_name': user.get_full_name(),
                    'user_type': user.user_type,
                    'preferred_language': user.preferred_language,
                    'is_phone_verified': user.is_phone_verified
                },
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Connexion JWT",
    description="Obtenir des tokens JWT (alternative à login)",
    tags=["Authentication"]
)
class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Vue personnalisée pour obtenir les JWT tokens
    
    POST /api/auth/token/
    """
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema_view(
    get=extend_schema(
        summary="Consulter son profil",
        description="Récupérer les informations du profil utilisateur connecté",
        tags=["Profile"]
    ),
    put=extend_schema(
        summary="Modifier son profil",
        description="Mettre à jour les informations du profil",
        tags=["Profile"]
    ),
    patch=extend_schema(
        summary="Modifier partiellement son profil",
        description="Mise à jour partielle du profil",
        tags=["Profile"]
    )
)
class UserProfileView(RetrieveUpdateAPIView):
    """
    Consultation et modification du profil utilisateur
    
    GET /api/auth/profile/
    PUT/PATCH /api/auth/profile/
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'message': 'Profil mis à jour avec succès!',
                'user': serializer.data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Changer le mot de passe",
    description="Changer son mot de passe en fournissant l'ancien",
    tags=["Profile"],
    request=ChangePasswordSerializer,
    responses={
        200: OpenApiResponse(description="Mot de passe changé avec succès"),
        400: OpenApiResponse(description="Erreurs de validation")
    }
)
class ChangePasswordView(APIView):
    """
    Changer le mot de passe
    
    POST /api/auth/change-password/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if serializer.is_valid():
            serializer.save()
            
            return Response({
                'success': True,
                'message': 'Mot de passe changé avec succès!'
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Vérifier le numéro de téléphone",
    description="Vérifier le numéro avec un code SMS",
    tags=["Verification"],
    request=PhoneVerificationSerializer,
    responses={
        200: OpenApiResponse(description="Téléphone vérifié avec succès"),
        400: OpenApiResponse(description="Code invalide ou expiré")
    }
)
class PhoneVerificationView(APIView):
    """
    Vérification du numéro de téléphone par SMS
    
    POST /api/auth/verify-phone/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PhoneVerificationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            code = serializer.validated_data['verification_code']
            
            # Vérifier le code et qu'il n'est pas expiré
            if (user.verification_code == code and 
                user.verification_code_expires and
                timezone.now() <= user.verification_code_expires):
                
                # Marquer comme vérifié
                user.is_phone_verified = True
                user.verification_code = None
                user.verification_code_expires = None
                user.save()
                
                return Response({
                    'success': True,
                    'message': 'Numéro de téléphone vérifié avec succès!'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Code de vérification invalide ou expiré.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Envoyer un code de vérification SMS",
    description="Envoyer un nouveau code de vérification par SMS",
    tags=["Verification"],
    responses={
        200: OpenApiResponse(description="Code SMS envoyé avec succès"),
        400: OpenApiResponse(description="Erreur d'envoi")
    }
)
class SendVerificationCodeView(APIView):
    """
    Envoyer un code de vérification SMS
    
    POST /api/auth/send-verification-code/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        # Générer un code à 6 chiffres
        code = ''.join(random.choices(string.digits, k=6))
        
        # Sauvegarder le code avec expiration (15 minutes)
        user.verification_code = code
        user.verification_code_expires = timezone.now() + timedelta(minutes=15)
        user.save()
        
        # TODO: Envoyer le SMS réel
        # Pour l'instant, on retourne le code en développement
        return Response({
            'success': True,
            'message': 'Code de vérification envoyé!',
            'debug_code': code if request.user.is_superuser else None  # Seulement pour les admins
        })


@extend_schema(
    summary="Demander une réinitialisation de mot de passe",
    description="Envoyer un code SMS pour réinitialiser le mot de passe",
    tags=["Password Reset"],
    request=RequestPasswordResetSerializer,
    responses={
        200: OpenApiResponse(description="Code de reset envoyé par SMS"),
        400: OpenApiResponse(description="Email non trouvé")
    }
)
class RequestPasswordResetView(APIView):
    """
    Demander une réinitialisation de mot de passe
    
    POST /api/auth/password-reset-request/
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            user = User.objects.get(phone_number=phone_number, is_active=True)
            
            # Générer un code à 6 chiffres
            reset_code = ''.join(random.choices(string.digits, k=6))
            
            # Sauvegarder le code avec expiration (30 minutes)
            user.verification_code = reset_code
            user.verification_code_expires = timezone.now() + timedelta(minutes=30)
            user.save()
            
            # TODO: Envoyer le SMS réel
            return Response({
                'success': True,
                'message': 'Code de réinitialisation envoyé par SMS!',
                'debug_code': reset_code if request.user and request.user.is_superuser else None
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Réinitialiser le mot de passe",
    description="Réinitialiser le mot de passe avec un code SMS",
    tags=["Password Reset"],
    request=PasswordResetSerializer,
    responses={
        200: OpenApiResponse(description="Mot de passe réinitialisé avec succès"),
        400: OpenApiResponse(description="Code invalide ou expiré")
    }
)
class PasswordResetView(APIView):
    """
    Réinitialiser le mot de passe avec un code
    
    POST /api/auth/password-reset/
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            reset_code = serializer.validated_data['verification_code']
            new_password = serializer.validated_data['new_password']
            
            try:
                user = User.objects.get(phone_number=phone_number, is_active=True)
                
                # Vérifier le code et qu'il n'est pas expiré
                if (user.verification_code == reset_code and 
                    user.verification_code_expires and
                    timezone.now() <= user.verification_code_expires):
                    
                    # Changer le mot de passe
                    user.set_password(new_password)
                    user.verification_code = None
                    user.verification_code_expires = None
                    user.save()
                    
                    return Response({
                        'success': True,
                        'message': 'Mot de passe réinitialisé avec succès!'
                    })
                else:
                    return Response({
                        'success': False,
                        'error': 'Code de réinitialisation invalide ou expiré.'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            except User.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Utilisateur introuvable.'
                }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Déconnexion",
    description="Blacklister le token JWT (déconnexion)",
    tags=["Authentication"]
)
class LogoutView(APIView):
    """
    Déconnexion (blacklist du token)
    
    POST /api/auth/logout/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                
            return Response({
                'success': True,
                'message': 'Déconnexion réussie!'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Erreur lors de la déconnexion.'
            }, status=status.HTTP_400_BAD_REQUEST)


# ========================================
# VUES UTILITAIRES
# ========================================

@extend_schema(
    summary="Vérifier le statut d'authentification",
    description="Vérifier si l'utilisateur est connecté",
    tags=["Utilities"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def auth_status(request):
    """
    Vérifier le statut d'authentification
    
    GET /api/auth/status/
    """
    user = request.user
    
    return Response({
        'authenticated': True,
        'user': {
            'id': user.id,
            'phone_number': user.phone_number,
            'full_name': user.get_full_name(),
            'user_type': user.user_type,
            'preferred_language': user.preferred_language,
            'is_phone_verified': user.is_phone_verified,
            'is_active': user.is_active
        }
    })


@extend_schema(
    summary="Supprimer son compte",
    description="Supprimer définitivement son compte utilisateur",
    tags=["Profile"]
)
@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_account(request):
    """
    Supprimer son compte utilisateur
    
    DELETE /api/auth/delete-account/
    """
    user = request.user
    
    # Vérifier le mot de passe pour confirmation
    password = request.data.get('password')
    if not password or not user.check_password(password):
        return Response({
            'success': False,
            'error': 'Mot de passe requis pour supprimer le compte.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Désactiver au lieu de supprimer (pour préserver l'historique)
    user.is_active = False
    user.email = f"deleted_{user.id}@smartqueue.sn"
    user.save()
    
    return Response({
        'success': True,
        'message': 'Compte supprimé avec succès!'
    })