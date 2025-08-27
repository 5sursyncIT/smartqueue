# apps/core/consumers.py
"""
WebSocket Consumers pour SmartQueue
Notifications temps réel géolocalisation et files d'attente
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


class UserNotificationConsumer(AsyncWebsocketConsumer):
    """Consumer pour notifications utilisateur individuelles"""
    
    async def connect(self):
        """Connexion WebSocket"""
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user_group_name = f'user_notifications_{self.user_id}'
        
        # Vérifier authentification
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close()
            return
        
        # Vérifier autorisation (utilisateur lui-même ou admin)
        if str(user.id) != self.user_id and not user.user_type in ['admin', 'super_admin']:
            await self.close()
            return
        
        # Rejoindre groupe
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer statut connexion
        await self.send(text_data=json.dumps({
            'type': 'connection_status',
            'message': 'Connecté aux notifications',
            'user_id': self.user_id
        }))
        
        logger.info(f"User {self.user_id} connected to notifications WebSocket")
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket"""
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
        
        logger.info(f"User {self.user_id} disconnected from notifications WebSocket")
    
    async def receive(self, text_data):
        """Recevoir message du client"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'ping':
                # Répondre au ping pour maintenir connexion
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': text_data_json.get('timestamp')
                }))
            
            elif message_type == 'mark_notification_read':
                # Marquer notification comme lue
                notification_id = text_data_json.get('notification_id')
                await self.mark_notification_read(notification_id)
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from user {self.user_id}")
    
    async def notification_message(self, event):
        """Envoyer notification à l'utilisateur"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    async def travel_update(self, event):
        """Mise à jour temps de trajet"""
        await self.send(text_data=json.dumps({
            'type': 'travel_update',
            'data': event['data']
        }))
    
    async def queue_position_update(self, event):
        """Mise à jour position dans la file"""
        await self.send(text_data=json.dumps({
            'type': 'queue_position_update',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Marquer notification comme lue"""
        try:
            from apps.notifications.models import Notification
            notification = Notification.objects.get(id=notification_id, recipient_id=self.user_id)
            notification.is_read = True
            notification.save()
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")


class LocationUpdateConsumer(AsyncWebsocketConsumer):
    """Consumer pour mises à jour géolocalisation temps réel"""
    
    async def connect(self):
        """Connexion WebSocket géolocalisation"""
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.location_group_name = f'user_location_{self.user_id}'
        
        # Vérifier authentification et autorisation
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close()
            return
        
        if str(user.id) != self.user_id and not user.user_type in ['admin', 'super_admin']:
            await self.close()
            return
        
        # Rejoindre groupe
        await self.channel_layer.group_add(
            self.location_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"User {self.user_id} connected to location updates WebSocket")
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket géolocalisation"""
        await self.channel_layer.group_discard(
            self.location_group_name,
            self.channel_name
        )
        
        logger.info(f"User {self.user_id} disconnected from location updates WebSocket")
    
    async def receive(self, text_data):
        """Recevoir mise à jour position GPS"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'location_update':
                # Traiter mise à jour localisation
                await self.process_location_update(data)
            
        except json.JSONDecodeError:
            logger.error(f"Invalid location data from user {self.user_id}")
    
    async def process_location_update(self, data):
        """Traiter mise à jour localisation"""
        try:
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            accuracy = data.get('accuracy', 50)
            
            if latitude and longitude:
                # Sauvegarder en base (async)
                await self.update_user_location(latitude, longitude, accuracy)
                
                # Confirmer réception
                await self.send(text_data=json.dumps({
                    'type': 'location_update_confirmed',
                    'timestamp': data.get('timestamp'),
                    'status': 'saved'
                }))
        
        except Exception as e:
            logger.error(f"Error processing location update: {e}")
            await self.send(text_data=json.dumps({
                'type': 'location_update_error',
                'error': 'Erreur sauvegarde localisation'
            }))
    
    @database_sync_to_async
    def update_user_location(self, latitude, longitude, accuracy):
        """Mettre à jour localisation utilisateur (async)"""
        from apps.locations.models import UserLocation
        from django.utils import timezone
        
        try:
            user = User.objects.get(id=self.user_id)
            location, created = UserLocation.objects.update_or_create(
                user=user,
                defaults={
                    'latitude': latitude,
                    'longitude': longitude,
                    'accuracy_meters': accuracy,
                    'last_updated': timezone.now()
                }
            )
            
            # Mettre à jour commune la plus proche
            location.update_nearest_commune()
            
        except Exception as e:
            logger.error(f"Database error updating location: {e}")
            raise
    
    async def travel_time_calculated(self, event):
        """Nouveau temps de trajet calculé"""
        await self.send(text_data=json.dumps({
            'type': 'travel_time_update',
            'data': event['data']
        }))
    
    async def departure_reminder(self, event):
        """Rappel heure de départ"""
        await self.send(text_data=json.dumps({
            'type': 'departure_reminder',
            'data': event['data']
        }))


class QueueUpdatesConsumer(AsyncWebsocketConsumer):
    """Consumer pour mises à jour file d'attente temps réel"""
    
    async def connect(self):
        """Connexion WebSocket file d'attente"""
        self.queue_id = self.scope['url_route']['kwargs']['queue_id']
        self.queue_group_name = f'queue_updates_{self.queue_id}'
        
        # Vérifier authentification
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close()
            return
        
        # Rejoindre groupe
        await self.channel_layer.group_add(
            self.queue_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer état actuel de la file
        await self.send_queue_status()
        
        logger.info(f"User {user.id} connected to queue {self.queue_id} WebSocket")
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket file"""
        await self.channel_layer.group_discard(
            self.queue_group_name,
            self.channel_name
        )
    
    async def send_queue_status(self):
        """Envoyer statut actuel de la file"""
        queue_data = await self.get_queue_data()
        await self.send(text_data=json.dumps({
            'type': 'queue_status',
            'data': queue_data
        }))
    
    @database_sync_to_async
    def get_queue_data(self):
        """Récupérer données file d'attente"""
        try:
            from apps.queues.models import Queue
            queue = Queue.objects.get(id=self.queue_id)
            
            return {
                'id': queue.id,
                'name': queue.name,
                'status': queue.status,
                'current_number': queue.current_number,
                'total_waiting': queue.tickets.filter(status='waiting').count(),
                'estimated_wait_time': queue.get_estimated_wait_time(),
            }
        except Exception as e:
            logger.error(f"Error getting queue data: {e}")
            return {}
    
    async def queue_update(self, event):
        """Mise à jour file d'attente"""
        await self.send(text_data=json.dumps({
            'type': 'queue_update',
            'data': event['data']
        }))
    
    async def ticket_called(self, event):
        """Ticket appelé"""
        await self.send(text_data=json.dumps({
            'type': 'ticket_called',
            'data': event['data']
        }))
    
    async def queue_reorganized(self, event):
        """File réorganisée"""
        await self.send(text_data=json.dumps({
            'type': 'queue_reorganized',
            'data': event['data']
        }))


class AdminDashboardConsumer(AsyncWebsocketConsumer):
    """Consumer pour dashboard admin temps réel"""
    
    async def connect(self):
        """Connexion WebSocket admin"""
        user = self.scope.get('user')
        
        # Vérifier droits admin
        if not user or user.is_anonymous or user.user_type not in ['admin', 'super_admin']:
            await self.close()
            return
        
        self.admin_group_name = 'admin_dashboard'
        
        await self.channel_layer.group_add(
            self.admin_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer données dashboard
        await self.send_dashboard_data()
        
        logger.info(f"Admin {user.id} connected to dashboard WebSocket")
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket admin"""
        await self.channel_layer.group_discard(
            self.admin_group_name,
            self.channel_name
        )
    
    async def send_dashboard_data(self):
        """Envoyer données dashboard"""
        dashboard_data = await self.get_dashboard_data()
        await self.send(text_data=json.dumps({
            'type': 'dashboard_data',
            'data': dashboard_data
        }))
    
    @database_sync_to_async
    def get_dashboard_data(self):
        """Récupérer données dashboard admin"""
        try:
            from apps.locations.models import UserLocation, TravelTimeEstimate
            from apps.queues.models import Queue
            from apps.tickets.models import Ticket
            from django.utils import timezone
            
            # Données temps réel
            active_locations = UserLocation.objects.filter(
                location_sharing_enabled=True,
                last_updated__gte=timezone.now() - timezone.timedelta(minutes=10)
            ).count()
            
            active_queues = Queue.objects.filter(status='open').count()
            waiting_tickets = Ticket.objects.filter(status='waiting').count()
            recent_estimates = TravelTimeEstimate.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(hours=1)
            ).count()
            
            return {
                'active_locations': active_locations,
                'active_queues': active_queues,
                'waiting_tickets': waiting_tickets,
                'recent_travel_estimates': recent_estimates,
                'timestamp': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {}
    
    async def dashboard_update(self, event):
        """Mise à jour dashboard"""
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': event['data']
        }))


class OrganizationMonitorConsumer(AsyncWebsocketConsumer):
    """Consumer pour monitoring organisation"""
    
    async def connect(self):
        """Connexion WebSocket monitoring organisation"""
        self.org_id = self.scope['url_route']['kwargs']['org_id']
        self.org_group_name = f'org_monitor_{self.org_id}'
        
        user = self.scope.get('user')
        
        # Vérifier droits sur organisation
        if not user or user.is_anonymous:
            await self.close()
            return
        
        # Vérifier appartenance organisation ou droits admin
        if not await self.user_can_monitor_org(user):
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.org_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"User {user.id} connected to org {self.org_id} monitoring WebSocket")
    
    async def disconnect(self, close_code):
        """Déconnexion WebSocket monitoring"""
        await self.channel_layer.group_discard(
            self.org_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def user_can_monitor_org(self, user):
        """Vérifier si utilisateur peut monitorer organisation"""
        try:
            if user.user_type in ['super_admin']:
                return True
            
            if user.user_type in ['admin', 'staff']:
                # Vérifier appartenance à l'organisation
                return user.organizations.filter(id=self.org_id).exists()
            
            return False
            
        except Exception:
            return False
    
    async def organization_update(self, event):
        """Mise à jour organisation"""
        await self.send(text_data=json.dumps({
            'type': 'organization_update',
            'data': event['data']
        }))