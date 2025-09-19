import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.payments.models import SubscriptionInvoice
from apps.notifications.services import NotificationAutomationService # Import the automation service

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Checks for overdue subscription invoices and triggers reminders."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🚀 Checking for overdue invoices..."))

        today = timezone.now().date()
        notification_automation_service = NotificationAutomationService() # Instantiate the service

        overdue_invoices = SubscriptionInvoice.objects.filter(
            status='due',
            due_date__lt=today
        )

        if not overdue_invoices.exists():
            self.stdout.write(self.style.WARNING("No overdue invoices found."))
            return

        self.stdout.write(f"Found {overdue_invoices.count()} overdue invoice(s).")

        sent_reminders = 0
        for invoice in overdue_invoices:
            try:
                # Check if a reminder has been sent recently (e.g., within the last 24 hours)
                # This prevents spamming reminders
                if invoice.last_reminder_sent_at and (timezone.now() - invoice.last_reminder_sent_at).total_seconds() < 24 * 3600:
                    self.stdout.write(self.style.NOTICE(f"⚠️ Reminder for invoice {invoice.invoice_number} already sent recently. Skipping."))
                    continue

                # Trigger notification using the automation service
                notification_automation_service.notify_invoice_reminder(invoice)
                
                # Update invoice status and last reminder sent timestamp
                invoice.status = 'overdue'
                invoice.last_reminder_sent_at = timezone.now()
                invoice.save(update_fields=['status', 'last_reminder_sent_at'])

                self.stdout.write(self.style.SUCCESS(f"✅ Reminder sent for invoice {invoice.invoice_number} (Org: {invoice.organization.name}). Invoice status updated to 'overdue'."))
                sent_reminders += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Error sending reminder for invoice {invoice.invoice_number}: {e}"))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("🎉 Overdue invoice check complete."))
        self.stdout.write(f"Reminders sent: {sent_reminders}")
