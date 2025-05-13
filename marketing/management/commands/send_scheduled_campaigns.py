from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from marketing.models import Campaign, EmailEvent, Notification
from users.models import UserActivity
from marketing.utils import send_email_with_settings
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Send scheduled campaigns that are due'
    
    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"Looking for scheduled campaigns due by {now}")
        
        # Find campaigns that are scheduled and due
        due_campaigns = Campaign.objects.filter(
            status='scheduled',
            schedule_time__lte=now
        )
        
        self.stdout.write(f"Found {due_campaigns.count()} campaign(s) to send")
        
        for campaign in due_campaigns:
            try:
                with transaction.atomic():
                    self.stdout.write(f"Processing campaign: {campaign.name} (ID: {campaign.id})")
                    
                    # Mark campaign as sending
                    campaign.status = 'sending'
                    campaign.save()
                    
                    # Get all subscribers from all lists
                    all_subscribers = set()
                    for email_list in campaign.lists.all():
                        subscribers = email_list.subscribers.filter(is_active=True)
                        all_subscribers.update(subscribers)
                    
                    self.stdout.write(f"Found {len(all_subscribers)} subscriber(s) for campaign")
                    
                    # Send emails to each subscriber
                    sent_count = 0
                    for subscriber in all_subscribers:
                        try:
                            # Personalize content
                            html_content = campaign.html_content
                            text_content = campaign.content
                            
                            # Replace personalization tags
                            for field in ['email', 'first_name', 'last_name']:
                                value = getattr(subscriber, field, '')
                                html_content = html_content.replace('{{' + field + '}}', value)
                                text_content = text_content.replace('{{' + field + '}}', value)
                            
                            # Send email using utility function
                            success = send_email_with_settings(
                                user=campaign.owner,
                                subject=campaign.subject,
                                message=text_content,
                                to_emails=subscriber.email,
                                html_content=html_content,
                                reply_to=campaign.reply_to,
                                from_name=campaign.from_name,
                                from_email=campaign.from_email
                            )
                            
                            if success:
                                sent_count += 1
                                
                                # Create email event
                                EmailEvent.objects.create(
                                    campaign=campaign,
                                    subscriber=subscriber,
                                    event_type='sent',
                                    metadata={
                                        'subscriber_id': subscriber.id, 
                                        'campaign_id': campaign.id
                                    }
                                )
                        except Exception as e:
                            logger.error(f"Error sending to {subscriber.email}: {str(e)}")
                            continue
                    
                    # Update campaign status
                    campaign.status = 'sent'
                    campaign.sent_time = timezone.now()
                    campaign.save()
                    
                    # Create notification
                    Notification.objects.create(
                        user=campaign.owner,
                        message=f"Campaign sent: {campaign.name} to {sent_count} subscribers",
                        notification_type='campaign_sent',
                        related_object_id=campaign.id,
                        related_object_type='campaign'
                    )
                    
                    # Log activity
                    UserActivity.objects.create(
                        user=campaign.owner,
                        action='campaign_sent',
                        description=f'Scheduled campaign "{campaign.name}" sent automatically',
                        metadata={
                            'campaign_id': campaign.id,
                            'recipients_count': sent_count,
                            'scheduled_time': campaign.schedule_time.isoformat() if campaign.schedule_time else None
                        }
                    )
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"Successfully sent campaign {campaign.name} to {sent_count} subscribers"
                    ))
                
            except Exception as e:
                # If any error occurs, mark campaign as draft
                campaign.status = 'draft'
                campaign.save()
                
                logger.error(f"Failed to send campaign {campaign.id}: {str(e)}")
                
                self.stdout.write(self.style.ERROR(
                    f"Failed to send campaign {campaign.name}: {str(e)}"
                ))
                
                # Create error notification
                Notification.objects.create(
                    user=campaign.owner,
                    message=f"Error sending campaign: {campaign.name}",
                    notification_type='campaign_error',
                    related_object_id=campaign.id,
                    related_object_type='campaign'
                )
        
        self.stdout.write(self.style.SUCCESS('Finished processing scheduled campaigns')) 