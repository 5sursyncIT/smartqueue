# apps/appointments/views.py
"""
Vues pour les rendez-vous SmartQueue
APIs REST pour la gestion des RDV sénégalais
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from django.utils import timezone
from django.db.models import Count, Q, Avg
from datetime import timedelta, datetime
from .models import AppointmentSlot, Appointment, AppointmentHistory
from .serializers import (
    AppointmentSlotListSerializer, AvailableSlotsSerializer,
    AppointmentCreateSerializer, AppointmentListSerializer, AppointmentDetailSerializer,
    AppointmentUpdateSerializer, AppointmentActionSerializer, RescheduleAppointmentSerializer,
    AppointmentStatsSerializer, AppointmentHistorySerializer
)


@extend_schema_view(
    list=extend_schema(
        summary="Liste des créneaux horaires",
        description="Récupérer tous les créneaux disponibles par organisation/service",
        tags=["Créneaux"]
    ),
    retrieve=extend_schema(
        summary="Détails d'un créneau",
        description="Récupérer les informations d'un créneau spécifique",
        tags=["Créneaux"]
    )
)
class AppointmentSlotViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les créneaux horaires de RDV
    
    GET /api/appointment-slots/ - Liste des créneaux
    GET /api/appointment-slots/1/ - Détails d'un créneau
    GET /api/appointment-slots/available/ - Créneaux disponibles pour une date
    """
    
    queryset = AppointmentSlot.objects.filter(is_active=True).select_related(
        'organization', 'service'
    )
    serializer_class = AppointmentSlotListSerializer
    permission_classes = [permissions.AllowAny]  # Public pour voir les disponibilités
    
    # Filtrage et recherche
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['organization', 'service', 'day_of_week']
    search_fields = ['organization__name', 'service__name']
    ordering_fields = ['day_of_week', 'start_time']
    ordering = ['day_of_week', 'start_time']
    
    @extend_schema(
        summary="Créneaux disponibles pour une date",
        description="Voir les créneaux libres pour une date donnée",
        request=AvailableSlotsSerializer,
        tags=["Créneaux"]
    )
    @action(detail=False, methods=['get'])
    def available(self, request):
        """
        Créneaux disponibles pour une date donnée
        GET /api/appointment-slots/available/?date=2025-08-20&service_id=1
        """
        serializer = AvailableSlotsSerializer(data=request.query_params)
        
        if serializer.is_valid():
            target_date = serializer.validated_data['date']
            service_id = serializer.validated_data.get('service_id')
            organization_id = serializer.validated_data.get('organization_id')
            
            # Filtrer les créneaux selon le jour de la semaine
            queryset = self.get_queryset().filter(
                day_of_week=target_date.weekday()
            )
            
            if service_id:
                queryset = queryset.filter(service_id=service_id)
            
            if organization_id:
                queryset = queryset.filter(organization_id=organization_id)
            
            available_slots = []
            
            for slot in queryset:
                # Obtenir les créneaux disponibles pour cette date
                slots_for_date = slot.get_available_slots_for_date(target_date)
                
                if slots_for_date:
                    available_slots.append({
                        'slot_id': slot.id,
                        'organization': {
                            'id': slot.organization.id,
                            'name': slot.organization.trade_name
                        },
                        'service': {
                            'id': slot.service.id,
                            'name': slot.service.name,
                            'code': slot.service.code
                        },
                        'available_times': slots_for_date,
                        'duration_minutes': slot.slot_duration
                    })
            
            return Response({
                'date': target_date,
                'weekday': target_date.weekday(),
                'available_slots': available_slots,
                'total_slots': len(available_slots)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(
        summary="Mes rendez-vous",
        description="Liste des RDV de l'utilisateur connecté",
        tags=["Rendez-vous"]
    ),
    create=extend_schema(
        summary="Prendre un rendez-vous",
        description="Créer un nouveau RDV",
        tags=["Rendez-vous"]
    ),
    retrieve=extend_schema(
        summary="Détails d'un RDV",
        description="Voir les détails complets d'un rendez-vous",
        tags=["Rendez-vous"]
    ),
    update=extend_schema(
        summary="Modifier un RDV",
        description="Modifier les notes ou priorité d'un RDV",
        tags=["Rendez-vous"]
    )
)
class AppointmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet principal pour les rendez-vous
    
    - GET /api/appointments/ (mes RDV)
    - POST /api/appointments/ (prendre RDV)
    - GET /api/appointments/1/ (détails)
    - PUT/PATCH /api/appointments/1/ (modifier)
    - DELETE /api/appointments/1/ (annuler = soft delete)
    
    Actions spéciales :
    - POST /api/appointments/1/confirm/
    - POST /api/appointments/1/cancel/
    - POST /api/appointments/1/reschedule/
    - POST /api/appointments/1/check_in/
    """
    
    queryset = Appointment.objects.select_related(
        'customer', 'organization', 'service', 'appointment_slot', 'assigned_staff'
    ).prefetch_related('history').all()
    
    permission_classes = [permissions.IsAuthenticated]
    
    # Filtrage et recherche
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'organization', 'service', 'scheduled_date']
    search_fields = ['appointment_number', 'customer_notes', 'service__name']
    ordering_fields = ['scheduled_date', 'scheduled_time', 'created_at']
    ordering = ['-scheduled_date', '-scheduled_time']
    
    def get_serializer_class(self):
        """Retourne le bon serializer selon l'action"""
        if self.action == 'list':
            return AppointmentListSerializer
        elif self.action == 'retrieve':
            return AppointmentDetailSerializer
        elif self.action == 'create':
            return AppointmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AppointmentUpdateSerializer
        elif self.action in ['confirm', 'cancel', 'check_in']:
            return AppointmentActionSerializer
        elif self.action == 'reschedule':
            return RescheduleAppointmentSerializer
        elif self.action == 'stats':
            return AppointmentStatsSerializer
        
        return AppointmentDetailSerializer
    
    def get_queryset(self):
        """Filtrer selon le type d'utilisateur"""
        user = self.request.user
        
        if user.is_super_admin:
            # Super admin voit tous les RDV
            return self.queryset
        elif user.is_organization_admin or user.is_staff_member:
            # Staff voit les RDV de son organisation
            if hasattr(user, 'staff_profile'):
                return self.queryset.filter(
                    organization=user.staff_profile.organization
                )
        elif user.is_customer:
            # Client voit seulement ses RDV
            return self.queryset.filter(customer=user)
        
        return Appointment.objects.none()
    
    def perform_create(self, serializer):
        """Personnaliser la création"""
        appointment = serializer.save()
        
        # Créer l'historique
        AppointmentHistory.objects.create(
            appointment=appointment,
            action='created',
            new_value={
                'scheduled_date': str(appointment.scheduled_date),
                'scheduled_time': str(appointment.scheduled_time),
                'service': appointment.service.name
            },
            performed_by=self.request.user,
            reason=f"RDV créé par {self.request.user.get_full_name()}"
        )
    
    def perform_destroy(self, instance):
        """Soft delete : annuler au lieu de supprimer"""
        if instance.can_be_cancelled:
            instance.cancel(reason="Annulé par le client")
            
            AppointmentHistory.objects.create(
                appointment=instance,
                action='cancelled',
                old_value={'status': 'confirmed'},
                new_value={'status': 'cancelled'},
                performed_by=self.request.user,
                reason="Annulé via suppression"
            )
        else:
            raise PermissionError("Ce rendez-vous ne peut plus être annulé.")
    
    @extend_schema(
        summary="Confirmer un RDV",
        description="Confirmer un RDV en attente (par le personnel)",
        request=AppointmentActionSerializer,
        tags=["Actions RDV"]
    )
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirmer un rendez-vous
        POST /api/appointments/1/confirm/
        """
        appointment = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            if appointment.confirm():
                # Historique
                AppointmentHistory.objects.create(
                    appointment=appointment,
                    action='confirmed',
                    old_value={'status': 'pending'},
                    new_value={'status': 'confirmed'},
                    performed_by=request.user,
                    reason=serializer.validated_data.get('reason', '')
                )
                
                return Response({
                    'success': True,
                    'message': f'RDV {appointment.appointment_number} confirmé!',
                    'status': appointment.get_status_display()
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Ce RDV ne peut pas être confirmé.'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Annuler un RDV",
        description="Annuler un rendez-vous",
        request=AppointmentActionSerializer,
        tags=["Actions RDV"]
    )
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Annuler un rendez-vous
        POST /api/appointments/1/cancel/
        """
        appointment = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            reason = serializer.validated_data.get('reason', '')
            
            if appointment.cancel(reason):
                # Historique
                AppointmentHistory.objects.create(
                    appointment=appointment,
                    action='cancelled',
                    old_value={'status': appointment.status},
                    new_value={'status': 'cancelled'},
                    performed_by=request.user,
                    reason=reason
                )
                
                return Response({
                    'success': True,
                    'message': f'RDV {appointment.appointment_number} annulé.',
                    'reason': reason
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Ce RDV ne peut plus être annulé (moins de 2h avant).'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Reporter un RDV",
        description="Reporter un rendez-vous à une autre date/heure",
        request=RescheduleAppointmentSerializer,
        tags=["Actions RDV"]
    )
    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        """
        Reporter un rendez-vous
        POST /api/appointments/1/reschedule/
        """
        appointment = self.get_object()
        
        if not appointment.can_be_rescheduled:
            return Response({
                'success': False,
                'error': 'Ce RDV ne peut plus être reporté.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Sauvegarder l'ancien RDV
            old_values = {
                'appointment_slot_id': appointment.appointment_slot.id,
                'scheduled_date': str(appointment.scheduled_date),
                'scheduled_time': str(appointment.scheduled_time)
            }
            
            # Mettre à jour
            appointment.appointment_slot = serializer.validated_data['new_appointment_slot']
            appointment.scheduled_date = serializer.validated_data['new_scheduled_date']
            appointment.scheduled_time = serializer.validated_data['new_scheduled_time']
            appointment.status = 'rescheduled'
            appointment.save()
            
            # Historique
            AppointmentHistory.objects.create(
                appointment=appointment,
                action='rescheduled',
                old_value=old_values,
                new_value={
                    'appointment_slot_id': appointment.appointment_slot.id,
                    'scheduled_date': str(appointment.scheduled_date),
                    'scheduled_time': str(appointment.scheduled_time)
                },
                performed_by=request.user,
                reason=serializer.validated_data.get('reason', '')
            )
            
            return Response({
                'success': True,
                'message': f'RDV {appointment.appointment_number} reporté!',
                'new_date': appointment.scheduled_date,
                'new_time': appointment.scheduled_time
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Check-in client",
        description="Marquer le client comme arrivé",
        request=AppointmentActionSerializer,
        tags=["Actions RDV"]
    )
    @action(detail=True, methods=['post'])
    def check_in(self, request, pk=None):
        """
        Check-in du client (il est arrivé)
        POST /api/appointments/1/check_in/
        """
        appointment = self.get_object()
        
        if appointment.check_in():
            # Historique
            AppointmentHistory.objects.create(
                appointment=appointment,
                action='checked_in',
                old_value={'status': 'confirmed'},
                new_value={'status': 'checked_in'},
                performed_by=request.user
            )
            
            return Response({
                'success': True,
                'message': f'Client {appointment.customer.get_full_name()} arrivé!',
                'checked_in_at': appointment.checked_in_at
            })
        else:
            return Response({
                'success': False,
                'error': 'Impossible de faire le check-in pour ce RDV.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Commencer le service",
        description="Marquer le début du service",
        tags=["Actions RDV"]
    )
    @action(detail=True, methods=['post'])
    def start_service(self, request, pk=None):
        """
        Commencer le service
        POST /api/appointments/1/start_service/
        """
        appointment = self.get_object()
        
        if appointment.start_service():
            return Response({
                'success': True,
                'message': f'Service commencé pour {appointment.customer.get_full_name()}',
                'started_at': appointment.started_at
            })
        else:
            return Response({
                'success': False,
                'error': 'Impossible de commencer le service.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Terminer le service",
        description="Marquer le service comme terminé",
        tags=["Actions RDV"]
    )
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Terminer le service
        POST /api/appointments/1/complete/
        """
        appointment = self.get_object()
        
        if appointment.complete():
            return Response({
                'success': True,
                'message': f'Service terminé pour {appointment.customer.get_full_name()}',
                'completed_at': appointment.completed_at
            })
        else:
            return Response({
                'success': False,
                'error': 'Impossible de terminer le service.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Historique d'un RDV",
        description="Voir l'historique des modifications d'un RDV",
        tags=["Historique"]
    )
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        Historique des modifications
        GET /api/appointments/1/history/
        """
        appointment = self.get_object()
        history = appointment.history.all()
        
        serializer = AppointmentHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Statistiques des RDV",
        description="Stats globales des rendez-vous",
        tags=["Statistiques"]
    )
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Statistiques des rendez-vous
        GET /api/appointments/stats/
        """
        queryset = self.get_queryset()
        
        # Stats générales
        total = queryset.count()
        pending = queryset.filter(status='pending').count()
        confirmed = queryset.filter(status='confirmed').count()
        completed = queryset.filter(status='completed').count()
        cancelled = queryset.filter(status='cancelled').count()
        
        # Aujourd'hui et à venir
        today = timezone.now().date()
        today_count = queryset.filter(scheduled_date=today).count()
        upcoming = queryset.filter(
            scheduled_date__gt=today,
            status__in=['pending', 'confirmed']
        ).count()
        
        # Taux de complétion
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        # Délai moyen de prise de RDV (jours entre création et RDV)
        completed_appointments = queryset.filter(status='completed')
        avg_lead_time = 0
        if completed_appointments.exists():
            lead_times = []
            for apt in completed_appointments:
                delta = apt.scheduled_date - apt.created_at.date()
                lead_times.append(delta.days)
            avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0
        
        # Stats hebdomadaires
        weekly_stats = []
        for i in range(7):
            date = today - timedelta(days=i)
            day_appointments = queryset.filter(scheduled_date=date)
            weekly_stats.append({
                'date': date,
                'day_name': date.strftime('%A'),
                'total': day_appointments.count(),
                'completed': day_appointments.filter(status='completed').count(),
                'cancelled': day_appointments.filter(status='cancelled').count()
            })
        
        return Response({
            'total_appointments': total,
            'pending_appointments': pending,
            'confirmed_appointments': confirmed,
            'completed_appointments': completed,
            'cancelled_appointments': cancelled,
            'today_appointments': today_count,
            'upcoming_appointments': upcoming,
            'average_lead_time': round(avg_lead_time, 1),
            'completion_rate': round(completion_rate, 1),
            'weekly_stats': list(reversed(weekly_stats))
        })


# ========================================
# VUES UTILITAIRES
# ========================================

@extend_schema(
    summary="RDV du jour",
    description="Liste des RDV d'aujourd'hui pour le personnel",
    tags=["Utilitaires"]
)
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def todays_appointments(request):
    """
    RDV du jour pour le personnel
    GET /api/appointments/today/
    """
    user = request.user
    today = timezone.now().date()
    
    # Filtrer selon le type d'utilisateur
    if user.is_customer:
        appointments = Appointment.objects.filter(
            customer=user,
            scheduled_date=today
        ).select_related('service', 'organization')
    elif user.is_staff_member or user.is_organization_admin:
        if hasattr(user, 'staff_profile'):
            appointments = Appointment.objects.filter(
                organization=user.staff_profile.organization,
                scheduled_date=today
            ).select_related('customer', 'service')
        else:
            appointments = Appointment.objects.none()
    else:
        # Super admin ou autre
        appointments = Appointment.objects.filter(
            scheduled_date=today
        ).select_related('customer', 'service', 'organization')
    
    # Grouper par statut
    by_status = {}
    for appointment in appointments:
        status_key = appointment.status
        if status_key not in by_status:
            by_status[status_key] = []
        
        by_status[status_key].append({
            'id': appointment.id,
            'appointment_number': appointment.appointment_number,
            'customer_name': appointment.customer.get_full_name(),
            'service_name': appointment.service.name,
            'scheduled_time': appointment.scheduled_time,
            'status': appointment.get_status_display(),
            'priority': appointment.get_priority_display()
        })
    
    return Response({
        'date': today,
        'total_appointments': appointments.count(),
        'appointments_by_status': by_status
    })