# apps/payments/views.py
"""
Vues pour les paiements SmartQueue Sénégal
APIs REST pour Wave Money, Orange Money, Free Money
"""

from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.conf import settings
from django.utils import timezone
from django.db import transaction, models
from decimal import Decimal
import requests
import hashlib
import hmac
import json
import logging
from datetime import timedelta

from .models import (
    PaymentProvider, Payment, PaymentMethod, PaymentLog, PaymentPlan, SubscriptionInvoice
)
from .serializers import (
    PaymentProviderSerializer, PaymentCreateSerializer, PaymentDetailSerializer,
    PaymentListSerializer, PaymentMethodSerializer, PaymentLogSerializer,
    PaymentPlanSerializer, PaymentCallbackSerializer, InitiatePaymentSerializer,
    PaymentStatsSerializer, SubscriptionInvoiceSerializer
)
from .payment_service import payment_service

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary="Liste des fournisseurs de paiement",
        description="Récupère tous les fournisseurs actifs (Wave, Orange, Free)",
        tags=["Payments"]
    ),
    retrieve=extend_schema(
        summary="Détails d'un fournisseur",
        tags=["Payments"]
    )
)
class PaymentProviderViewSet(ModelViewSet):
    """
    ViewSet pour les fournisseurs de paiement
    Lecture seule pour les clients, CRUD pour admins
    """
    queryset = PaymentProvider.objects.filter(is_active=True)
    serializer_class = PaymentProviderSerializer
    
    def get_permissions(self):
        """Lecture libre, modification admin seulement"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [permissions.IsAdminUser]
        return [permission() for permission in permission_classes]


@extend_schema_view(
    list=extend_schema(
        summary="Historique des paiements B2C (par client)",
        description="Liste des paiements de l'utilisateur connecté pour des services (tickets VIP, etc.)",
        tags=["Payments (B2C)"]
    ),
    create=extend_schema(
        summary="Initier un nouveau paiement B2C",
        description="Créer un paiement pour un service (ex: ticket VIP)",
        tags=["Payments (B2C)"]
    ),
    retrieve=extend_schema(
        summary="Détails d'un paiement B2C",
        tags=["Payments (B2C)"]
    )
)
class PaymentViewSet(ModelViewSet):
    """
    ViewSet principal pour les paiements B2C (client -> organisation)
    """
    serializer_class = PaymentListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Utilisateur voit seulement ses paiements B2C"""
        return Payment.objects.filter(customer=self.request.user)
    
    def get_serializer_class(self):
        """Serializer spécifique selon l'action"""
        if self.action == 'create':
            return PaymentCreateSerializer
        elif self.action == 'retrieve':
            return PaymentDetailSerializer
        return PaymentListSerializer
    
    def perform_create(self, serializer):
        """Créer un paiement et l'envoyer au provider"""
        payment = serializer.save(
            customer=self.request.user,
            created_ip=self.get_client_ip()
        )
        
        # Envoyer au fournisseur de paiement
        self.process_payment(payment)
    
    def get_client_ip(self):
        """Récupérer l'IP du client"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def process_payment(self, payment):
        """Traiter le paiement selon le provider"""
        provider_type = payment.provider.provider_type
        
        try:
            if provider_type == 'wave':
                self.process_wave_payment(payment)
            elif provider_type == 'orange_money':
                self.process_orange_payment(payment)
            elif provider_type == 'free_money':
                self.process_free_payment(payment)
            else:
                raise ValueError(f"Provider {provider_type} non supporté")
                
        except Exception as e:
            logger.error(f"Erreur paiement {payment.payment_number}: {str(e)}")
            payment.mark_as_failed(
                error_code="PROCESSING_ERROR",
                error_message=str(e)
            )
    
    def process_wave_payment(self, payment):
        """Traiter paiement Wave Money"""
        url = payment.provider.api_url + "/checkout/sessions"
        
        headers = {
            'Authorization': f'Bearer {payment.provider.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'amount': int(payment.total_amount),
            'currency': payment.currency,
            'error_url': f"{settings.FRONTEND_URL}/payment/error",
            'success_url': f"{settings.FRONTEND_URL}/payment/success",
            'checkout_intent': 'web_payment',
            'client_reference': payment.payment_number,
            'description': payment.description,
            'customer_email': payment.customer.email,
            'customer_phone': payment.payer_phone,
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            payment.external_reference = result.get('id')
            payment.metadata = result
            payment.status = 'processing'
            payment.save()
            
            # Log de l'envoi
            PaymentLog.objects.create(
                payment=payment,
                action='sent_to_provider',
                details={'request': data, 'response': result},
                http_status=response.status_code
            )
        else:
            raise Exception(f"Wave API error: {response.text}")
    
    def process_orange_payment(self, payment):
        """Traiter paiement Orange Money"""
        # Implémentation Orange Money API
        url = payment.provider.api_url + "/omcoreapis/1.0.2/mp/pay"
        
        # Signature Orange Money
        timestamp = str(int(timezone.now().timestamp()))
        to_sign = f"amount={payment.total_amount}&callback_url={settings.PAYMENT_CALLBACK_URL}&client_reference={payment.payment_number}&timestamp={timestamp}"
        signature = hmac.new(
            payment.provider.api_secret.encode(),
            to_sign.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Authorization': f'Bearer {payment.provider.api_key}',
            'Content-Type': 'application/json',
            'X-Timestamp': timestamp,
            'X-Signature': signature
        }
        
        data = {
            'amount': payment.total_amount,
            'currency': payment.currency,
            'callback_url': f"{settings.PAYMENT_CALLBACK_URL}/orange/",
            'client_reference': payment.payment_number,
            'description': payment.description,
            'customer_phone': payment.payer_phone,
            'merchant_id': payment.provider.merchant_id
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code in [200, 201]:
            result = response.json()
            payment.external_reference = result.get('transaction_id')
            payment.metadata = result
            payment.status = 'processing'
            payment.save()
            
            PaymentLog.objects.create(
                payment=payment,
                action='sent_to_provider',
                details={'request': data, 'response': result},
                http_status=response.status_code
            )
        else:
            raise Exception(f"Orange Money API error: {response.text}")
    
    def process_free_payment(self, payment):
        """Traiter paiement Free Money"""
        # Implémentation Free Money API
        url = payment.provider.api_url + "/api/v1/payments"
        
        headers = {
            'Authorization': f'Bearer {payment.provider.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'amount': payment.total_amount,
            'currency': payment.currency,
            'reference': payment.payment_number,
            'description': payment.description,
            'customer_phone': payment.payer_phone,
            'callback_url': f"{settings.PAYMENT_CALLBACK_URL}/free/",
            'merchant_code': payment.provider.merchant_id
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            payment.external_reference = result.get('payment_id')
            payment.metadata = result
            payment.status = 'processing'
            payment.save()
            
            PaymentLog.objects.create(
                payment=payment,
                action='sent_to_provider',
                details={'request': data, 'response': result},
                http_status=response.status_code
            )
        else:
            raise Exception(f"Free Money API error: {response.text}")
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Annuler un paiement"""
        payment = self.get_object()
        
        if payment.can_be_cancelled():
            payment.status = 'cancelled'
            payment.save()
            
            PaymentLog.objects.create(
                payment=payment,
                action='cancelled',
                details={'cancelled_by': request.user.id}
            )
            
            return Response({'status': 'cancelled'})
        
        return Response(
            {'error': 'Ce paiement ne peut pas être annulé'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['get'])
    def status_check(self, request, pk=None):
        """Vérifier le statut d'un paiement"""
        payment = self.get_object()
        
        # Vérifier auprès du provider si nécessaire
        if payment.status == 'processing':
            self.check_payment_status(payment)
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data)
    
    def check_payment_status(self, payment):
        """Vérifier le statut auprès du provider"""
        try:
            if payment.provider.provider_type == 'wave':
                self.check_wave_status(payment)
            elif payment.provider.provider_type == 'orange_money':
                self.check_orange_status(payment)
            elif payment.provider.provider_type == 'free_money':
                self.check_free_status(payment)
        except Exception as e:
            logger.error(f"Erreur vérification statut {payment.payment_number}: {str(e)}")
    
    def check_wave_status(self, payment):
        """Vérifier statut Wave"""
        if not payment.external_reference:
            return
        
        url = f"{payment.provider.api_url}/checkout/sessions/{payment.external_reference}"
        headers = {'Authorization': f'Bearer {payment.provider.api_key}'}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            wave_status = result.get('payment_status')
            
            if wave_status == 'completed':
                payment.mark_as_completed(
                    external_reference=result.get('payment_id'),
                    metadata=result
                )
            elif wave_status == 'failed':
                payment.mark_as_failed(
                    error_code=result.get('error_code'),
                    error_message=result.get('error_message')
                )

    def check_orange_status(self, payment):
        """Vérifier statut Orange Money"""
        if not payment.external_reference:
            return

        url = f"{payment.provider.api_url}/omcoreapis/1.0.2/mp/transactions/{payment.external_reference}"

        headers = {
            'Authorization': f'Bearer {payment.provider.api_key}',
            'Content-Type': 'application/json',
            'X-Timestamp': str(int(timezone.now().timestamp())), # Assuming timestamp is needed for status check
            'X-Signature': self._generate_orange_signature_for_status_check(payment) # Need to implement this helper
        }

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            orange_status = result.get('status')

            if orange_status == 'SUCCESSFUL':
                payment.mark_as_completed(
                    external_reference=result.get('transaction_id'),
                    metadata=result
                )
            elif orange_status in ['FAILED', 'CANCELLED']:
                payment.mark_as_failed(
                    error_code=result.get('error_code'),
                    error_message=result.get('error_message')
                )
        else:
            logger.error(f"Erreur vérification statut Orange Money pour {payment.payment_number}: {response.text}")

    def _generate_orange_signature_for_status_check(self, payment):
        """Générer la signature pour la vérification de statut Orange Money"""
        # La logique de signature pour la vérification de statut peut différer de l'initiation.
        # Il est crucial de consulter la documentation officielle d'Orange Money.
        # Pour l'exemple, nous allons signer l'external_reference et le timestamp.
        timestamp = str(int(timezone.now().timestamp()))
        to_sign = f"external_reference={payment.external_reference}&timestamp={timestamp}"
        
        signature = hmac.new(
            payment.provider.api_secret.encode(),
            to_sign.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature

    def check_free_status(self, payment):
        """Vérifier statut Free Money"""
        if not payment.external_reference:
            return

        # Assuming Free Money has a status check endpoint similar to Wave/Orange
        # This URL and parameters are speculative and need official documentation.
        url = f"{payment.provider.api_url}/api/v1/payments/{payment.external_reference}/status"

        headers = {
            'Authorization': f'Bearer {payment.provider.api_key}',
            'Content-Type': 'application/json'
        }

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            free_status = result.get('status')

            if free_status == 'completed':
                payment.mark_as_completed(
                    external_reference=result.get('payment_id'),
                    metadata=result
                )
            elif free_status == 'failed':
                payment.mark_as_failed(
                    error_code=result.get('error_code'),
                    error_message=result.get('error_message')
                )
        else:
            logger.error(f"Erreur vérification statut Free Money pour {payment.payment_number}: {response.text}")


@extend_schema_view(
    list=extend_schema(
        summary="[B2B] Factures de mon organisation",
        description="Liste les factures d'abonnement pour l'organisation de l'utilisateur connecté.",
        tags=["Payments (B2B)"]
    )
)
class MyOrganizationInvoicesView(generics.ListAPIView):
    """
    Vue pour que les admins d'organisation voient leurs factures.
    """
    serializer_class = SubscriptionInvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Retourne les factures pour l'organisation de l'utilisateur connecté."""
        user = self.request.user

        # Pour les super-admins, retourner toutes les factures
        if user.is_superuser:
            return SubscriptionInvoice.objects.all()

        # Pour les utilisateurs normaux (staff/admin d'organisation)
        # On suppose une relation via un profil, ex: user.staff_profile.organization
        if hasattr(user, 'staff_profile') and user.staff_profile.organization:
            return SubscriptionInvoice.objects.filter(organization=user.staff_profile.organization)
        
        # Si l'utilisateur n'est lié à aucune organisation, ne rien retourner
        return SubscriptionInvoice.objects.none()


@extend_schema(
    summary="[B2B] Payer une facture d'abonnement",
    description="Initie une transaction pour régler une facture d'abonnement spécifique.",
    tags=["Payments (B2B)"]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def pay_invoice_view(request, invoice_id):
    """
    Initie le paiement pour une facture d'abonnement.
    """
    try:
        invoice = SubscriptionInvoice.objects.get(id=invoice_id)
    except SubscriptionInvoice.DoesNotExist:
        return Response({'error': 'Facture non trouvée.'}, status=status.HTTP_404_NOT_FOUND)

    # Vérifier les permissions
    user = request.user
    if not user.is_superuser and (not hasattr(user, 'staff_profile') or user.staff_profile.organization != invoice.organization):
        return Response({'error': 'Permission refusée.'}, status=status.HTTP_403_FORBIDDEN)

    # Récupérer le numéro de téléphone du payeur depuis le corps de la requête
    payer_phone = request.data.get('payer_phone')
    if not payer_phone:
        return Response({'error': 'Le champ payer_phone est requis.'}, status=status.HTTP_400_BAD_REQUEST)

    # Initier le paiement via le service
    result = payment_service.initiate_invoice_payment(
        invoice=invoice,
        paying_user=user,
        payer_phone=payer_phone
    )

    if result.get('success'):
        return Response({'message': 'Initiation du paiement réussie.', 'data': result}, status=status.HTTP_200_OK)
    else:
        return Response({'error': result.get('error', 'Erreur inconnue')}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Webhook Wave Money",
    description="Callback Wave pour mise à jour statut paiement",
    tags=["Payments", "Webhooks"]
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def wave_callback(request):
    """
    Webhook Wave Money
    POST /api/payments/webhooks/wave/
    """
    try:
        data = request.data
        payment_number = data.get('client_reference')
        
        if not payment_number:
            return Response({'error': 'client_reference manquant'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        payment = Payment.objects.get(payment_number=payment_number)
        
        # Vérifier la signature Wave (sécurité)
        # Récupérer la signature du header
        signature = request.headers.get('X-Wave-Signature')
        if not signature:
            logger.warning(f"Callback Wave sans signature pour paiement {payment_number}")
            return Response({'error': 'Signature manquante'}, status=status.HTTP_400_BAD_REQUEST)

        # Récupérer le corps brut de la requête
        # request.body contient le corps brut de la requête POST
        raw_body = request.body

        # Récupérer le secret API du fournisseur
        provider_secret = payment.provider.api_secret.encode('utf-8')

        # Calculer la signature attendue
        # Assurez-vous que le secret est encodé en bytes
        expected_signature = hmac.new(
            provider_secret,
            raw_body,
            hashlib.sha256
        ).hexdigest()

        # Comparer les signatures
        if not hmac.compare_digest(expected_signature, signature):
            logger.warning(f"Signature Wave invalide pour paiement {payment_number}")
            return Response({'error': 'Signature invalide'}, status=status.HTTP_403_FORBIDDEN)
        
        wave_status = data.get('payment_status')
        
        if wave_status == 'completed':
            payment.mark_as_completed(
                external_reference=data.get('payment_id'),
                metadata=data
            )
        elif wave_status == 'failed':
            payment.mark_as_failed(
                error_code=data.get('error_code'),
                error_message=data.get('error_message')
            )
        
        # Log du callback
        PaymentLog.objects.create(
            payment=payment,
            action='callback_received',
            details=data
        )
        
        return Response({'status': 'processed'})
        
    except Payment.DoesNotExist:
        logger.error(f"Paiement {payment_number} introuvable pour callback Wave")
        return Response({'error': 'Paiement introuvable'}, 
                       status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur callback Wave: {str(e)}")
        return Response({'error': 'Erreur serveur'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Webhook Orange Money",
    description="Callback Orange Money pour mise à jour statut",
    tags=["Payments", "Webhooks"]
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def orange_callback(request):
    """
    Webhook Orange Money
    POST /api/payments/webhooks/orange/
    """
    try:
        data = request.data
        payment_number = data.get('client_reference')
        
        payment = Payment.objects.get(payment_number=payment_number)

        # Vérifier la signature Orange Money (sécurité)
        signature = request.headers.get('X-Signature')
        timestamp = request.headers.get('X-Timestamp') # Assuming timestamp is also sent in header

        if not signature or not timestamp:
            logger.warning(f"Callback Orange Money sans signature/timestamp pour paiement {payment_number}")
            return Response({'error': 'Signature ou Timestamp manquant'}, status=status.HTTP_400_BAD_REQUEST)

        # Reconstruire la chaîne à signer (doit correspondre à la logique de Orange Money)
        # Basé sur la logique de process_orange_payment, mais adapté pour le callback
        # Il est crucial de s'assurer que cette chaîne correspond EXACTEMENT à ce que Orange Money signe.
        # Pour l'exemple, nous utilisons les champs clés du callback.
        # NOTE: La documentation officielle d'Orange Money est nécessaire pour une implémentation exacte.
        to_sign = f"amount={data.get('amount')}&callback_url={settings.PAYMENT_CALLBACK_URL}/orange/&client_reference={payment_number}&timestamp={timestamp}"

        provider_secret = payment.provider.api_secret.encode('utf-8')

        expected_signature = hmac.new(
            provider_secret,
            to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            logger.warning(f"Signature Orange Money invalide pour paiement {payment_number}")
            return Response({'error': 'Signature invalide'}, status=status.HTTP_403_FORBIDDEN)
        
        orange_status = data.get('status')
        
        if orange_status == 'SUCCESSFUL':
            payment.mark_as_completed(
                external_reference=data.get('transaction_id'),
                metadata=data
            )
        elif orange_status in ['FAILED', 'CANCELLED']:
            payment.mark_as_failed(
                error_code=data.get('error_code'),
                error_message=data.get('error_message')
            )
        
        PaymentLog.objects.create(
            payment=payment,
            action='callback_received',
            details=data
        )
        
        return Response({'status': 'processed'})
        
    except Payment.DoesNotExist:
        return Response({'error': 'Paiement introuvable'}, 
                       status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur callback Orange: {str(e)}")
        return Response({'error': 'Erreur serveur'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Webhook Free Money",
    description="Callback Free Money pour mise à jour statut",
    tags=["Payments", "Webhooks"]
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def free_callback(request):
    """
    Webhook Free Money
    POST /api/payments/webhooks/free/
    """
    try:
        data = request.data
        payment_reference = data.get('reference')
        
        payment = Payment.objects.get(payment_number=payment_reference)
        
        free_status = data.get('status')
        
        if free_status == 'completed':
            payment.mark_as_completed(
                external_reference=data.get('payment_id'),
                metadata=data
            )
        elif free_status == 'failed':
            payment.mark_as_failed(
                error_code=data.get('error_code'),
                error_message=data.get('error_message')
            )
        
        PaymentLog.objects.create(
            payment=payment,
            action='callback_received',
            details=data
        )
        
        return Response({'status': 'processed'})
        
    except Payment.DoesNotExist:
        return Response({'error': 'Paiement introuvable'}, 
                       status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Erreur callback Free: {str(e)}")
        return Response({'error': 'Erreur serveur'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema_view(
    list=extend_schema(
        summary="Méthodes de paiement utilisateur",
        description="Liste des moyens de paiement sauvegardés",
        tags=["Payments (B2C)"]
    ),
    create=extend_schema(
        summary="Ajouter une méthode de paiement",
        tags=["Payments (B2C)"]
    )
)
class PaymentMethodViewSet(ModelViewSet):
    """
    ViewSet pour les méthodes de paiement sauvegardées
    """
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PaymentMethod.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(
        summary="[B2B] Liste des plans de tarification",
        description="Liste des plans d'abonnement disponibles pour les organisations",
        tags=["Payments (B2B)"]
    )
)
class PaymentPlanViewSet(generics.ListAPIView):
    """
    ViewSet pour les plans de tarification (lecture seule)
    """
    queryset = PaymentPlan.objects.filter(is_active=True)
    serializer_class = PaymentPlanSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    summary="Statistiques paiements B2C",
    description="Stats des paiements de l'utilisateur connecté",
    tags=["Payments (B2C)"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_stats(request):
    """
    Statistiques de paiements pour l'utilisateur
    GET /api/payments/stats/
    """
    user = request.user
    
    # Calculer les statistiques
    total_payments = Payment.objects.filter(customer=user).count()
    completed_payments = Payment.objects.filter(
        customer=user, 
        status='completed'
    ).count()
    
    total_amount = Payment.objects.filter(
        customer=user, 
        status='completed'
    ).aggregate(
        total=models.Sum('total_amount')
    )['total'] or Decimal('0')
    
    pending_payments = Payment.objects.filter(
        customer=user, 
        status__in=['pending', 'processing']
    ).count()
    
    stats = {
        'total_payments': total_payments,
        'completed_payments': completed_payments,
        'pending_payments': pending_payments,
        'total_amount_paid': float(total_amount),
        'success_rate': (completed_payments / total_payments * 100) if total_payments > 0 else 0,
        'currency': 'XOF'
    }
    
    return Response(stats)


@extend_schema(
    summary="Initier un paiement mobile money",
    description="Démarre une transaction Wave/Orange Money/Free Money",
    tags=["Payments - Mobile Money"],
    request=InitiatePaymentSerializer,
    responses={201: PaymentDetailSerializer}
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def initiate_payment(request):
    """
    Initier un paiement mobile money
    POST /api/payments/initiate/

    Body:
    {
        "phone_number": "+221781234567",
        "amount": 1000.00,
        "description": "Ticket SmartQueue",
        "organization_id": 1,
        "ticket_id": null,
        "appointment_id": null,
        "provider": "wave"
    }
    """
    from apps.business.models import Organization
    from apps.queue_management.models import Ticket
    from apps.appointments.models import Appointment

    data = request.data

    try:
        # Validation des données requises
        phone_number = data.get('phone_number')
        amount = Decimal(str(data.get('amount', 0)))
        description = data.get('description', 'Paiement SmartQueue')
        organization_id = data.get('organization_id')
        provider = data.get('provider', payment_service.default_provider)

        if not phone_number or amount <= 0 or not organization_id:
            return Response({
                'error': 'phone_number, amount et organization_id sont requis'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Récupérer les objets liés
        try:
            organization = Organization.objects.get(id=organization_id)
        except Organization.DoesNotExist:
            return Response({
                'error': f'Organisation {organization_id} non trouvée'
            }, status=status.HTTP_404_NOT_FOUND)

        ticket = None
        appointment = None

        if data.get('ticket_id'):
            try:
                ticket = Ticket.objects.get(id=data['ticket_id'])
            except Ticket.DoesNotExist:
                return Response({
                    'error': f'Ticket {data["ticket_id"]} non trouvé'
                }, status=status.HTTP_404_NOT_FOUND)

        if data.get('appointment_id'):
            try:
                appointment = Appointment.objects.get(id=data['appointment_id'])
            except Appointment.DoesNotExist:
                return Response({
                    'error': f'RDV {data["appointment_id"]} non trouvé'
                }, status=status.HTTP_404_NOT_FOUND)

        # Initier le paiement
        result = payment_service.initiate_payment(
            customer_phone=phone_number,
            amount=amount,
            description=description,
            customer=request.user,
            organization=organization,
            ticket=ticket,
            appointment=appointment,
            provider_name=provider
        )

        if result['success']:
            # Récupérer le paiement créé
            payment = Payment.objects.get(id=result['payment_id'])
            serializer = PaymentDetailSerializer(payment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)

    except ValueError as e:
        return Response({
            'error': f'Données invalides: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Erreur initiation paiement: {e}")
        return Response({
            'error': 'Erreur interne du serveur'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Vérifier le statut d'un paiement",
    description="Obtenir les détails et statut actuels d'un paiement",
    tags=["Payments - Mobile Money"],
    responses={200: PaymentDetailSerializer}
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_payment_status(request, payment_id):
    """
    Vérifier le statut d'un paiement
    GET /api/payments/{payment_id}/status/
    """
    try:
        payment = Payment.objects.get(
            id=payment_id,
            customer=request.user
        )

        # Utiliser le service pour obtenir le statut à jour
        status_result = payment_service.check_payment_status(payment_id)

        if status_result['success']:
            serializer = PaymentDetailSerializer(payment)
            return Response(serializer.data)
        else:
            return Response({
                'error': status_result['error']
            }, status=status.HTTP_400_BAD_REQUEST)

    except Payment.DoesNotExist:
        return Response({
            'error': 'Paiement non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    summary="Logs des paiements utilisateur",
    description="Historique détaillé des logs de paiements pour l'utilisateur connecté",
    tags=["Payments (B2C)"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_logs_view(request):
    """
    Vue pour lister les logs de paiements de l'utilisateur
    GET /api/payments/logs/
    """
    user = request.user

    # Récupérer les logs des paiements de l'utilisateur
    user_payments = Payment.objects.filter(customer=user)
    logs = PaymentLog.objects.filter(
        payment__in=user_payments
    ).select_related('payment').order_by('-created_at')

    # Pagination optionnelle
    from django.core.paginator import Paginator
    page_size = request.GET.get('page_size', 20)
    paginator = Paginator(logs, page_size)
    page_number = request.GET.get('page', 1)
    page_logs = paginator.get_page(page_number)

    # Sérializer les logs
    serializer = PaymentLogSerializer(page_logs, many=True)

    return Response({
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': page_logs.number,
        'has_next': page_logs.has_next(),
        'has_previous': page_logs.has_previous(),
        'results': serializer.data
    })


@extend_schema(
    summary="Statut des providers de paiement",
    description="Liste des providers disponibles et leur statut",
    tags=["Payments - Mobile Money"]
)
@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def payment_providers_status(request):
    """
    Obtenir le statut des providers de paiement
    GET /api/payments/providers/status/
    """
    status_data = payment_service.get_payment_providers_status()
    return Response(status_data)


@extend_schema(
    summary="Callback des providers de paiement",
    description="Endpoint pour recevoir les callbacks de confirmation",
    tags=["Payments - Callbacks"],
    request=PaymentCallbackSerializer
)
@api_view(['POST'])
@permission_classes([permissions.AllowAny])  # Les callbacks viennent de l'extérieur
def payment_callback(request, provider_name):
    """
    Recevoir les callbacks des providers de paiement
    POST /api/payments/callback/{provider_name}/

    PLACEHOLDER - En attente des spécifications de callbacks
    """
    try:
        callback_data = request.data

        # Logger le callback reçu
        logger.info(f"Callback reçu de {provider_name}: {callback_data}")

        # Traiter le callback
        result = payment_service.handle_payment_callback(provider_name, callback_data)

        if result['success']:
            return Response({'status': 'ok'})
        else:
            return Response({
                'error': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Erreur callback {provider_name}: {e}")
        return Response({
            'error': 'Erreur traitement callback'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Simuler un paiement réussi",
    description="API pour simuler la confirmation d'un paiement (développement uniquement)",
    tags=["Payments - Simulation"],
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def simulate_payment_success(request, payment_id):
    """
    Simuler la réussite d'un paiement
    POST /api/payments/{payment_id}/simulate-success/

    DÉVELOPPEMENT UNIQUEMENT - Pour tester le workflow complet
    """
    if not settings.DEBUG:
        return Response({
            'error': 'API disponible uniquement en mode développement'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        from .utils import simulate_payment_success as sim_success

        payment = Payment.objects.get(
            id=payment_id,
            customer=request.user
        )

        success = sim_success(payment_id, f"SIM_{timezone.now().strftime('%Y%m%d%H%M%S')}")

        if success:
            # Recharger le paiement pour avoir les données à jour
            payment.refresh_from_db()
            serializer = PaymentDetailSerializer(payment)
            return Response({
                'message': 'Paiement simulé comme réussi',
                'payment': serializer.data
            })
        else:
            return Response({
                'error': 'Impossible de simuler ce paiement'
            }, status=status.HTTP_400_BAD_REQUEST)

    except Payment.DoesNotExist:
        return Response({
            'error': 'Paiement non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    summary="Logs des paiements utilisateur",
    description="Historique détaillé des logs de paiements pour l'utilisateur connecté",
    tags=["Payments (B2C)"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_logs_view(request):
    """
    Vue pour lister les logs de paiements de l'utilisateur
    GET /api/payments/logs/
    """
    user = request.user

    # Récupérer les logs des paiements de l'utilisateur
    user_payments = Payment.objects.filter(customer=user)
    logs = PaymentLog.objects.filter(
        payment__in=user_payments
    ).select_related('payment').order_by('-created_at')

    # Pagination optionnelle
    from django.core.paginator import Paginator
    page_size = request.GET.get('page_size', 20)
    paginator = Paginator(logs, page_size)
    page_number = request.GET.get('page', 1)
    page_logs = paginator.get_page(page_number)

    # Sérializer les logs
    serializer = PaymentLogSerializer(page_logs, many=True)

    return Response({
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': page_logs.number,
        'has_next': page_logs.has_next(),
        'has_previous': page_logs.has_previous(),
        'results': serializer.data
    })


@extend_schema(
    summary="Simuler un paiement échoué",
    description="API pour simuler l'échec d'un paiement (développement uniquement)",
    tags=["Payments - Simulation"]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def simulate_payment_failure(request, payment_id):
    """
    Simuler l'échec d'un paiement
    POST /api/payments/{payment_id}/simulate-failure/

    DÉVELOPPEMENT UNIQUEMENT
    """
    if not settings.DEBUG:
        return Response({
            'error': 'API disponible uniquement en mode développement'
        }, status=status.HTTP_403_FORBIDDEN)

    try:
        from .utils import simulate_payment_failure as sim_failure

        payment = Payment.objects.get(
            id=payment_id,
            customer=request.user
        )

        error_message = request.data.get('error_message', 'Paiement simulé comme échoué')

        success = sim_failure(payment_id, error_message)

        if success:
            payment.refresh_from_db()
            serializer = PaymentDetailSerializer(payment)
            return Response({
                'message': 'Paiement simulé comme échoué',
                'payment': serializer.data
            })
        else:
            return Response({
                'error': "Impossible de simuler l'échec de ce paiement"
            }, status=status.HTTP_400_BAD_REQUEST)

    except Payment.DoesNotExist:
        return Response({
            'error': 'Paiement non trouvé'
        }, status=status.HTTP_404_NOT_FOUND)


@extend_schema(
    summary="Logs des paiements utilisateur",
    description="Historique détaillé des logs de paiements pour l'utilisateur connecté",
    tags=["Payments (B2C)"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_logs_view(request):
    """
    Vue pour lister les logs de paiements de l'utilisateur
    GET /api/payments/logs/
    """
    user = request.user

    # Récupérer les logs des paiements de l'utilisateur
    user_payments = Payment.objects.filter(customer=user)
    logs = PaymentLog.objects.filter(
        payment__in=user_payments
    ).select_related('payment').order_by('-created_at')

    # Pagination optionnelle
    from django.core.paginator import Paginator
    page_size = request.GET.get('page_size', 20)
    paginator = Paginator(logs, page_size)
    page_number = request.GET.get('page', 1)
    page_logs = paginator.get_page(page_number)

    # Sérializer les logs
    serializer = PaymentLogSerializer(page_logs, many=True)

    return Response({
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': page_logs.number,
        'has_next': page_logs.has_next(),
        'has_previous': page_logs.has_previous(),
        'results': serializer.data
    })