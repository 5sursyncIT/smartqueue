# apps/payments/payment_service.py
"""
Service de paiement pour SmartQueue Sénégal
Intégration Wave Money, Orange Money, Free Money
"""

import logging
import requests
from decimal import Decimal
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Payment, PaymentProvider, PaymentLog, SubscriptionInvoice

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Service principal pour gérer les paiements mobile money sénégalais
    """

    def __init__(self):
        self.config = getattr(settings, 'PAYMENT_CONFIG', {})
        self.enabled = self.config.get('ENABLED', False)
        self.default_provider = self.config.get('DEFAULT_PROVIDER', 'wave')

    def initiate_invoice_payment(
        self,
        invoice: SubscriptionInvoice,
        paying_user,
        payer_phone: str,
        provider_name: str = None
    ) -> Dict[str, Any]:
        """
        Initier le paiement B2B pour une facture d'abonnement.
        """
        if not self.enabled:
            return {'success': False, 'error': 'Service de paiement désactivé'}

        if invoice.status != 'due':
            return {'success': False, 'error': f'La facture n nest pas due pour paiement (statut: {invoice.status}).'}

        # Validation du numéro
        if not self._validate_senegal_phone(payer_phone):
            return {'success': False, 'error': f'Numéro invalide: {payer_phone}'}

        provider_name = provider_name or self.default_provider
        provider_config = self.config.get('PROVIDERS', {}).get(provider_name)
        if not provider_config:
            return {'success': False, 'error': f'Provider {provider_name} non configuré'}

        try:
            provider_obj = PaymentProvider.objects.get(provider_type=provider_name)

            # Créer un enregistrement de paiement pour tracer cette tentative
            payment = Payment.objects.create(
                customer=paying_user, # L'utilisateur qui effectue le paiement
                provider=provider_obj,
                organization=invoice.organization,
                invoice=invoice, # Lier ce paiement à la facture
                payment_type='subscription_fee',
                amount=invoice.amount,
                currency='XOF',
                payer_phone=payer_phone,
                payer_name=paying_user.get_full_name(),
                description=f"Paiement de la facture {invoice.invoice_number}",
                status='pending'
            )

            PaymentLog.objects.create(payment=payment, action='initiated')

            # Appeler la méthode du fournisseur (simulation Wave pour l'instant)
            if provider_name == 'wave':
                result = self._initiate_wave_payment(payment, provider_config)
            else:
                result = {'success': False, 'error': f'Provider {provider_name} non supporté pour le paiement de factures.'}

            if result.get('success'):
                payment.status = 'processing'
                payment.external_reference = result.get('transaction_id', '')
                payment.metadata = result.get('metadata', {})
                payment.save()
            else:
                payment.mark_as_failed('INITIATION_FAILED', result.get('error'))

            return result

        except Exception as e:
            logger.error(f"Erreur initiation paiement de facture {invoice.invoice_number}: {e}")
            return {'success': False, 'error': str(e)}


    def initiate_payment(
        self,
        customer_phone: str,
        amount: Decimal,
        description: str,
        customer,
        organization,
        ticket=None,
        appointment=None,
        provider_name: str = None
    ) -> Dict[str, Any]:
        """
        Initier un paiement mobile money (B2C)
        """
        if not self.enabled:
            return {
                'success': False,
                'error': 'Service de paiement désactivé',
                'payment_id': None
            }

        # ... (le reste de la fonction reste inchangé)
        if not self._validate_senegal_phone(customer_phone):
            return {
                'success': False,
                'error': f'Numéro invalide: {customer_phone}',
                'payment_id': None
            }

        if amount <= 0:
            return {
                'success': False,
                'error': f'Montant invalide: {amount}',
                'payment_id': None
            }

        provider_name = provider_name or self.default_provider
        provider_config = self.config.get('PROVIDERS', {}).get(provider_name)

        if not provider_config:
            return {
                'success': False,
                'error': f'Provider {provider_name} non configuré',
                'payment_id': None
            }

        try:
            provider_obj, created = PaymentProvider.objects.get_or_create(
                provider_type=provider_name,
                defaults={
                    'name': provider_config.get('NAME', provider_name),
                    'api_url': provider_config.get('API_URL', ''),
                    'is_active': True,
                    'priority': provider_config.get('PRIORITY', 1)
                }
            )

            payment = Payment.objects.create(
                customer=customer,
                provider=provider_obj,
                organization=organization,
                ticket=ticket,
                appointment=appointment,
                amount=amount,
                currency='XOF',
                payer_phone=customer_phone,
                payer_name=customer.get_full_name(),
                description=description,
                status='pending'
            )

            PaymentLog.objects.create(
                payment=payment,
                action='initiated',
                details={
                    'provider': provider_name,
                    'amount': float(amount),
                    'phone': customer_phone
                }
            )

            if provider_name == 'wave':
                result = self._initiate_wave_payment(payment, provider_config)
            elif provider_name == 'orange_money':
                result = self._initiate_orange_money_payment(payment, provider_config)
            elif provider_name == 'free_money':
                result = self._initiate_free_money_payment(payment, provider_config)
            else:
                result = {
                    'success': False,
                    'error': f'Provider {provider_name} non supporté'
                }

            if result['success']:
                payment.status = 'processing'
                payment.external_reference = result.get('transaction_id', '')
                payment.metadata = result.get('metadata', {})
                payment.save()
            else:
                payment.mark_as_failed(
                    error_code='INITIATION_FAILED',
                    error_message=result.get('error', 'Erreur inconnue')
                )

            result['payment_id'] = payment.id
            return result

        except Exception as e:
            logger.error(f"Erreur initiation paiement: {e}")
            return {
                'success': False,
                'error': str(e),
                'payment_id': None
            }

    def _initiate_wave_payment(self, payment: Payment, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        SIMULATION d'un paiement Wave Money.
        """
        import time
        transaction_id = f"WAVE_SIM_{int(time.time())}"
        
        logger.info(f"[SIMULATION] Initiation d'un paiement Wave pour le paiement {payment.payment_number}...")
        logger.info(f"[SIMULATION] ID de transaction généré: {transaction_id}")

        PaymentLog.objects.create(
            payment=payment,
            action='sent_to_provider',
            details={
                'provider': 'wave',
                'status': 'simulation',
                'note': 'Ceci est une transaction simulée.',
                'simulated_transaction_id': transaction_id
            }
        )

        return {
            'success': True,
            'provider': 'wave',
            'transaction_id': transaction_id,
            'metadata': {
                'status': 'pending_confirmation',
                'message': 'Veuillez confirmer le paiement sur votre téléphone.'
            }
        }

    def _initiate_orange_money_payment(self, payment: Payment, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        PLACEHOLDER - En attente de la documentation API Orange Money
        """
        PaymentLog.objects.create(
            payment=payment,
            action='sent_to_provider',
            details={
                'provider': 'orange_money',
                'status': 'placeholder',
                'note': 'En attente des spécifications API Orange Money'
            }
        )

        return {
            'success': False,
            'error': 'Service Orange Money - En attente des spécifications API officielle',
            'provider': 'orange_money'
        }

    def _initiate_free_money_payment(self, payment: Payment, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        PLACEHOLDER - En attente de la documentation API Free Money
        """
        PaymentLog.objects.create(
            payment=payment,
            action='sent_to_provider',
            details={
                'provider': 'free_money',
                'status': 'placeholder',
                'note': 'En attente des spécifications API Free Money'
            }
        )

        return {
            'success': False,
            'error': 'Service Free Money - En attente des spécifications API officielle',
            'provider': 'free_money'
        }

    def check_payment_status(self, payment_id: int) -> Dict[str, Any]:
        """
        Vérifier le statut d'un paiement
        """
        try:
            payment = Payment.objects.get(id=payment_id)

            return {
                'success': True,
                'payment_id': payment.id,
                'payment_number': payment.payment_number,
                'status': payment.status,
                'amount': float(payment.total_amount),
                'currency': payment.currency,
                'external_reference': payment.external_reference,
                'created_at': payment.created_at.isoformat(),
                'expires_at': payment.expires_at.isoformat() if payment.expires_at else None,
                'is_expired': payment.is_expired
            }

        except Payment.DoesNotExist:
            return {
                'success': False,
                'error': f'Paiement {payment_id} non trouvé'
            }

    def handle_payment_callback(self, provider_name: str, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Traiter un callback de confirmation de paiement.
        Cette fonction est appelée par la vue du webhook.
        """
        logger.info(f"[CALLBACK] Données reçues de {provider_name}: {callback_data}")

        # La référence de la transaction est supposée être dans `client_reference`
        payment_number = callback_data.get('client_reference')
        if not payment_number:
            logger.error("[CALLBACK] Erreur: client_reference manquant dans les données du callback.")
            return {'success': False, 'error': 'Référence de paiement manquante.'}

        try:
            # Retrouver la tentative de paiement originale
            payment = Payment.objects.select_related('invoice').get(payment_number=payment_number)
        except Payment.DoesNotExist:
            logger.error(f"[CALLBACK] Erreur: Paiement {payment_number} non trouvé.")
            return {'success': False, 'error': 'Paiement non trouvé.'}

        if payment.status == 'completed':
            logger.warning(f"[CALLBACK] Paiement {payment_number} déjà complété. Traitement ignoré.")
            return {'success': True, 'message': 'Paiement déjà traité.'}

        payment_status = callback_data.get('status')
        external_ref = callback_data.get('external_transaction_id')

        if payment_status == 'completed':
            payment.mark_as_completed(external_reference=external_ref, metadata=callback_data)
            logger.info(f"[CALLBACK] Paiement {payment.payment_number} marqué comme complété.")

            if payment.invoice:
                invoice = payment.invoice
                invoice.status = 'paid'
                invoice.paid_at = timezone.now()
                invoice.save()
                logger.info(f"[CALLBACK] Facture {invoice.invoice_number} marquée comme payée.")
            
            return {'success': True}
        else:
            error_msg = callback_data.get('error_message', 'Échec rapporté par le provider.')
            payment.mark_as_failed(error_code='CALLBACK_FAILED', error_message=error_msg)
            logger.error(f"[CALLBACK] Échec du paiement {payment.payment_number}. Raison: {error_msg}")
            return {'success': False, 'error': error_msg}

    def _validate_senegal_phone(self, phone: str) -> bool:
        """Valider numéro de téléphone sénégalais"""
        import re
        pattern = r'^\+221[0-9]{9}$'
        return bool(re.match(pattern, phone))

    def get_payment_providers_status(self) -> Dict[str, Any]:
        """
        Obtenir statut de tous les providers de paiement
        """
        status = {
            'enabled': self.enabled,
            'default_provider': self.default_provider,
            'providers': {}
        }

        for name, config in self.config.get('PROVIDERS', {}).items():
            api_key = config.get('API_KEY', '') or config.get('CLIENT_ID', '')
            configured = bool(api_key)

            status['providers'][name] = {
                'name': config.get('NAME', name),
                'configured': configured,
                'priority': config.get('PRIORITY', 999),
                'available': configured
            }

        return status

    def calculate_payment_amount(
        self,
        base_amount: Decimal,
        organization,
        payment_type: str = 'service_fee'
    ) -> Dict[str, Decimal]:
        """
        Calculer le montant total d'un paiement avec les frais
        """
        fees = Decimal('0.00')
        total = base_amount + fees

        return {
            'base_amount': base_amount,
            'fees': fees,
            'total_amount': total
        }


# Instance globale du service
payment_service = PaymentService()