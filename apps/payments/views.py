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
    PaymentProvider, Payment, PaymentMethod, PaymentLog, PaymentPlan
)
from .serializers import (
    PaymentProviderSerializer, PaymentCreateSerializer, PaymentDetailSerializer,
    PaymentListSerializer, PaymentMethodSerializer, PaymentLogSerializer, 
    PaymentPlanSerializer, PaymentCallbackSerializer, InitiatePaymentSerializer,
    PaymentStatsSerializer
)

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
        summary="Historique des paiements utilisateur",
        description="Liste des paiements de l'utilisateur connecté",
        tags=["Payments"]
    ),
    create=extend_schema(
        summary="Initier un nouveau paiement",
        description="Créer un paiement Wave/Orange/Free Money",
        tags=["Payments"]
    ),
    retrieve=extend_schema(
        summary="Détails d'un paiement",
        tags=["Payments"]
    )
)
class PaymentViewSet(ModelViewSet):
    """
    ViewSet principal pour les paiements
    """
    serializer_class = PaymentListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Utilisateur voit seulement ses paiements"""
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
        # TODO: Implémenter vérification signature
        
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
        tags=["Payments"]
    ),
    create=extend_schema(
        summary="Ajouter une méthode de paiement",
        tags=["Payments"]
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
        summary="Plans de tarification",
        description="Liste des plans disponibles pour organisations",
        tags=["Payments"]
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
    summary="Statistiques paiements",
    description="Stats des paiements pour l'utilisateur connecté",
    tags=["Payments"]
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
