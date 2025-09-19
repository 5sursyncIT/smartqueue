# apps/payments/utils.py
"""
Utilitaires pour les paiements SmartQueue
Fonctions helper pour simulation et tests
"""

import logging
from decimal import Decimal
from django.utils import timezone
from .models import Payment
from .payment_service import payment_service

logger = logging.getLogger(__name__)


def simulate_payment_success(payment_id: int, external_reference: str = None) -> bool:
    """
    Simuler un paiement réussi (pour tests sans vraies APIs)

    Args:
        payment_id: ID du paiement à marquer comme réussi
        external_reference: Référence externe simulée

    Returns:
        True si simulation réussie
    """
    try:
        payment = Payment.objects.get(id=payment_id)

        if payment.status != 'processing':
            logger.warning(f"Paiement {payment_id} n'est pas en cours de traitement")
            return False

        # Marquer comme complété
        payment.mark_as_completed(
            external_reference=external_reference or f"SIM_{timezone.now().strftime('%Y%m%d%H%M%S')}",
            metadata={
                'simulation': True,
                'completed_at': timezone.now().isoformat()
            }
        )

        logger.info(f"Paiement {payment.payment_number} simulé comme réussi")
        return True

    except Payment.DoesNotExist:
        logger.error(f"Paiement {payment_id} non trouvé")
        return False
    except Exception as e:
        logger.error(f"Erreur simulation paiement {payment_id}: {e}")
        return False


def simulate_payment_failure(payment_id: int, error_message: str = None) -> bool:
    """
    Simuler un paiement échoué (pour tests)

    Args:
        payment_id: ID du paiement à marquer comme échoué
        error_message: Message d'erreur simulé

    Returns:
        True si simulation réussie
    """
    try:
        payment = Payment.objects.get(id=payment_id)

        if payment.status not in ['pending', 'processing']:
            logger.warning(f"Paiement {payment_id} ne peut pas être marqué comme échoué")
            return False

        # Marquer comme échoué
        payment.mark_as_failed(
            error_code='SIMULATION_FAILED',
            error_message=error_message or 'Paiement simulé comme échoué'
        )

        logger.info(f"Paiement {payment.payment_number} simulé comme échoué")
        return True

    except Payment.DoesNotExist:
        logger.error(f"Paiement {payment_id} non trouvé")
        return False
    except Exception as e:
        logger.error(f"Erreur simulation échec paiement {payment_id}: {e}")
        return False


def create_test_ticket_payment(customer, organization, amount: Decimal = None) -> Payment:
    """
    Créer un paiement de test pour ticket

    Args:
        customer: Utilisateur client
        organization: Organisation
        amount: Montant (par défaut 1000 FCFA)

    Returns:
        Paiement créé
    """
    amount = amount or Decimal('1000.00')

    result = payment_service.initiate_payment(
        customer_phone=customer.phone,
        amount=amount,
        description=f'Test ticket {organization.trade_name}',
        customer=customer,
        organization=organization,
        provider_name='wave'  # Provider de test
    )

    if result['success']:
        payment = Payment.objects.get(id=result['payment_id'])
        logger.info(f"Paiement test créé: {payment.payment_number}")
        return payment
    else:
        logger.error(f"Échec création paiement test: {result['error']}")
        return None


def get_payment_stats(organization=None, customer=None) -> dict:
    """
    Obtenir des statistiques de paiement

    Args:
        organization: Filtrer par organisation
        customer: Filtrer par client

    Returns:
        Dict avec statistiques
    """
    from django.db import models

    queryset = Payment.objects.all()

    if organization:
        queryset = queryset.filter(organization=organization)
    if customer:
        queryset = queryset.filter(customer=customer)

    stats = {
        'total_payments': queryset.count(),
        'completed_payments': queryset.filter(status='completed').count(),
        'pending_payments': queryset.filter(status__in=['pending', 'processing']).count(),
        'failed_payments': queryset.filter(status='failed').count(),
    }

    # Montants
    completed_amount = queryset.filter(status='completed').aggregate(
        total=models.Sum('total_amount')
    )['total'] or Decimal('0')

    stats['total_amount'] = float(completed_amount)
    stats['average_amount'] = float(completed_amount / stats['completed_payments']) if stats['completed_payments'] > 0 else 0
    stats['success_rate'] = (stats['completed_payments'] / stats['total_payments'] * 100) if stats['total_payments'] > 0 else 0

    return stats


def check_payment_expiration():
    """
    Vérifier et marquer les paiements expirés

    Utilitaire à appeler périodiquement (cron job)
    """
    expired_payments = Payment.objects.filter(
        status__in=['pending', 'processing'],
        expires_at__lt=timezone.now()
    )

    count = 0
    for payment in expired_payments:
        payment.status = 'expired'
        payment.save(update_fields=['status'])
        count += 1

        logger.info(f"Paiement {payment.payment_number} marqué comme expiré")

    return count


def cleanup_old_failed_payments(days_old: int = 30):
    """
    Nettoyer les anciens paiements échoués

    Args:
        days_old: Supprimer paiements échoués plus vieux que X jours

    Returns:
        Nombre de paiements supprimés
    """
    from datetime import timedelta

    cutoff_date = timezone.now() - timedelta(days=days_old)

    old_failed = Payment.objects.filter(
        status__in=['failed', 'expired', 'cancelled'],
        created_at__lt=cutoff_date
    )

    count = old_failed.count()
    old_failed.delete()

    logger.info(f"{count} anciens paiements échoués supprimés")
    return count