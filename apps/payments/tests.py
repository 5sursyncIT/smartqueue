# apps/payments/tests.py
"""
Tests pour l'application payments SmartQueue
Tests des modèles, vues et services de paiement
"""

import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.business.models import Organization
from .models import (
    PaymentProvider, Payment, PaymentMethod, PaymentLog,
    PaymentPlan, SubscriptionInvoice
)
from .payment_service import payment_service

User = get_user_model()


class PaymentProviderModelTest(TestCase):
    """Tests du modèle PaymentProvider"""

    def setUp(self):
        self.provider = PaymentProvider.objects.create(
            name="Wave Sénégal",
            provider_type="wave",
            api_url="https://api.wave.com",
            api_key="test_key",
            min_amount=Decimal('100.00'),
            max_amount=Decimal('1000000.00'),
            transaction_fee_percent=Decimal('1.5'),
            is_active=True
        )

    def test_provider_creation(self):
        """Test création d'un provider"""
        self.assertEqual(self.provider.name, "Wave Sénégal")
        self.assertEqual(self.provider.provider_type, "wave")
        self.assertTrue(self.provider.is_active)

    def test_calculate_fees(self):
        """Test calcul des frais"""
        amount = Decimal('1000.00')
        fees = self.provider.calculate_fees(amount)
        expected = Decimal('15.00')  # 1.5% de 1000
        self.assertEqual(fees, expected)

    def test_is_amount_valid(self):
        """Test validation des montants"""
        self.assertTrue(self.provider.is_amount_valid(Decimal('500.00')))
        self.assertFalse(self.provider.is_amount_valid(Decimal('50.00')))  # Trop bas
        self.assertFalse(self.provider.is_amount_valid(Decimal('2000000.00')))  # Trop haut

    def test_str_representation(self):
        """Test représentation string"""
        self.assertIn("Wave Sénégal", str(self.provider))


class PaymentModelTest(TestCase):
    """Tests du modèle Payment"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone='+221781234567',
            first_name='Test',
            last_name='User'
        )
        self.organization = Organization.objects.create(
            name="Test Org",
            trade_name="Test Trade",
            status='active'
        )
        self.provider = PaymentProvider.objects.create(
            name="Wave Test",
            provider_type="wave",
            is_active=True
        )
        self.payment = Payment.objects.create(
            customer=self.user,
            provider=self.provider,
            organization=self.organization,
            amount=Decimal('1000.00'),
            fees=Decimal('15.00'),
            total_amount=Decimal('1015.00'),
            payer_phone='+221781234567',
            payer_name='Test User',
            description='Test payment'
        )

    def test_payment_creation(self):
        """Test création d'un paiement"""
        self.assertEqual(self.payment.customer, self.user)
        self.assertEqual(self.payment.total_amount, Decimal('1015.00'))
        self.assertEqual(self.payment.status, 'pending')
        self.assertIsNotNone(self.payment.payment_number)

    def test_payment_number_generation(self):
        """Test génération automatique du numéro"""
        self.assertTrue(self.payment.payment_number.startswith('PAY'))

    def test_payment_expiration(self):
        """Test expiration des paiements"""
        # Le paiement ne devrait pas être expiré à la création
        self.assertFalse(self.payment.is_expired)
        self.assertIsNotNone(self.payment.time_remaining)

    def test_can_be_cancelled(self):
        """Test possibilité d'annulation"""
        self.assertTrue(self.payment.can_be_cancelled())

        self.payment.status = 'completed'
        self.assertFalse(self.payment.can_be_cancelled())

    def test_mark_as_completed(self):
        """Test marquage comme complété"""
        self.payment.mark_as_completed(
            external_reference='WAVE123',
            metadata={'test': 'data'}
        )

        self.assertEqual(self.payment.status, 'completed')
        self.assertEqual(self.payment.external_reference, 'WAVE123')
        self.assertIsNotNone(self.payment.completed_at)

    def test_mark_as_failed(self):
        """Test marquage comme échoué"""
        self.payment.mark_as_failed(
            error_code='INSUFFICIENT_FUNDS',
            error_message='Solde insuffisant'
        )

        self.assertEqual(self.payment.status, 'failed')
        self.assertEqual(self.payment.error_code, 'INSUFFICIENT_FUNDS')


class PaymentServiceTest(TestCase):
    """Tests du service de paiement"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone='+221781234567',
            first_name='Test',
            last_name='User'
        )
        self.organization = Organization.objects.create(
            name="Test Org",
            trade_name="Test Trade",
            status='active'
        )
        self.provider = PaymentProvider.objects.create(
            name="Wave Test",
            provider_type="wave",
            is_active=True
        )

    def test_validate_senegal_phone(self):
        """Test validation numéro sénégalais"""
        service = payment_service

        # Numéros valides
        self.assertTrue(service._validate_senegal_phone('+221781234567'))
        self.assertTrue(service._validate_senegal_phone('+221701234567'))

        # Numéros invalides
        self.assertFalse(service._validate_senegal_phone('781234567'))
        self.assertFalse(service._validate_senegal_phone('+33123456789'))
        self.assertFalse(service._validate_senegal_phone('+22178123456'))  # Trop court

    def test_initiate_payment(self):
        """Test initiation d'un paiement"""
        result = payment_service.initiate_payment(
            customer_phone='+221781234567',
            amount=Decimal('1000.00'),
            description='Test payment',
            customer=self.user,
            organization=self.organization,
            provider_name='wave'
        )

        self.assertTrue(result['success'])
        self.assertIsNotNone(result['payment_id'])

        # Vérifier que le paiement a été créé
        payment = Payment.objects.get(id=result['payment_id'])
        self.assertEqual(payment.customer, self.user)
        self.assertEqual(payment.amount, Decimal('1000.00'))

    def test_check_payment_status(self):
        """Test vérification du statut"""
        # Créer un paiement
        payment = Payment.objects.create(
            customer=self.user,
            provider=self.provider,
            organization=self.organization,
            amount=Decimal('1000.00'),
            payer_phone='+221781234567',
            payer_name='Test User'
        )

        result = payment_service.check_payment_status(payment.id)

        self.assertTrue(result['success'])
        self.assertEqual(result['payment_id'], payment.id)
        self.assertEqual(result['status'], 'pending')


class PaymentAPITest(APITestCase):
    """Tests des APIs de paiement"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone='+221781234567',
            first_name='Test',
            last_name='User'
        )
        self.organization = Organization.objects.create(
            name="Test Org",
            trade_name="Test Trade",
            status='active'
        )
        self.provider = PaymentProvider.objects.create(
            name="Wave Test",
            provider_type="wave",
            is_active=True
        )

    def authenticate(self):
        """Authentifier l'utilisateur pour les tests"""
        self.client.force_authenticate(user=self.user)

    def test_payment_providers_list(self):
        """Test listing des providers (sans auth)"""
        url = reverse('payments:payment-provider-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_payment_stats_authenticated(self):
        """Test stats de paiements (avec auth)"""
        self.authenticate()

        url = reverse('payments:payment-stats')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_payments', response.data)
        self.assertIn('success_rate', response.data)

    def test_payment_stats_unauthenticated(self):
        """Test stats sans authentification"""
        url = reverse('payments:payment-stats')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_initiate_payment_api(self):
        """Test API d'initiation de paiement"""
        self.authenticate()

        url = reverse('payments:initiate-payment')
        data = {
            'phone_number': '+221781234567',
            'amount': '1000.00',
            'description': 'Test API payment',
            'organization_id': self.organization.id,
            'provider': 'wave'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('payment_number', response.data)
        self.assertEqual(response.data['status'], 'processing')

    def test_payment_logs_view(self):
        """Test vue des logs de paiements"""
        self.authenticate()

        # Créer un paiement avec logs
        payment = Payment.objects.create(
            customer=self.user,
            provider=self.provider,
            organization=self.organization,
            amount=Decimal('1000.00'),
            payer_phone='+221781234567',
            payer_name='Test User'
        )

        PaymentLog.objects.create(
            payment=payment,
            action='initiated'
        )

        url = reverse('payments:payment-logs')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)


class PaymentPlanTest(TestCase):
    """Tests du modèle PaymentPlan"""

    def test_plan_creation(self):
        """Test création d'un plan"""
        plan = PaymentPlan.objects.create(
            name="Plan Basique",
            plan_type="basic",
            monthly_fee=Decimal('5000.00'),
            fee_per_ticket=Decimal('50.00'),
            max_tickets_per_month=100
        )

        self.assertEqual(plan.name, "Plan Basique")
        self.assertEqual(plan.monthly_fee, Decimal('5000.00'))
        self.assertTrue(plan.is_active)


class SubscriptionInvoiceTest(TestCase):
    """Tests du modèle SubscriptionInvoice"""

    def setUp(self):
        self.organization = Organization.objects.create(
            name="Test Org",
            trade_name="Test Trade",
            status='active'
        )
        self.plan = PaymentPlan.objects.create(
            name="Plan Test",
            plan_type="basic",
            monthly_fee=Decimal('5000.00')
        )

    def test_invoice_creation(self):
        """Test création d'une facture"""
        invoice = SubscriptionInvoice.objects.create(
            organization=self.organization,
            plan=self.plan,
            amount=Decimal('5000.00'),
            billing_period_start=timezone.now().date(),
            billing_period_end=timezone.now().date(),
            due_date=timezone.now().date()
        )

        self.assertEqual(invoice.organization, self.organization)
        self.assertEqual(invoice.amount, Decimal('5000.00'))
        self.assertEqual(invoice.status, 'due')
        self.assertIsNotNone(invoice.invoice_number)

    def test_invoice_number_generation(self):
        """Test génération du numéro de facture"""
        invoice = SubscriptionInvoice.objects.create(
            organization=self.organization,
            plan=self.plan,
            amount=Decimal('5000.00'),
            billing_period_start=timezone.now().date(),
            billing_period_end=timezone.now().date(),
            due_date=timezone.now().date()
        )

        self.assertTrue(invoice.invoice_number.startswith('FACT-'))


class PaymentUtilsTest(TestCase):
    """Tests des utilitaires de paiement"""

    def setUp(self):
        self.user = User.objects.create_user(
            phone='+221781234567',
            first_name='Test',
            last_name='User'
        )
        self.organization = Organization.objects.create(
            name="Test Org",
            trade_name="Test Trade",
            status='active'
        )
        self.provider = PaymentProvider.objects.create(
            name="Wave Test",
            provider_type="wave",
            is_active=True
        )

    def test_simulate_payment_success(self):
        """Test simulation de succès"""
        from .utils import simulate_payment_success

        payment = Payment.objects.create(
            customer=self.user,
            provider=self.provider,
            organization=self.organization,
            amount=Decimal('1000.00'),
            payer_phone='+221781234567',
            payer_name='Test User',
            status='processing'
        )

        success = simulate_payment_success(payment.id)

        self.assertTrue(success)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'completed')

    def test_simulate_payment_failure(self):
        """Test simulation d'échec"""
        from .utils import simulate_payment_failure

        payment = Payment.objects.create(
            customer=self.user,
            provider=self.provider,
            organization=self.organization,
            amount=Decimal('1000.00'),
            payer_phone='+221781234567',
            payer_name='Test User',
            status='processing'
        )

        success = simulate_payment_failure(payment.id, 'Test error')

        self.assertTrue(success)
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'failed')
        self.assertEqual(payment.error_message, 'Test error')