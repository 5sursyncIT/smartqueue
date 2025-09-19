
# apps/accounts/models.py
"""
Modèles d'utilisateurs pour SmartQueue Sénégal
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
import uuid

from apps.business.models import Organization # Import ajouté

class User(AbstractUser):
    """
    Modèle utilisateur personnalisé pour SmartQueue Sénégal
    
    Ce modèle étend AbstractUser de Django pour ajouter :
    - Support des numéros de téléphone sénégalais
    - Types d'utilisateurs spécifiques à SmartQueue
    - Support multilingue (français/wolof)
    - Champs spécifiques au contexte sénégalais
    """
    
    # ==============================================
    # TYPES D'UTILISATEURS SMARTQUEUE
    # ==============================================
    
    USER_TYPES = [
        ('customer', _('Client')),           # Grand public (prend des tickets)
        ('staff', _('Personnel')),           # Employés aux guichets
        ('admin', _('Administrateur')),      # Responsables d'établissement
        ('super_admin', _('Super Admin')),   # Équipe SmartQueue
    ]
    
    # ==============================================
    # LANGUES SUPPORTÉES AU SÉNÉGAL
    # ==============================================
    
    LANGUAGE_CHOICES = [
        ('fr', _('Français')),    # Langue officielle
        ('wo', _('Wolof')),       # Langue nationale principale  
        ('en', _('English')),     # Pour expansion internationale
    ]
    
    # ==============================================
    # IDENTIFIANTS UNIQUES
    # ==============================================
    
    # UUID pour éviter les collisions et améliorer la sécurité
    uuid = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        unique=True,
        verbose_name=_('Identifiant unique')
    )
    
    # ==============================================
    # TYPE ET RÔLE DE L'UTILISATEUR
    # ==============================================
    
    user_type = models.CharField(
        max_length=20, 
        choices=USER_TYPES, 
        default='customer',
        verbose_name=_('Type d\'utilisateur'),
        help_text=_('Définit le rôle de l\'utilisateur dans SmartQueue')
    )
    
    # ==============================================
    # NUMÉRO DE TÉLÉPHONE (OPTIONNEL - Focus EMAIL)
    # ==============================================

    # ⚠️ MODIFICATION SUPERVISEUR : Téléphone optionnel, EMAIL prioritaire
    # Validation pour numéros sénégalais (+221XXXXXXXXX) - OPTIONNEL
    phone_regex = RegexValidator(
        regex=r'^\+221[0-9]{9}$',
        message=_('Le numéro doit être au format: +221XXXXXXXXX (Optionnel)')
    )
    
    # ⚠️ TÉLÉPHONE MAINTENANT OPTIONNEL (Décision superviseur)
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=13,
        blank=True,  # ← OPTIONNEL maintenant
        null=True,   # ← OPTIONNEL maintenant
        unique=True,
        verbose_name=_('Numéro de téléphone (optionnel)'),
        help_text=_('Format: +221XXXXXXXXX - OPTIONNEL (Email prioritaire)')
    )
    
    # ==============================================
    # PRÉFÉRENCES LINGUISTIQUES
    # ==============================================
    
    preferred_language = models.CharField(
        max_length=5, 
        choices=LANGUAGE_CHOICES, 
        default='fr',
        verbose_name=_('Langue préférée'),
        help_text=_('Langue d\'affichage de l\'interface')
    )
    
    # ==============================================
    # VÉRIFICATION EMAIL (Remplace vérification téléphone)
    # ==============================================

    # ⚠️ MODIFICATION SUPERVISEUR : Vérification EMAIL au lieu de SMS
    is_email_verified = models.BooleanField(
        default=False,
        verbose_name=_('Email vérifié'),
        help_text=_('L\'adresse email a été vérifiée')
    )

    # Code de vérification EMAIL (temporaire)
    email_verification_code = models.CharField(
        max_length=6,
        blank=True,
        null=True,
        verbose_name=_('Code de vérification email'),
        help_text=_('Code à 6 chiffres envoyé par email')
    )

    # Quand le code expire
    email_verification_expires = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Expiration du code email')
    )

    # ⚠️ TÉLÉPHONE VÉRIFICATION COMMENTÉE (SMS désactivé)
    # is_phone_verified = models.BooleanField(
    #     default=False,
    #     verbose_name=_('Téléphone vérifié'),
    #     help_text=_('Le numéro a été vérifié par SMS - DÉSACTIVÉ')
    # )
    
    # ==============================================
    # INFORMATIONS PERSONNELLES OPTIONNELLES
    # ==============================================
    
    # Photo de profil
    avatar = models.ImageField(
        upload_to='avatars/', 
        blank=True, 
        null=True,
        verbose_name=_('Photo de profil')
    )
    
    # Date de naissance
    date_of_birth = models.DateField(
        blank=True, 
        null=True,
        verbose_name=_('Date de naissance')
    )
    
    # Genre
    GENDER_CHOICES = [
        ('M', _('Masculin')),
        ('F', _('Féminin')),
        ('O', _('Autre')),
    ]
    gender = models.CharField(
        max_length=1, 
        choices=GENDER_CHOICES, 
        blank=True,
        verbose_name=_('Genre')
    )
    
    # Adresse
    address = models.TextField(
        blank=True,
        verbose_name=_('Adresse')
    )
    
    # Ville (important pour géolocalisation)
    city = models.CharField(
        max_length=100, 
        blank=True,
        verbose_name=_('Ville')
    )
    
    # ==============================================
    # PRÉFÉRENCES NOTIFICATIONS
    # ==============================================
    
    push_notifications_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Notifications push'),
        help_text=_('Recevoir des notifications sur mobile')
    )
    
    # ⚠️ SMS DÉSACTIVÉ (Décision superviseur - Focus PUSH + EMAIL)
    # sms_notifications_enabled = models.BooleanField(
    #     default=False,  # Désactivé par défaut
    #     verbose_name=_('Notifications SMS'),
    #     help_text=_('Recevoir des SMS pour les files d\'attente - DÉSACTIVÉ')
    # )
    
    email_notifications_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Notifications email'),
        help_text=_('Recevoir des emails de confirmation')
    )
    
    # ==============================================
    # MÉTADONNÉES DE CONNEXION
    # ==============================================
    
    # Dernière connexion mobile (différent de last_login)
    last_mobile_login = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name=_('Dernière connexion mobile')
    )
    
    # IP de la dernière connexion (pour sécurité)
    last_ip_address = models.GenericIPAddressField(
        blank=True, 
        null=True,
        verbose_name=_('Dernière adresse IP')
    )
    
    # ==============================================
    # ACCEPTATION CONDITIONS
    # ==============================================
    
    terms_accepted = models.BooleanField(
        default=False,
        verbose_name=_('Conditions acceptées'),
        help_text=_('A accepté les conditions d\'utilisation')
    )
    
    terms_accepted_date = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name=_('Date acceptation conditions')
    )
    
    # ==============================================
    # TIMESTAMPS
    # ==============================================
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Créé le')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Modifié le')
    )
    
    # ==============================================
    # CONFIGURATION DU MODÈLE
    # ==============================================
    
    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        db_table = 'accounts_user'
        
        # Index pour optimiser les requêtes
        indexes = [
            models.Index(fields=['user_type']),
            models.Index(fields=['phone_number']),
            # models.Index(fields=['is_phone_verified']),  # Commenté (SMS désactivé)
            models.Index(fields=['is_email_verified']),  # Nouvel index email
            models.Index(fields=['created_at']),
        ]
    
    # ==============================================
    # MÉTHODES PERSONNALISÉES
    # ==============================================
    
    def __str__(self):
        """Représentation en chaîne de caractères"""
        return f"{self.get_full_name() or self.username} ({self.phone_number})"
    
    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Retourne le prénom de l'utilisateur"""
        return self.first_name
    
    # ==============================================
    # PROPRIÉTÉS POUR VÉRIFIER LE TYPE D'UTILISATEUR
    # ==============================================
    
    @property
    def is_customer(self):
        """Vérifie si l'utilisateur est un client"""
        return self.user_type == 'customer'
    
    @property
    def is_staff_member(self):
        """Vérifie si l'utilisateur est un membre du personnel"""
        return self.user_type == 'staff'
    
    @property
    def is_organization_admin(self):
        """Vérifie si l'utilisateur est admin d'une organisation"""
        return self.user_type == 'admin'
    
    @property
    def is_super_admin(self):
        """Vérifie si l'utilisateur est super admin SmartQueue"""
        return self.user_type == 'super_admin'


# ==============================================
# PROFIL D'EMPLOYÉ (STAFF PROFILE)
# ==============================================

class StaffProfile(models.Model):
    """
    Profil étendu pour les utilisateurs de type 'staff' ou 'admin'.
    Lie un utilisateur à une organisation spécifique.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='staff_members')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Employé"
        verbose_name_plural = "Profils Employés"

    def __str__(self):
        return f"{self.user.username} - {self.organization.name}"
