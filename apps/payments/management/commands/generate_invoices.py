
# apps/payments/management/commands/generate_invoices.py
import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from apps.business.models import Organization
from apps.payments.models import PaymentPlan, SubscriptionInvoice
from apps.queue_management.models import Ticket
from apps.notifications.models import Notification
from apps.appointments.models import Appointment
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Commande Django pour générer les factures d'abonnement mensuelles pour les organisations.
    """
    help = "Génère les factures d'abonnement mensuelles pour les organisations actives."

    def handle(self, *args, **options):
        """
        Logique principale de la commande.
        """
        self.stdout.write(self.style.SUCCESS("🚀 Démarrage de la génération des factures..."))

        today = timezone.now().date()
        billing_period_start = today.replace(day=1)
        billing_period_end = (billing_period_start + relativedelta(months=1)) - relativedelta(days=1)

        # Sélectionner les organisations actives avec un plan d'abonnement
        active_organizations = Organization.objects.filter(
            status='active'
        ).exclude(
            subscription_plan__in=['free', 'custom', '']
        )

        if not active_organizations.exists():
            self.stdout.write(self.style.WARNING("Aucune organisation active avec un plan payant trouvée."))
            return

        self.stdout.write(f"Found {active_organizations.count()} organization(s) to process for the period {billing_period_start} to {billing_period_end}.")

        successful_invoices = 0
        skipped_invoices = 0

        for org in active_organizations:
            # Vérifier si une facture pour cette période existe déjà
            invoice_exists = SubscriptionInvoice.objects.filter(
                organization=org,
                billing_period_start=billing_period_start,
                billing_period_end=billing_period_end
            ).exists()

            if invoice_exists:
                self.stdout.write(self.style.NOTICE(f"Une facture existe déjà pour {org.name} pour cette période. Ignorée."))
                skipped_invoices += 1
                continue

            # Trouver le plan de paiement correspondant
            try:
                payment_plan = PaymentPlan.objects.get(plan_type=org.subscription_plan)
            except PaymentPlan.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"⚠️ Plan de paiement '{org.subscription_plan}' non trouvé pour {org.name}. Facture non créée."))
                continue
            except PaymentPlan.MultipleObjectsReturned:
                self.stderr.write(self.style.ERROR(f"⚠️ Plusieurs plans de paiement '{org.subscription_plan}' trouvés. Facture non créée pour {org.name}."))
                continue

            # Calculer l'utilisation des tickets
            tickets_count = Ticket.objects.filter(
                queue__organization=org,
                created_at__gte=billing_period_start,
                created_at__lte=billing_period_end,
                status='served' # Seuls les tickets servis sont facturés
            ).count()

            # Calculer l'utilisation des SMS
            ticket_content_type = ContentType.objects.get_for_model(Ticket)
            appointment_content_type = ContentType.objects.get_for_model(Appointment)

            org_ticket_ids = Ticket.objects.filter(
                queue__organization=org,
                created_at__gte=billing_period_start,
                created_at__lte=billing_period_end
            ).values_list('id', flat=True)

            org_appointment_ids = Appointment.objects.filter(
                organization=org,
                created_at__gte=billing_period_start,
                created_at__lte=billing_period_end
            ).values_list('id', flat=True)

            sms_count = Notification.objects.filter(
                template__notification_type='sms',
                sent_at__gte=billing_period_start,
                sent_at__lte=billing_period_end
            ).filter(
                Q(content_type=ticket_content_type, object_id__in=list(org_ticket_ids)) |
                Q(content_type=appointment_content_type, object_id__in=list(org_appointment_ids))
            ).count()

            # Calculer les frais d'utilisation
            usage_fees = Decimal('0.00')
            if payment_plan.fee_per_ticket > 0:
                usage_fees += payment_plan.fee_per_ticket * tickets_count
            if payment_plan.fee_per_sms > 0:
                usage_fees += payment_plan.fee_per_sms * sms_count

            total_invoice_amount = payment_plan.monthly_fee + usage_fees

            # Créer la facture
            if total_invoice_amount > 0: # Générer une facture si le montant total est > 0
                try:
                    invoice = SubscriptionInvoice.objects.create(
                        organization=org,
                        plan=payment_plan,
                        amount=total_invoice_amount, # Montant total incluant l'usage
                        billing_period_start=billing_period_start,
                        billing_period_end=billing_period_end,
                        due_date=billing_period_end + relativedelta(days=15) # Échéance 15 jours après la fin du mois
                    )
                    self.stdout.write(self.style.SUCCESS(f"✅ Facture {invoice.invoice_number} créée pour {org.name} d'un montant de {invoice.amount} CFA (Tickets: {tickets_count}, SMS: {sms_count})."))
                    successful_invoices += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"❌ Erreur lors de la création de la facture pour {org.name}: {e}"))
            else:
                self.stdout.write(self.style.NOTICE(f"Le plan '{payment_plan.name}' pour {org.name} est gratuit et/ou l'usage est nul. Aucune facture générée."))


        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("🎉 Opération terminée."))
        self.stdout.write(f"Factures créées: {successful_invoices}")
        self.stdout.write(f"Factures ignorées (déjà existantes): {skipped_invoices}")
