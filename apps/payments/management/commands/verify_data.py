# apps/payments/management/commands/verify_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.business.models import Organization
from apps.payments.models import PaymentPlan, SubscriptionInvoice

from apps.accounts.models import StaffProfile # Import direct

User = get_user_model()

class Command(BaseCommand):
    help = "Vérifie et, si nécessaire, crée les données de test complètes, puis les affiche."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("--- Création/Mise à jour des données de test ---"))

        # Étape 1: Plan de paiement
        plan, _ = PaymentPlan.objects.get_or_create(
            plan_type='business',
            defaults={'name': 'Pack Business', 'monthly_fee': 50000}
        )
        self.stdout.write(f"- Plan de paiement '{plan.name}' OK.")

        # Étape 2: Organisation
        org, _ = Organization.objects.get_or_create(
            name="Hôpital de Test",
            defaults={
                'type': 'hospital', 'phone_number': '+221771234567', 'email': 'contact@hopitaltest.sn',
                'address': '123 Avenue de Test', 'city': 'Dakar', 'region': 'dakar',
                'subscription_plan': 'business', 'status': 'active'
            }
        )
        org.status = 'active'
        org.subscription_plan = 'business'
        org.save()
        self.stdout.write(f"- Organisation '{org.name}' OK.")

        # Étape 3: Utilisateur Staff/Admin pour l'organisation
        admin_user, created = User.objects.get_or_create(
            username='admin_hopital',
            defaults={
                'email': 'admin@hopitaltest.sn',
                'user_type': 'admin',
                'phone_number': '+221771112233'
            }
        )
        if created:
            admin_user.set_password('adminpass')
            admin_user.save()
        
        StaffProfile.objects.get_or_create(user=admin_user, defaults={'organization': org})
        self.stdout.write(f"- Utilisateur admin '{admin_user.username}' pour '{org.name}' OK.")

        # --- AFFICHAGE POUR VÉRIFICATION ---
        self.stdout.write(self.style.SUCCESS("\n--- Vérification des Données ---"))
        for org_item in Organization.objects.all():
            self.stdout.write(f"[ORG] Nom: {org_item.name}, Statut: {org_item.status}, Plan: {org_item.subscription_plan}")
        
        for plan_item in PaymentPlan.objects.all():
            self.stdout.write(f"[PLAN] Type: {plan_item.plan_type}, Frais mensuels: {plan_item.monthly_fee}")

        for profile in StaffProfile.objects.select_related('user', 'organization').all():
            self.stdout.write(f"[STAFF] User: {profile.user.username}, Org: {profile.organization.name}")
