# apps/accounts/serializers.py
"""
Serializers pour l'authentification SmartQueue
Gestion des comptes utilisateurs sénégalais
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
import re
from .models import User


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'inscription d'un nouveau utilisateur
    
    Usage : POST /api/auth/register/
    Validation spécifique au contexte sénégalais
    """
    
    password = serializers.CharField(
        write_only=True,
        min_length=6,
        help_text="Mot de passe (minimum 6 caractères)"
    )
    
    password_confirm = serializers.CharField(
        write_only=True,
        help_text="Confirmation du mot de passe"
    )
    
    class Meta:
        model = User
        fields = [
            # Obligatoires
            'phone_number', 'first_name', 'last_name', 'user_type',
            'password', 'password_confirm',
            
            # Optionnels
            'email', 'preferred_language', 'city', 'address',
            'date_of_birth', 'gender'
        ]
        extra_kwargs = {
            'phone_number': {'help_text': 'Format: +221XXXXXXXXX'},
            'user_type': {'help_text': 'Type: customer, staff, admin'},
        }
    
    def validate_phone_number(self, value):
        """Validation du numéro de téléphone sénégalais"""
        if not re.match(r'^\+221[0-9]{9}$', value):
            raise serializers.ValidationError(
                "Le numéro doit être au format +221XXXXXXXXX"
            )
        
        # Vérifier unicité
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError(
                "Ce numéro de téléphone est déjà utilisé."
            )
        
        return value
    
    def validate_email(self, value):
        """Validation de l'email (optionnel)"""
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Cette adresse email est déjà utilisée."
            )
        return value
    
    def validate(self, attrs):
        """Validation globale"""
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')
        
        # Vérifier que les mots de passe correspondent
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Les mots de passe ne correspondent pas.'
            })
        
        # Validation Django du mot de passe
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({
                'password': list(e.messages)
            })
        
        return attrs
    
    def create(self, validated_data):
        """Création d'un nouvel utilisateur"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Générer un username unique basé sur le téléphone
        phone_digits = validated_data['phone_number'].replace('+221', '')
        validated_data['username'] = f"user_{phone_digits}"
        
        # Créer l'utilisateur
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        return user


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Login avec Email',
            summary='Connexion avec adresse email',
            description='Exemple de connexion avec email',
            value={
                'login': 'test@example.com',
                'password': 'test123'
            },
            request_only=True,
        ),
        OpenApiExample(
            'Login avec Téléphone',
            summary='Connexion avec numéro de téléphone',
            description='Exemple de connexion avec téléphone sénégalais',
            value={
                'login': '+221771234567',
                'password': 'test123'
            },
            request_only=True,
        ),
    ]
)
class UserLoginSerializer(serializers.Serializer):
    """
    Serializer pour la connexion utilisateur
    
    Usage : POST /api/auth/login/
    Support connexion par téléphone ou email
    """
    
    login = serializers.CharField(
        help_text="Numéro de téléphone (+221XXXXXXXXX) ou email",
        required=True,
        allow_blank=False,
        max_length=150
    )
    password = serializers.CharField(
        write_only=True,
        help_text="Mot de passe",
        required=True,
        allow_blank=False,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        login = attrs.get('login')
        password = attrs.get('password')
        
        if not login or not password:
            raise serializers.ValidationError(
                'Les champs login et password sont obligatoires.'
            )
        
        # Tenter connexion par téléphone d'abord
        user = None
        if login.startswith('+221'):
            user = User.objects.filter(phone_number=login, is_active=True).first()
        else:
            # Sinon par email
            user = User.objects.filter(email=login, is_active=True).first()
        
        if not user:
            raise serializers.ValidationError(
                'Aucun compte actif trouvé avec ces identifiants.'
            )
        
        # Vérifier le mot de passe
        if not user.check_password(password):
            raise serializers.ValidationError(
                'Mot de passe incorrect.'
            )
        
        attrs['user'] = user
        return attrs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personnalisé pour les JWT tokens
    Ajoute des informations utilisateur au token
    """
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Ajouter des claims personnalisés
        token['user_type'] = user.user_type
        token['phone_number'] = user.phone_number
        token['full_name'] = user.get_full_name()
        token['preferred_language'] = user.preferred_language
        
        return token
    
    def validate(self, attrs):
        # Permettre connexion par téléphone au lieu de username
        login = attrs.get('username')  # Le champ s'appelle 'username' dans JWT
        password = attrs.get('password')
        
        # Chercher l'utilisateur par téléphone ou email
        user = None
        if login.startswith('+221'):
            user = User.objects.filter(phone_number=login, is_active=True).first()
        else:
            user = User.objects.filter(email=login, is_active=True).first()
            
        if user and user.check_password(password):
            # Remplacer par le username pour que JWT fonctionne
            attrs['username'] = user.username
        
        return super().validate(attrs)


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pour consulter et modifier le profil utilisateur
    
    Usage : GET/PUT /api/auth/profile/
    """
    
    full_name = serializers.CharField(
        source='get_full_name', 
        read_only=True,
        help_text="Nom complet calculé"
    )
    
    class Meta:
        model = User
        fields = [
            # Identifiants (lecture seule)
            'id', 'uuid', 'username', 'full_name',
            
            # Informations de base
            'first_name', 'last_name', 'email', 'phone_number',
            'user_type', 'preferred_language',
            
            # Informations personnelles
            'avatar', 'date_of_birth', 'gender', 'address', 'city',
            
            # Préférences
            'push_notifications_enabled', 'sms_notifications_enabled',
            'email_notifications_enabled',
            
            # Statuts
            'is_phone_verified', 'is_active',
            
            # Métadonnées
            'created_at', 'last_login'
        ]
        read_only_fields = [
            'id', 'uuid', 'username', 'user_type', 'phone_number',
            'is_phone_verified', 'created_at', 'last_login'
        ]
    
    def validate_email(self, value):
        """Validation email pour modification"""
        if value:
            user_id = self.instance.id if self.instance else None
            if User.objects.filter(email=value).exclude(id=user_id).exists():
                raise serializers.ValidationError(
                    "Cette adresse email est déjà utilisée."
                )
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer pour changer le mot de passe
    
    Usage : POST /api/auth/change-password/
    """
    
    current_password = serializers.CharField(
        write_only=True,
        help_text="Mot de passe actuel"
    )
    
    new_password = serializers.CharField(
        write_only=True,
        min_length=6,
        help_text="Nouveau mot de passe"
    )
    
    new_password_confirm = serializers.CharField(
        write_only=True,
        help_text="Confirmation du nouveau mot de passe"
    )
    
    def validate_current_password(self, value):
        """Vérifier le mot de passe actuel"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value
    
    def validate(self, attrs):
        """Validation globale"""
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')
        
        if new_password != new_password_confirm:
            raise serializers.ValidationError({
                'new_password_confirm': 'Les nouveaux mots de passe ne correspondent pas.'
            })
        
        # Validation Django
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })
        
        return attrs
    
    def save(self, **kwargs):
        """Sauvegarder le nouveau mot de passe"""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PhoneVerificationSerializer(serializers.Serializer):
    """
    Serializer pour vérifier le numéro de téléphone par SMS
    
    Usage : POST /api/auth/verify-phone/
    """
    
    verification_code = serializers.CharField(
        max_length=6,
        min_length=6,
        help_text="Code de vérification à 6 chiffres"
    )
    
    def validate_verification_code(self, value):
        """Vérifier le code"""
        if not value.isdigit():
            raise serializers.ValidationError(
                "Le code doit contenir uniquement des chiffres."
            )
        return value


class RequestPasswordResetSerializer(serializers.Serializer):
    """
    Serializer pour demander une réinitialisation de mot de passe
    
    Usage : POST /api/auth/password-reset-request/
    """
    
    phone_number = serializers.CharField(
        help_text="Numéro de téléphone (+221XXXXXXXXX)"
    )
    
    def validate_phone_number(self, value):
        """Vérifier que le numéro existe"""
        if not re.match(r'^\+221[0-9]{9}$', value):
            raise serializers.ValidationError(
                "Le numéro doit être au format +221XXXXXXXXX"
            )
        
        if not User.objects.filter(phone_number=value, is_active=True).exists():
            raise serializers.ValidationError(
                "Aucun compte actif trouvé avec ce numéro."
            )
        
        return value


class PasswordResetSerializer(serializers.Serializer):
    """
    Serializer pour réinitialiser le mot de passe avec un code
    
    Usage : POST /api/auth/password-reset/
    """
    
    phone_number = serializers.CharField()
    verification_code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=6, write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validation complète"""
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')
        
        if new_password != new_password_confirm:
            raise serializers.ValidationError({
                'new_password_confirm': 'Les mots de passe ne correspondent pas.'
            })
        
        # Validation Django
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })
        
        return attrs