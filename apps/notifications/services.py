# apps/notifications/services.py
"""
Services pour les notifications SmartQueue
Logique métier pour SMS, Push, Email sénégalais
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from django.utils import timezone
from django.template import Template, Context
from django.contrib.contenttypes.models import ContentType
from datetime import timedelta
from .models import (
    NotificationTemplate, Notification, NotificationPreference,
    SMSProvider, NotificationLog
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service principal pour créer et envoyer des notifications
    
    Gère la création, le templating, et l'envoi de notifications
    via différents canaux (SMS, Email, Push)
    """
    
    def create_notification(
        self,
        template: NotificationTemplate,
        recipient,  # User object
        content_object=None,
        custom_variables: Dict[str, Any] = None,
        priority: str = 'normal',
        schedule_for: Optional[timezone.datetime] = None
    ) -> Notification:
        """
        Créer une notification à partir d'un template
        
        Args:
            template: Template de notification à utiliser
            recipient: Utilisateur destinataire
            content_object: Objet lié (Ticket, Appointment, etc.)
            custom_variables: Variables personnalisées pour le template
            priority: Priorité de la notification
            schedule_for: Programmer l'envoi (optionnel)
        
        Returns:
            Instance de Notification créée
        """
        try:
            # Vérifier les préférences du destinataire
            preferences = self._get_user_preferences(recipient)
            
            # Vérifier si ce type de notification est activé
            if not self._should_send_notification(template, preferences):
                logger.info(f"Notification {template.category} désactivée pour {recipient}")
                return None
            
            # Choisir le canal selon les préférences
            notification_type = self._choose_notification_channel(template, preferences)
            if not notification_type:
                logger.info(f"Aucun canal disponible pour {recipient}")
                return None
            
            # Préparer les variables pour le template
            variables = self._prepare_template_variables(
                content_object, custom_variables or {}
            )
            
            # Générer le contenu final
            language = preferences.language if preferences else 'fr'
            subject = self._render_template(template.get_subject(language), variables)
            message = self._render_template(template.get_message(language), variables)
            
            # Déterminer la destination
            phone_number, email_address, push_token = self._get_destination_info(
                recipient, notification_type
            )
            
            # Calculer la date d'envoi
            if schedule_for is None:
                if template.send_immediately:
                    schedule_for = timezone.now()
                else:
                    schedule_for = timezone.now() + timedelta(minutes=template.delay_minutes)
            
            # Vérifier les heures silencieuses
            if preferences and not preferences.should_send_at_time(schedule_for):
                # Reporter au lendemain après les heures silencieuses
                next_day = schedule_for.date() + timedelta(days=1)
                schedule_for = timezone.datetime.combine(
                    next_day, preferences.quiet_hours_end
                ).replace(tzinfo=schedule_for.tzinfo)
            
            # Créer la notification
            notification = Notification.objects.create(
                recipient=recipient,
                template=template,
                content_type=ContentType.objects.get_for_model(content_object) if content_object else None,
                object_id=content_object.id if content_object else None,
                subject=subject,
                message=message,
                phone_number=phone_number,
                email_address=email_address,
                push_token=push_token,
                priority=priority,
                scheduled_at=schedule_for
            )
            
            # Log de création
            NotificationLog.objects.create(
                notification=notification,
                action='created',
                details={
                    'template_id': template.id,
                    'notification_type': notification_type,
                    'scheduled_for': schedule_for.isoformat(),
                    'variables': variables
                }
            )
            
            # Si c'est immédiat, l'envoyer tout de suite
            if schedule_for <= timezone.now():
                self._queue_for_sending(notification)
            
            logger.info(f"Notification créée: {notification.id} pour {recipient}")
            return notification
            
        except Exception as e:
            logger.error(f"Erreur création notification: {e}")
            raise
    
    def send_notification(self, notification: Notification) -> bool:
        """
        Envoyer une notification spécifique
        
        Args:
            notification: Instance de notification à envoyer
        
        Returns:
            True si envoi réussi, False sinon
        """
        try:
            # Marquer comme en cours d'envoi
            notification.status = 'sending'
            notification.save(update_fields=['status'])
            
            # Log de tentative
            NotificationLog.objects.create(
                notification=notification,
                action='sent',
                details={'attempt': notification.attempt_count + 1}
            )
            
            # Choisir la méthode d'envoi selon le type
            if notification.template.notification_type == 'sms':
                success = self._send_sms(notification)
            elif notification.template.notification_type == 'email':
                success = self._send_email(notification)
            elif notification.template.notification_type == 'push':
                success = self._send_push(notification)
            else:
                success = False
                logger.error(f"Type de notification non supporté: {notification.template.notification_type}")
            
            if success:
                notification.mark_as_sent()
                logger.info(f"Notification {notification.id} envoyée avec succès")
            else:
                notification.mark_as_failed("Échec d'envoi")
                logger.error(f"Échec envoi notification {notification.id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur envoi notification {notification.id}: {e}")
            notification.mark_as_failed(str(e))
            return False
    
    def _get_user_preferences(self, user) -> Optional[NotificationPreference]:
        """Récupérer les préférences de notification d'un utilisateur"""
        try:
            return user.notification_preferences
        except NotificationPreference.DoesNotExist:
            return None
    
    def _should_send_notification(
        self, 
        template: NotificationTemplate, 
        preferences: Optional[NotificationPreference]
    ) -> bool:
        """Vérifier si on doit envoyer cette notification selon les préférences"""
        if not preferences:
            return True  # Pas de préférences = envoyer
        
        # Vérifier selon la catégorie
        category_mapping = {
            'ticket_called': preferences.notify_ticket_called,
            'queue_position_update': preferences.notify_position_update,
            'queue_full': preferences.notify_queue_full,
            'appointment_confirmed': preferences.notify_appointment_confirmed,
            'appointment_reminder': preferences.notify_appointment_reminder,
        }
        
        return category_mapping.get(template.category, True)
    
    def _choose_notification_channel(
        self, 
        template: NotificationTemplate, 
        preferences: Optional[NotificationPreference]
    ) -> Optional[str]:
        """Choisir le meilleur canal selon les préférences et le template"""
        if not preferences:
            return template.notification_type
        
        # Ordre de préférence selon le type de template
        if template.notification_type == 'sms' and preferences.prefer_sms:
            return 'sms'
        elif template.notification_type == 'email' and preferences.prefer_email:
            return 'email'
        elif template.notification_type == 'push' and preferences.prefer_push:
            return 'push'
        elif template.notification_type == 'web' and preferences.prefer_web:
            return 'web'
        
        # Fallback vers SMS si préféré
        if preferences.prefer_sms:
            return 'sms'
        elif preferences.prefer_email:
            return 'email'
        elif preferences.prefer_push:
            return 'push'
        
        return None
    
    def _prepare_template_variables(
        self, 
        content_object, 
        custom_variables: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Préparer les variables pour le rendu du template"""
        variables = custom_variables.copy()
        
        # Variables communes
        variables.update({
            'current_date': timezone.now().strftime('%d/%m/%Y'),
            'current_time': timezone.now().strftime('%H:%M'),
        })
        
        # Variables spécifiques à l'objet lié
        if content_object:
            if hasattr(content_object, 'ticket_number'):
                # C'est un Ticket
                variables.update({
                    'ticket_number': content_object.ticket_number,
                    'organization': content_object.organization.trade_name,
                    'service': content_object.service.name,
                    'queue_name': content_object.queue.name if content_object.queue else '',
                    'position': getattr(content_object, 'position', ''),
                    'window_number': getattr(content_object, 'window_number', ''),
                })
            elif hasattr(content_object, 'appointment_number'):
                # C'est un Appointment
                variables.update({
                    'appointment_number': content_object.appointment_number,
                    'organization': content_object.organization.trade_name,
                    'service': content_object.service.name,
                    'date': content_object.scheduled_date.strftime('%d/%m/%Y'),
                    'time': content_object.scheduled_time.strftime('%H:%M'),
                    'customer_name': content_object.customer.get_full_name(),
                })
        
        return variables
    
    def _render_template(self, template_text: str, variables: Dict[str, Any]) -> str:
        """Rendre un template avec les variables"""
        try:
            template = Template(template_text)
            context = Context(variables)
            return template.render(context)
        except Exception as e:
            logger.error(f"Erreur rendu template: {e}")
            return template_text  # Retourner le template original en cas d'erreur
    
    def _get_destination_info(self, user, notification_type):
        """Récupérer les informations de destination selon le type"""
        phone_number = ''
        email_address = ''
        push_token = ''
        
        if notification_type == 'sms':
            phone_number = user.phone
        elif notification_type == 'email':
            email_address = user.email
        elif notification_type == 'push':
            # À implémenter : récupérer le token FCM du user
            push_token = getattr(user, 'push_token', '')
        
        return phone_number, email_address, push_token
    
    def _queue_for_sending(self, notification: Notification):
        """Mettre en file d'attente pour envoi"""
        notification.status = 'queued'
        notification.save(update_fields=['status'])
        
        # Log
        NotificationLog.objects.create(
            notification=notification,
            action='queued'
        )
        
        # Dans un vrai projet, on utiliserait Celery ici
        # Pour l'instant, on envoie directement
        self.send_notification(notification)
    
    def _send_sms(self, notification: Notification) -> bool:
        """Envoyer un SMS via les fournisseurs configurés"""
        try:
            # Récupérer le fournisseur SMS actif
            provider = SMSProvider.objects.filter(
                is_active=True
            ).order_by('priority').first()
            
            if not provider:
                logger.error("Aucun fournisseur SMS configuré")
                return False
            
            # Préparer les données
            data = {
                'to': notification.phone_number,
                'message': notification.message,
                'from': provider.sender_name
            }
            
            # Headers avec authentification
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {provider.api_key}'
            }
            
            # Envoyer via l'API du fournisseur
            response = requests.post(
                provider.api_url,
                json=data,
                headers=headers,
                timeout=30
            )
            
            # Log du résultat
            NotificationLog.objects.create(
                notification=notification,
                action='sent' if response.status_code == 200 else 'failed',
                provider_used=provider,
                cost=provider.cost_per_sms if response.status_code == 200 else None,
                details={
                    'status_code': response.status_code,
                    'response': response.text[:500],  # Limiter la taille
                    'provider': provider.name
                }
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erreur envoi SMS: {e}")
            
            NotificationLog.objects.create(
                notification=notification,
                action='failed',
                details={'error': str(e)}
            )
            
            return False
    
    def _send_email(self, notification: Notification) -> bool:
        """Envoyer un email"""
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            # Envoyer l'email
            send_mail(
                subject=notification.subject,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.email_address],
                fail_silently=False
            )
            
            # Log du succès
            NotificationLog.objects.create(
                notification=notification,
                action='sent',
                details={'email_sent': True}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            
            NotificationLog.objects.create(
                notification=notification,
                action='failed',
                details={'error': str(e)}
            )
            
            return False
    
    def _send_push(self, notification: Notification) -> bool:
        """Envoyer une notification push"""
        try:
            # À implémenter avec Firebase Cloud Messaging
            logger.info(f"Notification push simulée pour {notification.push_token}")
            
            # Log de simulation
            NotificationLog.objects.create(
                notification=notification,
                action='sent',
                details={'push_simulated': True}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi push: {e}")
            
            NotificationLog.objects.create(
                notification=notification,
                action='failed',
                details={'error': str(e)}
            )
            
            return False


class NotificationAutomationService:
    """
    Service pour les notifications automatiques
    
    Intégration avec les autres apps pour envoyer des notifications
    lors d'événements spécifiques (ticket appelé, RDV confirmé, etc.)
    """
    
    def __init__(self):
        self.notification_service = NotificationService()
    
    def notify_ticket_called(self, ticket):
        """Notifier qu'un ticket est appelé"""
        try:
            template = NotificationTemplate.objects.get(
                category='ticket_called',
                notification_type='sms',
                is_active=True
            )
            
            variables = {
                'window_number': getattr(ticket, 'window_number', 'G1')
            }
            
            return self.notification_service.create_notification(
                template=template,
                recipient=ticket.customer,
                content_object=ticket,
                custom_variables=variables,
                priority='high'
            )
            
        except NotificationTemplate.DoesNotExist:
            logger.warning("Template 'ticket_called' SMS non trouvé")
            return None
        except Exception as e:
            logger.error(f"Erreur notification ticket appelé: {e}")
            return None
    
    def notify_appointment_confirmed(self, appointment):
        """Notifier qu'un RDV est confirmé"""
        try:
            template = NotificationTemplate.objects.get(
                category='appointment_confirmed',
                notification_type='sms',
                is_active=True
            )
            
            return self.notification_service.create_notification(
                template=template,
                recipient=appointment.customer,
                content_object=appointment,
                priority='normal'
            )
            
        except NotificationTemplate.DoesNotExist:
            logger.warning("Template 'appointment_confirmed' SMS non trouvé")
            return None
        except Exception as e:
            logger.error(f"Erreur notification RDV confirmé: {e}")
            return None
    
    def notify_appointment_reminder(self, appointment):
        """Envoyer un rappel de RDV"""
        try:
            template = NotificationTemplate.objects.get(
                category='appointment_reminder',
                notification_type='sms',
                is_active=True
            )
            
            # Programmer 24h avant le RDV
            appointment_datetime = timezone.datetime.combine(
                appointment.scheduled_date,
                appointment.scheduled_time
            ).replace(tzinfo=timezone.get_current_timezone())
            
            reminder_time = appointment_datetime - timedelta(hours=24)
            
            return self.notification_service.create_notification(
                template=template,
                recipient=appointment.customer,
                content_object=appointment,
                priority='normal',
                schedule_for=reminder_time
            )
            
        except NotificationTemplate.DoesNotExist:
            logger.warning("Template 'appointment_reminder' SMS non trouvé")
            return None
        except Exception as e:
            logger.error(f"Erreur notification rappel RDV: {e}")
            return None