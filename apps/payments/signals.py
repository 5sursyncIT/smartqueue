# apps/payments/signals.py
"""
Signaux pour l'intégration paiements avec tickets et RDV
Automatise la création de tickets/RDV quand paiement confirmé
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Payment)
def handle_payment_completion(sender, instance, created, **kwargs):
    """
    Signal déclenché quand un paiement change de statut

    Automatise la création de tickets/RDV quand paiement confirmé
    """
    # Ne traiter que si le statut devient 'completed'
    if instance.status == 'completed':
        logger.info(f"Paiement {instance.payment_number} confirmé - Traitement automatique")

        try:
            # Si le paiement est lié à un ticket
            if instance.ticket:
                _handle_ticket_payment_completed(instance)

            # Si le paiement est lié à un RDV
            elif instance.appointment:
                _handle_appointment_payment_completed(instance)

            # Si c'est un paiement générique (création nouveau ticket/RDV)
            else:
                _handle_generic_payment_completed(instance)

        except Exception as e:
            logger.error(f"Erreur traitement paiement {instance.payment_number}: {e}")


def _handle_ticket_payment_completed(payment: Payment):
    """
    Traiter un paiement confirmé pour un ticket existant
    """
    ticket = payment.ticket

    # Marquer le ticket comme payé
    if hasattr(ticket, 'is_paid'):
        ticket.is_paid = True
        ticket.save(update_fields=['is_paid'])

    # Envoyer SMS de confirmation
    _send_ticket_payment_confirmation(payment, ticket)

    logger.info(f"Ticket {ticket.ticket_number} marqué comme payé")


def _handle_appointment_payment_completed(payment: Payment):
    """
    Traiter un paiement confirmé pour un RDV existant
    """
    appointment = payment.appointment

    # Confirmer le RDV
    if appointment.status == 'pending_payment':
        appointment.status = 'confirmed'
        appointment.save(update_fields=['status'])

    # Envoyer SMS de confirmation
    _send_appointment_payment_confirmation(payment, appointment)

    logger.info(f"RDV {appointment.appointment_number} confirmé après paiement")


def _handle_generic_payment_completed(payment: Payment):
    """
    Traiter un paiement générique (création automatique ticket/RDV)
    """
    # Selon le type de paiement, créer automatiquement le service
    if payment.payment_type == 'ticket_fee':
        _create_ticket_from_payment(payment)
    elif payment.payment_type == 'appointment_fee':
        # Pour les RDV, il faut plus d'infos (date, heure)
        # On ne peut pas créer automatiquement
        logger.info(f"Paiement RDV confirmé - Création manuelle nécessaire")

    # Envoyer SMS de confirmation générique
    _send_generic_payment_confirmation(payment)


def _create_ticket_from_payment(payment: Payment):
    """
    Créer automatiquement un ticket après paiement confirmé
    """
    try:
        from apps.queue_management.models import Ticket, Queue
        from apps.core.utils import TokenGenerator

        # Trouver une queue disponible dans l'organisation
        available_queue = Queue.objects.filter(
            organization=payment.organization,
            is_active=True,
            status='open'
        ).first()

        if not available_queue:
            logger.warning(f"Aucune queue disponible pour organisation {payment.organization}")
            return

        # Créer le ticket
        ticket = Ticket.objects.create(
            customer=payment.customer,
            organization=payment.organization,
            service=available_queue.service,
            queue=available_queue,
            ticket_number=TokenGenerator.generate_ticket_number(),
            status='waiting',
            is_paid=True,
            payment=payment  # Lier au paiement
        )

        # Mettre à jour le paiement avec le ticket créé
        payment.ticket = ticket
        payment.save(update_fields=['ticket'])

        logger.info(f"Ticket {ticket.ticket_number} créé automatiquement après paiement")

        # Envoyer SMS avec numéro de ticket
        _send_ticket_creation_confirmation(payment, ticket)

    except Exception as e:
        logger.error(f"Erreur création ticket automatique: {e}")


def _send_ticket_payment_confirmation(payment: Payment, ticket):
    """
    Envoyer SMS de confirmation de paiement pour ticket
    """
    try:
        from apps.notifications.sms_service import sms_service

        message = (
            f"SmartQueue: Paiement confirmé ! "
            f"Votre ticket #{ticket.ticket_number} est valide. "
            f"Organisation: {payment.organization.trade_name}"
        )

        result = sms_service.send_sms(payment.payer_phone, message)

        if result['success']:
            logger.info(f"SMS confirmation envoyé pour ticket {ticket.ticket_number}")
        else:
            logger.warning(f"Échec envoi SMS ticket {ticket.ticket_number}: {result['error']}")

    except Exception as e:
        logger.error(f"Erreur envoi SMS ticket: {e}")


def _send_appointment_payment_confirmation(payment: Payment, appointment):
    """
    Envoyer SMS de confirmation de paiement pour RDV
    """
    try:
        from apps.notifications.sms_service import sms_service

        message = (
            f"SmartQueue: Paiement confirmé ! "
            f"RDV #{appointment.appointment_number} confirmé le "
            f"{appointment.scheduled_date.strftime('%d/%m/%Y')} à "
            f"{appointment.scheduled_time.strftime('%H:%M')} "
            f"chez {payment.organization.trade_name}"
        )

        result = sms_service.send_sms(payment.payer_phone, message)

        if result['success']:
            logger.info(f"SMS confirmation envoyé pour RDV {appointment.appointment_number}")
        else:
            logger.warning(f"Échec envoi SMS RDV {appointment.appointment_number}: {result['error']}")

    except Exception as e:
        logger.error(f"Erreur envoi SMS RDV: {e}")


def _send_ticket_creation_confirmation(payment: Payment, ticket):
    """
    Envoyer SMS avec numéro de ticket créé automatiquement
    """
    try:
        from apps.notifications.sms_service import sms_service

        message = (
            f"SmartQueue: Paiement reçu ! "
            f"Votre ticket #{ticket.ticket_number} a été créé. "
            f"File d'attente: {ticket.queue.name}. "
            f"Rendez-vous à {payment.organization.trade_name}"
        )

        result = sms_service.send_sms(payment.payer_phone, message)

        if result['success']:
            logger.info(f"SMS création ticket envoyé: {ticket.ticket_number}")
        else:
            logger.warning(f"Échec envoi SMS création ticket: {result['error']}")

    except Exception as e:
        logger.error(f"Erreur envoi SMS création ticket: {e}")


def _send_generic_payment_confirmation(payment: Payment):
    """
    Envoyer SMS de confirmation générique de paiement
    """
    try:
        from apps.notifications.sms_service import sms_service

        message = (
            f"SmartQueue: Paiement de {payment.total_amount} FCFA confirmé ! "
            f"Réf: {payment.payment_number}. "
            f"Merci de votre confiance."
        )

        result = sms_service.send_sms(payment.payer_phone, message)

        if result['success']:
            logger.info(f"SMS confirmation générique envoyé: {payment.payment_number}")
        else:
            logger.warning(f"Échec envoi SMS générique: {result['error']}")

    except Exception as e:
        logger.error(f"Erreur envoi SMS générique: {e}")


@receiver(post_save, sender=Payment)
def handle_payment_failure(sender, instance, created, **kwargs):
    """
    Signal déclenché quand un paiement échoue

    Nettoie les ressources et informe le client
    """
    if instance.status == 'failed':
        logger.info(f"Paiement {instance.payment_number} échoué - Nettoyage")

        try:
            # Annuler ticket/RDV en attente si applicable
            if instance.ticket and instance.ticket.status == 'pending_payment':
                instance.ticket.status = 'cancelled'
                instance.ticket.save(update_fields=['status'])

            if instance.appointment and instance.appointment.status == 'pending_payment':
                instance.appointment.status = 'cancelled'
                instance.appointment.save(update_fields=['status'])

            # Envoyer SMS d'échec
            _send_payment_failure_notification(instance)

        except Exception as e:
            logger.error(f"Erreur nettoyage paiement échoué {instance.payment_number}: {e}")


def _send_payment_failure_notification(payment: Payment):
    """
    Envoyer SMS de notification d'échec de paiement
    """
    try:
        from apps.notifications.sms_service import sms_service

        message = (
            f"SmartQueue: Échec paiement {payment.total_amount} FCFA. "
            f"Réf: {payment.payment_number}. "
            f"Veuillez réessayer ou contacter le support."
        )

        result = sms_service.send_sms(payment.payer_phone, message)

        if result['success']:
            logger.info(f"SMS échec paiement envoyé: {payment.payment_number}")

    except Exception as e:
        logger.error(f"Erreur envoi SMS échec: {e}")