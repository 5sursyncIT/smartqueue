# apps/notifications/views.py
"""
Vues pour les notifications SmartQueue
APIs REST pour SMS, Push, Email sénégalais
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils import timezone
from django.db.models import Count, Q, Avg, Sum
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta, datetime, date
from .models import (
    NotificationTemplate, Notification, NotificationPreference,
    SMSProvider, NotificationLog
)
from .serializers import (
    NotificationTemplateListSerializer, NotificationTemplateDetailSerializer,
    NotificationTemplateCreateSerializer, NotificationListSerializer,
    NotificationDetailSerializer, SendNotificationSerializer,
    NotificationPreferenceSerializer, SMSProviderSerializer,
    NotificationStatsSerializer, NotificationLogSerializer,
    BulkNotificationSerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="Liste des templates de notification",
        description="Voir tous les templates disponibles",
        tags=["Templates"]
    ),
    create=extend_schema(
        summary="Créer un template",
        description="Créer un nouveau template de notification",
        tags=["Templates"]
    ),
    retrieve=extend_schema(
        summary="Détails d'un template",
        description="Voir le contenu complet d'un template",
        tags=["Templates"]
    )
)
class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les templates de notification
    
    Gestion des modèles SMS/Email/Push pour différents événements
    """
    
    queryset = NotificationTemplate.objects.select_related('created_by').all()
    permission_classes = [permissions.IsAuthenticated]
    
    # Filtrage et recherche
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'notification_type', 'is_active']
    search_fields = ['name', 'message_fr', 'message_wo']
    ordering_fields = ['name', 'category', 'created_at']
    ordering = ['category', 'notification_type']
    
    def get_serializer_class(self):
        """Retourne le bon serializer selon l'action"""
        if self.action == 'list':
            return NotificationTemplateListSerializer
        elif self.action == 'retrieve':
            return NotificationTemplateDetailSerializer
        elif self.action == 'create':
            return NotificationTemplateCreateSerializer
        return NotificationTemplateDetailSerializer
    
    def get_permissions(self):
        """Permissions : seuls admins peuvent créer/modifier"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated()]


@extend_schema_view(
    list=extend_schema(
        summary="Mes notifications",
        description="Liste des notifications reçues",
        tags=["Notifications"]
    ),
    retrieve=extend_schema(
        summary="Détails notification",
        description="Voir une notification complète",
        tags=["Notifications"]
    )
)
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les notifications reçues
    
    Les utilisateurs peuvent voir leurs notifications mais pas les modifier
    (les notifications sont créées automatiquement par le système)
    """
    
    queryset = Notification.objects.select_related(
        'recipient', 'template'
    ).prefetch_related('content_type', 'logs').all()
    
    permission_classes = [permissions.IsAuthenticated]
    
    # Filtrage
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'template__category', 'template__notification_type']
    ordering_fields = ['created_at', 'scheduled_at', 'sent_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Serializer selon l'action"""
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationDetailSerializer
    
    def get_queryset(self):
        """Filtrer selon l'utilisateur"""
        user = self.request.user
        
        if user.is_super_admin:
            # Super admin voit toutes les notifications
            return self.queryset
        elif user.is_organization_admin or user.is_staff_member:
            # Staff voit les notifications de son organisation
            if hasattr(user, 'staff_profile'):
                # Notifications liées aux objets de son organisation
                return self.queryset.filter(
                    Q(recipient=user) |  # Ses propres notifications
                    Q(recipient__customer_profile__organization=user.staff_profile.organization) |
                    Q(recipient__staff_profile__organization=user.staff_profile.organization)
                )
        
        # Client voit seulement ses notifications
        return self.queryset.filter(recipient=user)
    
    @extend_schema(
        summary="Marquer comme lu",
        description="Marquer une notification comme lue",
        tags=["Actions"]
    )
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Marquer une notification comme lue
        POST /api/notifications/1/mark_as_read/
        """
        notification = self.get_object()
        
        if notification.recipient != request.user:
            return Response({
                'error': 'Vous ne pouvez marquer que vos propres notifications.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        notification.mark_as_read()
        
        return Response({
            'success': True,
            'message': 'Notification marquée comme lue',
            'read_at': notification.read_at
        })
    
    @extend_schema(
        summary="Historique d'une notification",
        description="Voir les logs d'envoi d'une notification",
        tags=["Historique"]
    )
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """
        Historique des tentatives d'envoi
        GET /api/notifications/1/logs/
        """
        notification = self.get_object()
        logs = notification.logs.all()
        
        serializer = NotificationLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Statistiques notifications",
        description="Stats globales des notifications",
        tags=["Statistiques"]
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Statistiques des notifications
        GET /api/notifications/stats/
        """
        queryset = self.get_queryset()
        
        # Stats générales
        total = queryset.count()
        pending = queryset.filter(status='pending').count()
        sent = queryset.filter(status='sent').count()
        delivered = queryset.filter(status='delivered').count()
        failed = queryset.filter(status='failed').count()
        
        # Période
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        today_count = queryset.filter(created_at__date=today).count()
        week_count = queryset.filter(created_at__date__gte=week_ago).count()
        month_count = queryset.filter(created_at__date__gte=month_ago).count()
        
        # Taux de réussite
        success_rate = ((sent + delivered) / total * 100) if total > 0 else 0
        delivery_rate = (delivered / total * 100) if total > 0 else 0
        
        # Temps de livraison moyen
        delivered_notifications = queryset.filter(
            status='delivered',
            sent_at__isnull=False,
            delivered_at__isnull=False
        )
        
        avg_delivery_time = 0
        if delivered_notifications.exists():
            delivery_times = []
            for notif in delivered_notifications:
                if notif.sent_at and notif.delivered_at:
                    delta = notif.delivered_at - notif.sent_at
                    delivery_times.append(delta.total_seconds() / 60)  # En minutes
            avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        # Répartition par type et catégorie
        by_type = queryset.values(
            'template__notification_type'
        ).annotate(
            count=Count('id')
        )
        
        by_category = queryset.values(
            'template__category'
        ).annotate(
            count=Count('id')
        )
        
        # Stats hebdomadaires
        weekly_stats = []
        for i in range(7):
            day_date = today - timedelta(days=i)
            day_notifications = queryset.filter(created_at__date=day_date)
            weekly_stats.append({
                'date': day_date,
                'day_name': day_date.strftime('%A'),
                'total': day_notifications.count(),
                'sent': day_notifications.filter(status__in=['sent', 'delivered']).count(),
                'failed': day_notifications.filter(status='failed').count()
            })
        
        # Coûts (si disponibles)
        today_cost = NotificationLog.objects.filter(
            created_at__date=today,
            cost__isnull=False
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        month_cost = NotificationLog.objects.filter(
            created_at__date__gte=month_ago,
            cost__isnull=False
        ).aggregate(total=Sum('cost'))['total'] or 0
        
        return Response({
            'total_notifications': total,
            'pending_notifications': pending,
            'sent_notifications': sent,
            'delivered_notifications': delivered,
            'failed_notifications': failed,
            'today_notifications': today_count,
            'weekly_notifications': week_count,
            'monthly_notifications': month_count,
            'success_rate': round(success_rate, 1),
            'delivery_rate': round(delivery_rate, 1),
            'average_delivery_time': round(avg_delivery_time, 1),
            'notifications_by_type': {item['template__notification_type']: item['count'] for item in by_type},
            'notifications_by_category': {item['template__category']: item['count'] for item in by_category},
            'weekly_stats': list(reversed(weekly_stats)),
            'total_cost_today': today_cost,
            'total_cost_month': month_cost
        })


class NotificationPreferenceView(APIView):
    """
    Vue pour les préférences de notification d'un utilisateur
    
    GET : Voir ses préférences
    PUT : Modifier ses préférences
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Mes préférences de notification",
        description="Voir mes paramètres de notification",
        responses=NotificationPreferenceSerializer,
        tags=["Préférences"]
    )
    def get(self, request):
        """
        Préférences de notification de l'utilisateur
        GET /api/notification-preferences/
        """
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        serializer = NotificationPreferenceSerializer(preferences)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Modifier mes préférences",
        description="Mettre à jour mes paramètres de notification",
        request=NotificationPreferenceSerializer,
        responses=NotificationPreferenceSerializer,
        tags=["Préférences"]
    )
    def put(self, request):
        """
        Mettre à jour les préférences
        PUT /api/notification-preferences/
        """
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        
        serializer = NotificationPreferenceSerializer(
            preferences, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        summary="Fournisseurs SMS",
        description="Configuration des opérateurs SMS sénégalais",
        tags=["Administration"]
    )
)
class SMSProviderViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les fournisseurs SMS
    
    Administration des opérateurs SMS (Orange, Free, etc.)
    Accès réservé aux super admins
    """
    
    queryset = SMSProvider.objects.all()
    serializer_class = SMSProviderSerializer
    permission_classes = [permissions.IsAdminUser]
    
    ordering = ['priority', 'name']


# ========================================
# VUES UTILITAIRES
# ========================================

@extend_schema(
    summary="Envoyer notification manuelle",
    description="Envoyer une notification à des utilisateurs spécifiques",
    request=SendNotificationSerializer,
    tags=["Actions"]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def send_notification(request):
    """
    Envoyer une notification manuelle
    POST /api/notifications/send/
    """
    serializer = SendNotificationSerializer(data=request.data)
    
    if serializer.is_valid():
        from .services import NotificationService  # Import local pour éviter circular import
        
        template_id = serializer.validated_data['template_id']
        recipient_ids = serializer.validated_data['recipient_ids']
        content_type_id = serializer.validated_data.get('content_type_id')
        object_id = serializer.validated_data.get('object_id')
        custom_variables = serializer.validated_data.get('custom_variables', {})
        priority = serializer.validated_data['priority']
        schedule_for = serializer.validated_data.get('schedule_for')
        
        try:
            # Utiliser le service de notification
            service = NotificationService()
            
            template = NotificationTemplate.objects.get(id=template_id)
            
            # Objet lié (optionnel)
            content_object = None
            if content_type_id and object_id:
                content_type = ContentType.objects.get(id=content_type_id)
                content_object = content_type.get_object_for_this_type(id=object_id)
            
            notifications_created = []
            
            for recipient_id in recipient_ids:
                from apps.accounts.models import User
                recipient = User.objects.get(id=recipient_id)
                
                notification = service.create_notification(
                    template=template,
                    recipient=recipient,
                    content_object=content_object,
                    custom_variables=custom_variables,
                    priority=priority,
                    schedule_for=schedule_for
                )
                
                notifications_created.append(notification.id)
            
            return Response({
                'success': True,
                'message': f'{len(notifications_created)} notification(s) créée(s)',
                'notification_ids': notifications_created
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Notifications en masse",
    description="Envoyer des notifications à plusieurs utilisateurs selon des critères",
    request=BulkNotificationSerializer,
    tags=["Actions"]
)
@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])  # Réservé aux admins
def bulk_notification(request):
    """
    Envoyer des notifications en masse
    POST /api/notifications/bulk/
    """
    serializer = BulkNotificationSerializer(data=request.data)
    
    if serializer.is_valid():
        from apps.accounts.models import User
        from .services import NotificationService
        
        template_id = serializer.validated_data['template_id']
        user_type = serializer.validated_data['user_type']
        organization_ids = serializer.validated_data.get('organization_ids')
        service_ids = serializer.validated_data.get('service_ids')
        has_active_ticket = serializer.validated_data.get('has_active_ticket')
        has_upcoming_appointment = serializer.validated_data.get('has_upcoming_appointment')
        custom_variables = serializer.validated_data.get('custom_variables', {})
        priority = serializer.validated_data['priority']
        schedule_for = serializer.validated_data.get('schedule_for')
        dry_run = serializer.validated_data.get('dry_run', False)
        
        # Construire la requête pour sélectionner les destinataires
        queryset = User.objects.all()
        
        # Filtrer par type d'utilisateur
        if user_type == 'customer':
            queryset = queryset.filter(user_type='customer')
        elif user_type == 'staff':
            queryset = queryset.filter(user_type__in=['staff', 'admin'])
        elif user_type == 'admin':
            queryset = queryset.filter(user_type__in=['admin', 'super_admin'])
        
        # Filtrer par organisations
        if organization_ids:
            queryset = queryset.filter(
                Q(customer_profile__organization_id__in=organization_ids) |
                Q(staff_profile__organization_id__in=organization_ids)
            )
        
        # Filtrer par services
        if service_ids:
            queryset = queryset.filter(
                Q(tickets__service_id__in=service_ids) |
                Q(appointments__service_id__in=service_ids)
            ).distinct()
        
        # Filtrer par ticket actif
        if has_active_ticket:
            queryset = queryset.filter(
                tickets__status__in=['waiting', 'called', 'in_progress']
            ).distinct()
        
        # Filtrer par RDV à venir
        if has_upcoming_appointment:
            queryset = queryset.filter(
                appointments__scheduled_date__gte=timezone.now().date(),
                appointments__status__in=['pending', 'confirmed']
            ).distinct()
        
        recipients = list(queryset)
        
        # Si c'est un test, retourner seulement le nombre
        if dry_run:
            return Response({
                'success': True,
                'recipients_count': len(recipients),
                'message': f'{len(recipients)} destinataires sélectionnés'
            })
        
        # Envoyer les notifications
        try:
            service = NotificationService()
            template = NotificationTemplate.objects.get(id=template_id)
            
            notifications_created = []
            
            for recipient in recipients:
                notification = service.create_notification(
                    template=template,
                    recipient=recipient,
                    custom_variables=custom_variables,
                    priority=priority,
                    schedule_for=schedule_for
                )
                notifications_created.append(notification.id)
            
            return Response({
                'success': True,
                'message': f'{len(notifications_created)} notification(s) créée(s)',
                'recipients_count': len(recipients),
                'notification_ids': notifications_created[:10]  # Premiers 10 IDs seulement
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Notifications non lues",
    description="Compter les notifications non lues de l'utilisateur",
    tags=["Utilitaires"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def unread_count(request):
    """
    Nombre de notifications non lues
    GET /api/notifications/unread-count/
    """
    count = Notification.objects.filter(
        recipient=request.user,
        status__in=['sent', 'delivered'],
        read_at__isnull=True
    ).count()
    
    return Response({
        'unread_count': count
    })


@extend_schema(
    summary="Marquer toutes comme lues",
    description="Marquer toutes les notifications comme lues",
    tags=["Actions"]
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_as_read(request):
    """
    Marquer toutes les notifications comme lues
    POST /api/notifications/mark-all-read/
    """
    updated = Notification.objects.filter(
        recipient=request.user,
        status__in=['sent', 'delivered'],
        read_at__isnull=True
    ).update(
        status='read',
        read_at=timezone.now()
    )
    
    return Response({
        'success': True,
        'message': f'{updated} notification(s) marquée(s) comme lues'
    })