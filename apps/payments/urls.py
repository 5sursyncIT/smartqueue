# apps/payments/urls.py
"""
URLs pour les paiements SmartQueue Sénégal
APIs Wave Money, Orange Money, Free Money
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PaymentProviderViewSet,
    PaymentViewSet,
    PaymentMethodViewSet,
    PaymentPlanViewSet,
    MyOrganizationInvoicesView,
    pay_invoice_view, # Ajout de la nouvelle vue de paiement
    wave_callback,
    orange_callback,
    free_callback,
    payment_stats,
    initiate_payment,
    check_payment_status,
    payment_providers_status,
    payment_callback,
    simulate_payment_success,
    simulate_payment_failure,
    payment_logs_view
)

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'providers', PaymentProviderViewSet, basename='payment-provider')
router.register(r'payments', PaymentViewSet, basename='payment') # B2C Payments
router.register(r'methods', PaymentMethodViewSet, basename='payment-method')

app_name = 'payments'

urlpatterns = [
    # APIs REST B2C (client -> organisation)
    path('api/', include(router.urls)),
    path('api/payments/stats/', payment_stats, name='payment-stats'),
    path('api/payments/logs/', payment_logs_view, name='payment-logs'),

    # APIs REST B2B (organisation -> smartqueue)
    path('api/my-organization/invoices/', MyOrganizationInvoicesView.as_view(), name='my-organization-invoices'),
    path('api/invoices/<int:invoice_id>/pay/', pay_invoice_view, name='pay-invoice'), # NOUVELLE URL
    path('api/plans/', PaymentPlanViewSet.as_view(), name='payment-plans'),

    # Endpoints de paiement mobile money (communs)
    path('api/payments/initiate/', initiate_payment, name='initiate-payment'),
    path('api/payments/<int:payment_id>/status/', check_payment_status, name='check-payment-status'),
    path('api/payments/providers/status/', payment_providers_status, name='payment-providers-status'),
    path('api/payments/callback/<str:provider_name>/', payment_callback, name='payment-callback'),

    # APIs de simulation (développement uniquement)
    path('api/payments/<int:payment_id>/simulate-success/', simulate_payment_success, name='simulate-payment-success'),
    path('api/payments/<int:payment_id>/simulate-failure/', simulate_payment_failure, name='simulate-payment-failure'),

    # Webhooks des providers (URLs publiques)
    path('webhooks/wave/', wave_callback, name='wave-callback'),
    path('webhooks/orange/', orange_callback, name='orange-callback'),
    path('webhooks/free/', free_callback, name='free-callback'),
]