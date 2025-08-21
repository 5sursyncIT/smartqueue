# apps/appointments/serializers.py
"""
Serializers pour les rendez-vous SmartQueue
Gestion des RDV pour banques, hôpitaux, administrations sénégalaises
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta, date, time
from .models import AppointmentSlot, Appointment, AppointmentHistory


class AppointmentSlotListSerializer(serializers.ModelSerializer):
    """
    Serializer pour lister les créneaux horaires disponibles
    
    Usage : GET /api/appointment-slots/
    """
    
    organization_name = serializers.CharField(
        source='organization.name', 
        read_only=True
    )
    
    organization_trade_name = serializers.CharField(
        source='organization.trade_name', 
        read_only=True
    )
    
    service_name = serializers.CharField(
        source='service.name', 
        read_only=True
    )
    
    service_code = serializers.CharField(
        source='service.code', 
        read_only=True
    )
    
    day_name = serializers.SerializerMethodField()
    
    class Meta:
        model = AppointmentSlot
        fields = [
            'id', 'uuid', 
            'organization_name', 'organization_trade_name',
            'service_name', 'service_code',
            'day_of_week', 'day_name',
            'start_time', 'end_time', 'slot_duration',
            'max_appointments', 'is_active'
        ]
    
    def get_day_name(self, obj):
        """Retourne le nom du jour en français"""
        days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        return days[obj.day_of_week]


class AvailableSlotsSerializer(serializers.Serializer):
    """
    Serializer pour les créneaux disponibles d'une date donnée
    
    Usage : GET /api/appointment-slots/available/?date=2025-08-20&service_id=1
    """
    
    date = serializers.DateField(
        help_text="Date au format YYYY-MM-DD (ex: 2025-08-20)"
    )
    
    service_id = serializers.IntegerField(
        required=False,
        help_text="ID du service (optionnel pour filtrer)"
    )
    
    organization_id = serializers.IntegerField(
        required=False,
        help_text="ID de l'organisation (optionnel pour filtrer)"
    )
    
    def validate_date(self, value):
        """Valider que la date est dans le futur"""
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "La date doit être aujourd'hui ou dans le futur."
            )
        
        # Maximum 3 mois à l'avance
        max_date = timezone.now().date() + timedelta(days=90)
        if value > max_date:
            raise serializers.ValidationError(
                "Vous ne pouvez prendre RDV que 3 mois à l'avance maximum."
            )
        
        return value


class AppointmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour créer un nouveau rendez-vous
    
    Usage : POST /api/appointments/
    """
    
    scheduled_date = serializers.DateField(
        help_text="Date du RDV (YYYY-MM-DD)"
    )
    
    scheduled_time = serializers.TimeField(
        help_text="Heure du RDV (HH:MM)"
    )
    
    class Meta:
        model = Appointment
        fields = [
            'appointment_slot', 'scheduled_date', 'scheduled_time',
            'priority', 'customer_notes', 'customer_phone'
        ]
    
    def validate_scheduled_date(self, value):
        """Valider la date du RDV"""
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Vous ne pouvez pas prendre RDV dans le passé."
            )
        
        # Maximum 3 mois à l'avance
        max_date = timezone.now().date() + timedelta(days=90)
        if value > max_date:
            raise serializers.ValidationError(
                "Maximum 3 mois à l'avance."
            )
        
        return value
    
    def validate(self, attrs):
        """Validation globale"""
        appointment_slot = attrs.get('appointment_slot')
        scheduled_date = attrs.get('scheduled_date')
        scheduled_time = attrs.get('scheduled_time')
        
        if not (appointment_slot and scheduled_date and scheduled_time):
            raise serializers.ValidationError(
                "Créneau, date et heure sont obligatoires."
            )
        
        # Vérifier que le jour correspond au créneau
        if scheduled_date.weekday() != appointment_slot.day_of_week:
            raise serializers.ValidationError({
                'scheduled_date': 'Cette date ne correspond pas au jour du créneau.'
            })
        
        # Vérifier que l'heure est dans la plage du créneau
        if not (appointment_slot.start_time <= scheduled_time <= appointment_slot.end_time):
            raise serializers.ValidationError({
                'scheduled_time': f'L\'heure doit être entre {appointment_slot.start_time} et {appointment_slot.end_time}.'
            })
        
        # Vérifier la disponibilité
        existing_appointments = Appointment.objects.filter(
            appointment_slot=appointment_slot,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
            status__in=['pending', 'confirmed', 'checked_in']
        ).count()
        
        if existing_appointments >= appointment_slot.max_appointments:
            raise serializers.ValidationError({
                'scheduled_time': 'Ce créneau est complet.'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Créer le rendez-vous"""
        # Ajouter le client connecté
        validated_data['customer'] = self.context['request'].user
        
        # Ajouter l'IP de création
        validated_data['created_ip'] = self.context['request'].META.get('REMOTE_ADDR')
        
        return super().create(validated_data)


class AppointmentListSerializer(serializers.ModelSerializer):
    """
    Serializer pour lister les rendez-vous
    
    Usage : GET /api/appointments/
    """
    
    customer_name = serializers.CharField(
        source='customer.get_full_name', 
        read_only=True
    )
    
    organization_name = serializers.CharField(
        source='organization.trade_name', 
        read_only=True
    )
    
    service_name = serializers.CharField(
        source='service.name', 
        read_only=True
    )
    
    status_display = serializers.CharField(
        source='get_status_display', 
        read_only=True
    )
    
    priority_display = serializers.CharField(
        source='get_priority_display', 
        read_only=True
    )
    
    # Propriétés calculées
    is_upcoming = serializers.BooleanField(read_only=True)
    is_today = serializers.BooleanField(read_only=True)
    can_be_cancelled = serializers.BooleanField(read_only=True)
    can_be_rescheduled = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'uuid', 'appointment_number',
            'customer_name', 'organization_name', 'service_name',
            'scheduled_date', 'scheduled_time', 
            'status', 'status_display', 'priority', 'priority_display',
            'customer_notes', 'customer_phone',
            'is_upcoming', 'is_today', 'can_be_cancelled', 'can_be_rescheduled',
            'created_at', 'confirmed_at'
        ]


class AppointmentDetailSerializer(AppointmentListSerializer):
    """
    Serializer pour les détails d'un rendez-vous
    
    Usage : GET /api/appointments/1/
    """
    
    # Informations du créneau
    appointment_slot_info = serializers.SerializerMethodField()
    
    # Informations staff
    assigned_staff_name = serializers.CharField(
        source='assigned_staff.get_full_name',
        read_only=True
    )
    
    # Timeline complète
    timeline = serializers.SerializerMethodField()
    
    class Meta(AppointmentListSerializer.Meta):
        fields = AppointmentListSerializer.Meta.fields + [
            'appointment_slot_info', 'assigned_staff_name', 'staff_notes',
            'checked_in_at', 'started_at', 'completed_at',
            'reminder_sent', 'reminder_sent_at', 'confirmation_sent',
            'timeline', 'updated_at'
        ]
    
    def get_appointment_slot_info(self, obj):
        """Informations du créneau"""
        if obj.appointment_slot:
            slot = obj.appointment_slot
            days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
            return {
                'id': slot.id,
                'day_name': days[slot.day_of_week],
                'start_time': slot.start_time,
                'end_time': slot.end_time,
                'duration_minutes': slot.slot_duration
            }
        return None
    
    def get_timeline(self, obj):
        """Timeline des événements du RDV"""
        timeline = [
            {
                'event': 'created',
                'label': 'RDV créé',
                'timestamp': obj.created_at,
                'completed': True
            }
        ]
        
        if obj.confirmed_at:
            timeline.append({
                'event': 'confirmed',
                'label': 'RDV confirmé',
                'timestamp': obj.confirmed_at,
                'completed': True
            })
        
        if obj.checked_in_at:
            timeline.append({
                'event': 'checked_in',
                'label': 'Client arrivé',
                'timestamp': obj.checked_in_at,
                'completed': True
            })
        
        if obj.started_at:
            timeline.append({
                'event': 'started',
                'label': 'Service commencé',
                'timestamp': obj.started_at,
                'completed': True
            })
        
        if obj.completed_at:
            timeline.append({
                'event': 'completed',
                'label': 'Service terminé',
                'timestamp': obj.completed_at,
                'completed': True
            })
        
        return timeline


class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour modifier un rendez-vous
    
    Usage : PUT/PATCH /api/appointments/1/
    """
    
    class Meta:
        model = Appointment
        fields = [
            'customer_notes', 'customer_phone', 'priority'
        ]
        
        # Champs non modifiables après création
        read_only_fields = [
            'appointment_slot', 'scheduled_date', 'scheduled_time',
            'customer', 'organization', 'service', 'status'
        ]


class AppointmentActionSerializer(serializers.Serializer):
    """
    Serializer pour les actions sur les rendez-vous
    
    Usage : POST /api/appointments/1/confirm/, cancel/, etc.
    """
    
    reason = serializers.CharField(
        required=False,
        max_length=500,
        help_text="Raison de l'action (optionnel)"
    )


class RescheduleAppointmentSerializer(serializers.Serializer):
    """
    Serializer pour reporter un rendez-vous
    
    Usage : POST /api/appointments/1/reschedule/
    """
    
    new_appointment_slot = serializers.PrimaryKeyRelatedField(
        queryset=AppointmentSlot.objects.filter(is_active=True),
        help_text="Nouveau créneau horaire"
    )
    
    new_scheduled_date = serializers.DateField(
        help_text="Nouvelle date (YYYY-MM-DD)"
    )
    
    new_scheduled_time = serializers.TimeField(
        help_text="Nouvelle heure (HH:MM)"
    )
    
    reason = serializers.CharField(
        required=False,
        max_length=500,
        help_text="Raison du report"
    )
    
    def validate_new_scheduled_date(self, value):
        """Valider la nouvelle date"""
        if value < timezone.now().date():
            raise serializers.ValidationError(
                "Impossible de reporter dans le passé."
            )
        
        max_date = timezone.now().date() + timedelta(days=90)
        if value > max_date:
            raise serializers.ValidationError(
                "Maximum 3 mois à l'avance."
            )
        
        return value
    
    def validate(self, attrs):
        """Validation globale du report"""
        slot = attrs.get('new_appointment_slot')
        date = attrs.get('new_scheduled_date')
        time = attrs.get('new_scheduled_time')
        
        # Vérifier cohérence jour/créneau
        if date.weekday() != slot.day_of_week:
            raise serializers.ValidationError({
                'new_scheduled_date': 'Cette date ne correspond pas au jour du créneau.'
            })
        
        # Vérifier heure dans plage
        if not (slot.start_time <= time <= slot.end_time):
            raise serializers.ValidationError({
                'new_scheduled_time': f'L\'heure doit être entre {slot.start_time} et {slot.end_time}.'
            })
        
        # Vérifier disponibilité
        existing = Appointment.objects.filter(
            appointment_slot=slot,
            scheduled_date=date,
            scheduled_time=time,
            status__in=['pending', 'confirmed', 'checked_in']
        ).count()
        
        if existing >= slot.max_appointments:
            raise serializers.ValidationError({
                'new_scheduled_time': 'Ce nouveau créneau est complet.'
            })
        
        return attrs


class AppointmentStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques des rendez-vous
    
    Usage : GET /api/appointments/stats/
    """
    
    total_appointments = serializers.IntegerField()
    pending_appointments = serializers.IntegerField()
    confirmed_appointments = serializers.IntegerField()
    completed_appointments = serializers.IntegerField()
    cancelled_appointments = serializers.IntegerField()
    
    today_appointments = serializers.IntegerField()
    upcoming_appointments = serializers.IntegerField()
    
    average_lead_time = serializers.FloatField()  # Délai moyen de prise de RDV
    completion_rate = serializers.FloatField()    # Taux de RDV honorés
    
    weekly_stats = serializers.ListField()


class AppointmentHistorySerializer(serializers.ModelSerializer):
    """
    Serializer pour l'historique des rendez-vous
    
    Usage : GET /api/appointments/1/history/
    """
    
    performed_by_name = serializers.CharField(
        source='performed_by.get_full_name',
        read_only=True
    )
    
    class Meta:
        model = AppointmentHistory
        fields = [
            'id', 'action', 'old_value', 'new_value',
            'performed_by_name', 'reason', 'created_at'
        ]