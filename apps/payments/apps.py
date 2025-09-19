from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payments'
    verbose_name = 'Paiements Mobile Money'

    def ready(self):
        """Importer les signaux quand l'app est prête"""
        import apps.payments.signals
