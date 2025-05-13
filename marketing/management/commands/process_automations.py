from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from marketing.models import Automation, AutomationStep, EmailEvent, Notification, Subscriber, SubscriberList
from users.models import UserActivity
from marketing.utils import send_email_with_settings
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Process active automations and trigger appropriate steps'
    
    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"Processing automations at {now}")
        
        # Get all active automations
        active_automations = Automation.objects.filter(is_active=True)
        self.stdout.write(f"Found {active_automations.count()} active automation(s)")
        
        for automation in active_automations:
            try:
                self.stdout.write(f"Processing automation: {automation.name} (ID: {automation.id})")
                self.process_automation(automation)
            except Exception as e:
                logger.error(f"Error processing automation {automation.id}: {str(e)}")
                self.stdout.write(self.style.ERROR(
                    f"Failed to process automation {automation.name}: {str(e)}"
                ))
                
                # Create error notification
                Notification.objects.create(
                    user=automation.owner,
                    message=f"Error processing automation: {automation.name}",
                    notification_type='system',
                    related_object_id=automation.id,
                    related_object_type='automation'
                )
        
        self.stdout.write(self.style.SUCCESS('Finished processing automations'))
    
    def process_automation(self, automation):
        """Process an automation based on its trigger type"""
        trigger_type = automation.trigger_type
        
        if trigger_type == 'subscription':
            self.process_subscription_trigger(automation)
        elif trigger_type == 'inactivity':
            self.process_inactivity_trigger(automation)
        elif trigger_type == 'birthday':
            self.process_birthday_trigger(automation)
        elif trigger_type == 'anniversary':
            self.process_anniversary_trigger(automation)
        else:
            self.stdout.write(f"Trigger type '{trigger_type}' is not implemented yet")
    
    def process_subscription_trigger(self, automation):
        """Process automation for new subscriptions"""
        # Find subscribers added in the last 24 hours
        one_day_ago = timezone.now() - timedelta(days=1)
        
        # Get relevant subscribers
        new_subscribers = Subscriber.objects.filter(
            owner=automation.owner,
            created_at__gte=one_day_ago,
            is_active=True
        )
        
        if not new_subscribers.exists():
            self.stdout.write(f"No new subscribers for automation: {automation.name}")
            return
        
        # Get the first email step
        try:
            first_step = automation.steps.filter(step_type='email').order_by('position').first()
            if not first_step:
                self.stdout.write(f"No email steps found for automation: {automation.name}")
                return
                
            # Process each new subscriber
            sent_count = 0
            for subscriber in new_subscribers:
                success = self.send_automation_email(automation, first_step, subscriber)
                if success:
                    sent_count += 1
            
            if sent_count > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"Sent welcome emails to {sent_count} new subscribers for automation: {automation.name}"
                ))
                
                # Create notification
                Notification.objects.create(
                    user=automation.owner,
                    message=f"Automation '{automation.name}' sent to {sent_count} new subscribers",
                    notification_type='system',
                    related_object_id=automation.id,
                    related_object_type='automation'
                )
                
                # Update automation stats
                automation.sent_count += sent_count
                automation.save()
                
        except Exception as e:
            logger.error(f"Error in subscription trigger for automation {automation.id}: {str(e)}")
            self.stdout.write(self.style.ERROR(
                f"Error in subscription trigger for automation {automation.name}: {str(e)}"
            ))
    
    def process_inactivity_trigger(self, automation):
        """Process automation for inactive subscribers"""
        # Get inactivity days from trigger details
        try:
            inactivity_days = int(automation.trigger_details.get('days', 60))
        except (ValueError, TypeError):
            inactivity_days = 60  # default
        
        inactivity_date = timezone.now() - timedelta(days=inactivity_days)
        
        # Find subscribers who haven't engaged since inactivity_date
        # This is a simplified implementation - in a real system, you would
        # check email events like opens and clicks to determine engagement
        inactive_subscribers = Subscriber.objects.filter(
            owner=automation.owner,
            is_active=True,
            events__isnull=True,  # No events recorded
            updated_at__lt=inactivity_date  # Not updated recently
        ).distinct()
        
        if not inactive_subscribers.exists():
            self.stdout.write(f"No inactive subscribers for automation: {automation.name}")
            return
        
        # Get the first email step
        try:
            first_step = automation.steps.filter(step_type='email').order_by('position').first()
            if not first_step:
                self.stdout.write(f"No email steps found for automation: {automation.name}")
                return
                
            # Process each inactive subscriber
            sent_count = 0
            for subscriber in inactive_subscribers:
                success = self.send_automation_email(automation, first_step, subscriber)
                if success:
                    sent_count += 1
            
            if sent_count > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"Sent re-engagement emails to {sent_count} inactive subscribers for automation: {automation.name}"
                ))
                
                # Create notification
                Notification.objects.create(
                    user=automation.owner,
                    message=f"Re-engagement automation '{automation.name}' sent to {sent_count} inactive subscribers",
                    notification_type='system',
                    related_object_id=automation.id,
                    related_object_type='automation'
                )
                
                # Update automation stats
                automation.sent_count += sent_count
                automation.save()
                
        except Exception as e:
            logger.error(f"Error in inactivity trigger for automation {automation.id}: {str(e)}")
            self.stdout.write(self.style.ERROR(
                f"Error in inactivity trigger for automation {automation.name}: {str(e)}"
            ))
    
    def process_birthday_trigger(self, automation):
        """Process automation for subscriber birthdays"""
        # This would require a birthday field in the Subscriber model
        # This is a simplified implementation
        self.stdout.write(f"Birthday trigger for automation: {automation.name} (not fully implemented)")
    
    def process_anniversary_trigger(self, automation):
        """Process automation for anniversaries"""
        # This would require an anniversary field or date tracking
        # This is a simplified implementation
        self.stdout.write(f"Anniversary trigger for automation: {automation.name} (not fully implemented)")
    
    def send_automation_email(self, automation, step, subscriber):
        """Send an email for an automation step to a subscriber"""
        try:
            # Get step details from config
            config = step.config
            subject = config.get('subject', f'Step {step.position} - {automation.name}')
            content = config.get('content', '')
            
            # Replace personalization tags
            for field in ['email', 'first_name', 'last_name']:
                value = getattr(subscriber, field, '')
                content = content.replace('{{' + field + '}}', value)
            
            # Send email using utility function
            success = send_email_with_settings(
                user=automation.owner,
                subject=subject,
                message=content,
                to_emails=subscriber.email,
                html_content=content,  # Use same content as HTML
                headers={'X-Automation-ID': str(automation.id), 'X-Automation-Step': str(step.position)}
            )
            
            if success:
                # Log the email event
                EmailEvent.objects.create(
                    campaign=None,  # No campaign for automation emails
                    subscriber=subscriber,
                    event_type='sent',
                    metadata={
                        'automation_id': automation.id,
                        'step_id': step.id,
                        'subscriber_id': subscriber.id
                    }
                )
                
                # Update user activity
                UserActivity.objects.create(
                    user=automation.owner,
                    action='automation_email_sent',
                    description=f'Automation email sent: {automation.name} - Step {step.position}',
                    metadata={
                        'automation_id': automation.id,
                        'step_id': step.id,
                        'subscriber_id': subscriber.id,
                        'subscriber_email': subscriber.email
                    }
                )
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending automation email: {str(e)}")
            return False 