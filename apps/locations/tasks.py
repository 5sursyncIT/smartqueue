# apps/locations/tasks.py
"""
Tâches automatisées Celery pour géolocalisation intelligente
Calculs périodiques, notifications, réorganisation des files
"""

from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from datetime import timedelta
import logging

from .models import (
    UserLocation, TravelTimeEstimate, TrafficCondition,
    WeatherCondition, Region, Commune
)
from .services import (
    SmartTravelTimeCalculator, QueueReorganizationService,
    LocationNotificationService, TrafficPredictionService
)

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True)
def update_user_locations(self):
    """
    Mettre à jour les localisations utilisateurs
    Tâche exécutée toutes les 5 minutes
    """
    try:
        updated_count = 0
        
        # Utilisateurs avec partage localisation activé
        users_with_location = User.objects.filter(
            current_location__location_sharing_enabled=True,
            current_location__last_updated__gte=timezone.now() - timedelta(hours=1)
        )
        
        for user in users_with_location:
            try:
                location = user.current_location
                
                # Mettre à jour commune la plus proche
                old_commune = location.nearest_commune
                location.update_nearest_commune()
                
                # Logger changement de commune
                if old_commune != location.nearest_commune:
                    logger.info(
                        f"User {user.email} moved: {old_commune} → {location.nearest_commune}"
                    )
                
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Erreur MAJ location user {user.email}: {e}")
        
        logger.info(f"Locations mises à jour: {updated_count}")
        return f"Updated {updated_count} user locations"
        
    except Exception as e:
        logger.error(f"Erreur tâche update_user_locations: {e}")
        self.retry(countdown=300, max_retries=3)


@shared_task(bind=True)
def calculate_travel_estimates_for_active_tickets(self):
    """
    Calculer temps de trajet pour tickets actifs
    Tâche exécutée toutes les 10 minutes
    """
    try:
        from apps.tickets.models import Ticket
        from apps.queues.models import Queue
        
        estimates_created = 0
        
        # Tickets actifs avec utilisateurs géolocalisés
        active_tickets = Ticket.objects.filter(
            status__in=['waiting', 'called'],
            customer__current_location__location_sharing_enabled=True,
            customer__current_location__last_updated__gte=timezone.now() - timedelta(minutes=30)
        ).select_related('customer', 'queue', 'service')
        
        for ticket in active_tickets:
            try:
                user = ticket.customer
                location = user.current_location
                queue = ticket.queue
                organization = queue.organization
                
                # Vérifier si estimation récente existe
                recent_estimate = TravelTimeEstimate.objects.filter(
                    user=user,
                    organization=organization,
                    created_at__gte=timezone.now() - timedelta(minutes=15)
                ).first()
                
                if recent_estimate:
                    continue
                
                # Calculer nouvelle estimation
                travel_data = SmartTravelTimeCalculator.calculate_travel_time(
                    user=user,
                    origin_lat=float(location.latitude),
                    origin_lng=float(location.longitude),
                    dest_lat=float(organization.latitude),
                    dest_lng=float(organization.longitude),
                    organization=organization,
                    departure_time=timezone.now()
                )
                
                # Créer estimation en base
                TravelTimeEstimate.objects.create(
                    user=user,
                    origin_latitude=location.latitude,
                    origin_longitude=location.longitude,
                    origin_commune=travel_data['origin_commune'],
                    destination_latitude=organization.latitude,
                    destination_longitude=organization.longitude,
                    destination_commune=travel_data['destination_commune'],
                    organization=organization,
                    estimated_travel_minutes=travel_data['estimated_travel_minutes'],
                    distance_km=travel_data['distance_km'],
                    transport_mode=travel_data['transport_mode'],
                    traffic_factor_applied=travel_data['traffic_factor'],
                    weather_factor_applied=travel_data['weather_factor'],
                    time_of_day_factor=travel_data.get('time_of_day_factor', 1.0),
                    safety_margin_minutes=travel_data['safety_margin_minutes'],
                    recommended_departure_time=travel_data['departure_time'],
                    estimated_arrival_time=travel_data['estimated_arrival_time'],
                    confidence_score=travel_data['confidence_score'],
                    calculation_source=travel_data['calculation_source']
                )
                
                estimates_created += 1
                
                logger.info(
                    f"Estimation créée: {user.email} → {organization.name} "
                    f"({travel_data['estimated_travel_minutes']}min)"
                )
                
            except Exception as e:
                logger.error(f"Erreur calcul estimation ticket {ticket.id}: {e}")
        
        logger.info(f"Estimations créées: {estimates_created}")
        return f"Created {estimates_created} travel estimates"
        
    except Exception as e:
        logger.error(f"Erreur tâche calculate_travel_estimates: {e}")
        self.retry(countdown=600, max_retries=3)


@shared_task(bind=True)
def check_queue_reorganization(self):
    """
    Vérifier et déclencher réorganisation des files d'attente
    Tâche exécutée toutes les 5 minutes
    """
    try:
        from apps.tickets.models import Ticket
        from apps.queues.models import Queue
        
        reorganizations_done = 0
        
        # Files actives
        active_queues = Queue.objects.filter(
            status='open',
            tickets__status__in=['waiting', 'called']
        ).distinct()
        
        for queue in active_queues:
            try:
                # Tickets dans cette file avec géolocalisation
                tickets_with_location = queue.tickets.filter(
                    status__in=['waiting', 'called'],
                    customer__current_location__location_sharing_enabled=True
                ).order_by('position')
                
                reorganization_needed = False
                tickets_to_move = []
                
                for ticket in tickets_with_location:
                    # Vérifier si réorganisation nécessaire
                    should_reorganize = QueueReorganizationService.should_reorganize_queue(
                        ticket, queue
                    )
                    
                    if should_reorganize:
                        optimal_position = QueueReorganizationService.calculate_optimal_position(
                            ticket, queue
                        )
                        
                        if optimal_position != ticket.position:
                            tickets_to_move.append({
                                'ticket': ticket,
                                'new_position': optimal_position,
                                'old_position': ticket.position
                            })
                            reorganization_needed = True
                
                # Appliquer réorganisation
                if reorganization_needed and tickets_to_move:
                    _apply_queue_reorganization(queue, tickets_to_move)
                    reorganizations_done += 1
                    
                    logger.info(f"File réorganisée: {queue} ({len(tickets_to_move)} tickets)")
                
            except Exception as e:
                logger.error(f"Erreur réorganisation file {queue.id}: {e}")
        
        logger.info(f"Réorganisations effectuées: {reorganizations_done}")
        return f"Reorganized {reorganizations_done} queues"
        
    except Exception as e:
        logger.error(f"Erreur tâche check_queue_reorganization: {e}")
        self.retry(countdown=300, max_retries=3)


@shared_task(bind=True)
def send_departure_notifications(self):
    """
    Envoyer notifications "Temps de partir"
    Tâche exécutée toutes les minutes
    """
    try:
        from apps.appointments.models import Appointment
        from apps.notifications.tasks import send_sms_notification
        
        notifications_sent = 0
        
        # RDV dans les 2 prochaines heures avec géolocalisation
        upcoming_appointments = Appointment.objects.filter(
            date=timezone.now().date(),
            time__gte=timezone.now().time(),
            time__lte=(timezone.now() + timedelta(hours=2)).time(),
            status='confirmed',
            customer__current_location__location_sharing_enabled=True
        ).select_related('customer', 'service', 'organization')
        
        for appointment in upcoming_appointments:
            try:
                user = appointment.customer
                organization = appointment.service.organization
                appointment_datetime = timezone.make_aware(
                    timezone.datetime.combine(appointment.date, appointment.time)
                )
                
                # Vérifier s'il faut notifier
                should_notify = LocationNotificationService.should_send_departure_notification(
                    user, organization, appointment_datetime
                )
                
                if should_notify:
                    # Calculer temps de trajet actuel
                    location = user.current_location
                    travel_data = SmartTravelTimeCalculator.calculate_travel_time(
                        user=user,
                        origin_lat=float(location.latitude),
                        origin_lng=float(location.longitude),
                        dest_lat=float(organization.latitude),
                        dest_lng=float(organization.longitude),
                        organization=organization,
                        departure_time=timezone.now()
                    )
                    
                    travel_time = travel_data['estimated_travel_minutes']
                    
                    # Message selon langue utilisateur
                    if user.preferred_language == 'wo':
                        message = (
                            f"SmartQueue: Sa RDV ci {appointment.time.strftime('%H:%M')} "
                            f"ci {organization.name}. Dem fiit thi {travel_time} simili. "
                            f"Liggéey na ngeen dem!"
                        )
                    else:
                        message = (
                            f"SmartQueue: Votre RDV à {appointment.time.strftime('%H:%M')} "
                            f"chez {organization.name}. Temps trajet: {travel_time}min. "
                            f"Il est temps de partir!"
                        )
                    
                    # Envoyer SMS
                    send_sms_notification.delay(
                        user.phone_number,
                        message,
                        notification_type='departure_reminder'
                    )
                    
                    notifications_sent += 1
                    
                    logger.info(
                        f"Notification départ envoyée: {user.email} → {organization.name} "
                        f"(trajet {travel_time}min)"
                    )
                
            except Exception as e:
                logger.error(f"Erreur notification départ RDV {appointment.id}: {e}")
        
        logger.info(f"Notifications départ envoyées: {notifications_sent}")
        return f"Sent {notifications_sent} departure notifications"
        
    except Exception as e:
        logger.error(f"Erreur tâche send_departure_notifications: {e}")
        self.retry(countdown=60, max_retries=5)


@shared_task(bind=True)
def update_traffic_conditions(self):
    """
    Mettre à jour conditions de circulation via APIs
    Tâche exécutée toutes les 15 minutes
    """
    try:
        from .services import ExternalAPIService
        
        updates_count = 0
        
        # Routes principales à surveiller (communes populaires)
        major_routes = [
            # Dakar → autres communes importantes
            ('dakar', 'pikine'),
            ('dakar', 'guediawaye'), 
            ('dakar', 'thiaroye'),
            ('pikine', 'diamnadio'),
            ('dakar', 'rufisque'),
            ('dakar', 'keur-massar'),
        ]
        
        for origin_name, dest_name in major_routes:
            try:
                origin_commune = Commune.objects.filter(name__icontains=origin_name).first()
                dest_commune = Commune.objects.filter(name__icontains=dest_name).first()
                
                if not origin_commune or not dest_commune:
                    continue
                
                # Obtenir données trafic via API
                traffic_data = ExternalAPIService.get_google_maps_duration(
                    float(origin_commune.latitude),
                    float(origin_commune.longitude),
                    float(dest_commune.latitude), 
                    float(dest_commune.longitude),
                    departure_time=timezone.now()
                )
                
                if traffic_data:
                    # Calculer facteur de retard
                    base_time = traffic_data['duration_minutes']
                    traffic_time = traffic_data.get('traffic_duration_seconds', 0) // 60
                    
                    if traffic_time > 0:
                        delay_factor = traffic_time / base_time
                    else:
                        delay_factor = 1.0
                    
                    # Déterminer statut trafic
                    if delay_factor >= 2.0:
                        status = 'embouteille'
                    elif delay_factor >= 1.5:
                        status = 'dense'
                    elif delay_factor >= 1.2:
                        status = 'normal'
                    else:
                        status = 'fluide'
                    
                    # Mettre à jour ou créer condition trafic
                    traffic_condition, created = TrafficCondition.objects.update_or_create(
                        source_commune=origin_commune,
                        destination_commune=dest_commune,
                        defaults={
                            'status': status,
                            'travel_time_minutes': int(traffic_time or base_time),
                            'distance_km': traffic_data['distance_km'],
                            'delay_factor': delay_factor,
                            'data_source': 'google',
                            'reliability_score': 85
                        }
                    )
                    
                    updates_count += 1
                    
                    logger.info(
                        f"Trafic MAJ: {origin_commune} → {dest_commune} "
                        f"({status}, {delay_factor:.1f}x)"
                    )
                
            except Exception as e:
                logger.error(f"Erreur MAJ trafic {origin_name}->{dest_name}: {e}")
        
        logger.info(f"Conditions trafic mises à jour: {updates_count}")
        return f"Updated {updates_count} traffic conditions"
        
    except Exception as e:
        logger.error(f"Erreur tâche update_traffic_conditions: {e}")
        self.retry(countdown=900, max_retries=3)


@shared_task(bind=True) 
def cleanup_old_location_data(self):
    """
    Nettoyer anciennes données de géolocalisation
    Tâche exécutée quotidiennement
    """
    try:
        # Supprimer estimations > 24h
        old_estimates = TravelTimeEstimate.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=1)
        )
        estimates_deleted = old_estimates.count()
        old_estimates.delete()
        
        # Supprimer conditions trafic > 2h
        old_traffic = TrafficCondition.objects.filter(
            last_updated__lt=timezone.now() - timedelta(hours=2)
        )
        traffic_deleted = old_traffic.count()
        old_traffic.delete()
        
        # Désactiver partage localisation inactif > 24h
        inactive_locations = UserLocation.objects.filter(
            location_sharing_enabled=True,
            last_updated__lt=timezone.now() - timedelta(days=1)
        )
        locations_disabled = inactive_locations.count()
        inactive_locations.update(location_sharing_enabled=False)
        
        logger.info(
            f"Nettoyage: {estimates_deleted} estimations, "
            f"{traffic_deleted} conditions trafic, "
            f"{locations_disabled} localisations désactivées"
        )
        
        return f"Cleaned up old location data: {estimates_deleted + traffic_deleted + locations_disabled} records"
        
    except Exception as e:
        logger.error(f"Erreur tâche cleanup_old_location_data: {e}")
        self.retry(countdown=3600, max_retries=3)


def _apply_queue_reorganization(queue, tickets_to_move):
    """
    Helper pour appliquer réorganisation de file
    """
    try:
        from apps.tickets.models import Ticket
        from apps.core.models import ActivityLog
        
        # Trier tickets par nouvelle position
        tickets_to_move.sort(key=lambda x: x['new_position'])
        
        # Appliquer changements
        for item in tickets_to_move:
            ticket = item['ticket']
            new_position = item['new_position']
            old_position = item['old_position']
            
            # Mettre à jour position
            ticket.position = new_position
            ticket.save(update_fields=['position'])
            
            # Logger activité
            ActivityLog.log_activity(
                user=ticket.customer,
                action_type='update',
                description=f"Position automatiquement changée: {old_position} → {new_position}",
                model_name='Ticket',
                object_id=ticket.id,
                queue_id=queue.id,
                reorganization_reason='travel_time_optimization'
            )
        
        # Recalculer positions de tous les tickets de la file
        queue.reorder_tickets()
        
        logger.info(f"Réorganisation appliquée sur file {queue.id}")
        
    except Exception as e:
        logger.error(f"Erreur application réorganisation: {e}")
        raise