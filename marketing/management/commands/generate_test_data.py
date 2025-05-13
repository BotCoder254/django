import random
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from marketing.models import Campaign, EmailTemplate, Subscriber, SubscriberList, CampaignAnalytics, EmailOpen, LinkClick
from users.models import UserActivity, Subscription

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates test data for the email marketing platform'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=5, help='Number of test users to create')
        parser.add_argument('--subscribers', type=int, default=100, help='Number of subscribers to create')
        parser.add_argument('--campaigns', type=int, default=15, help='Number of campaigns to create')
        parser.add_argument('--clean', action='store_true', help='Clean existing test data before generating new data')

    def handle(self, *args, **options):
        user_count = options['users']
        subscriber_count = options['subscribers']
        campaign_count = options['campaigns']
        clean = options['clean']

        if clean:
            self.clean_data()
            self.stdout.write(self.style.SUCCESS('Cleaned existing test data.'))

        with transaction.atomic():
            # Create test users
            users = self.create_test_users(user_count)
            self.stdout.write(self.style.SUCCESS(f'Created {len(users)} test users'))

            # Create test subscriber lists and subscribers
            subscriber_lists = self.create_subscriber_lists(users)
            self.stdout.write(self.style.SUCCESS(f'Created {len(subscriber_lists)} subscriber lists'))

            subscribers = self.create_subscribers(subscriber_count, subscriber_lists)
            self.stdout.write(self.style.SUCCESS(f'Created {len(subscribers)} subscribers'))

            # Create test templates and campaigns
            templates = self.create_email_templates(users)
            self.stdout.write(self.style.SUCCESS(f'Created {len(templates)} email templates'))

            campaigns = self.create_campaigns(campaign_count, users, subscriber_lists, templates)
            self.stdout.write(self.style.SUCCESS(f'Created {len(campaigns)} campaigns'))

            # Generate campaign analytics
            self.generate_campaign_analytics(campaigns, subscribers)
            self.stdout.write(self.style.SUCCESS('Generated campaign analytics data'))

            # Create subscriptions and user activities
            self.create_subscriptions(users)
            self.create_user_activities(users)
            self.stdout.write(self.style.SUCCESS('Created subscription and user activity data'))

        self.stdout.write(self.style.SUCCESS('Test data generation complete!'))
        self.stdout.write(self.style.SUCCESS('\nTest User Credentials:'))
        for i, user in enumerate(users):
            self.stdout.write(f"User #{i+1}: Email: {user.email}, Password: password123")

    def clean_data(self):
        """Clean existing test data"""
        LinkClick.objects.filter(subscriber__email__contains='test_subscriber').delete()
        EmailOpen.objects.filter(subscriber__email__contains='test_subscriber').delete()
        CampaignAnalytics.objects.filter(campaign__name__startswith='Test Campaign').delete()
        Campaign.objects.filter(name__startswith='Test Campaign').delete()
        EmailTemplate.objects.filter(name__startswith='Test Template').delete()
        Subscriber.objects.filter(email__contains='test_subscriber').delete()
        SubscriberList.objects.filter(name__startswith='Test List').delete()
        User.objects.filter(email__contains='test_user').delete()

    def create_test_users(self, count):
        """Create test users with different subscription plans"""
        users = []
        plans = ['free', 'basic', 'premium', 'enterprise']
        
        # Create admin user if needed
        admin_exists = User.objects.filter(is_superuser=True).exists()
        if not admin_exists:
            admin = User.objects.create_superuser(
                email='admin@example.com',
                username='admin',
                password='adminpassword',
                is_verified=True,
                company_name='Admin Company',
                subscription_plan='enterprise',
                usage_quota=100000,
                usage_count=random.randint(5000, 20000)
            )
            users.append(admin)

        for i in range(count):
            plan = random.choice(plans)
            quota = {
                'free': 100,
                'basic': 5000,
                'premium': 20000,
                'enterprise': 100000
            }[plan]
            
            usage = random.randint(0, quota // 2)
            
            user = User.objects.create_user(
                email=f'test_user{i+1}@example.com',
                username=f'test_user{i+1}',
                password='password123',
                first_name=f'Test{i+1}',
                last_name=f'User{i+1}',
                is_verified=True,
                company_name=f'Company {i+1}',
                subscription_plan=plan,
                usage_quota=quota,
                usage_count=usage,
                stripe_customer_id=f'cus_test{i+1}',
                has_active_payment_method=plan != 'free',
                subscription_renewal=timezone.now() + timezone.timedelta(days=30) if plan != 'free' else None
            )
            users.append(user)
            
        return users

    def create_subscriber_lists(self, users):
        """Create subscriber lists for each user"""
        lists = []
        list_types = ['Customers', 'Leads', 'Newsletter', 'Product Updates', 'Event Invitations']
        
        for user in users:
            # Each user gets 2-4 lists
            for i in range(random.randint(2, 4)):
                list_type = random.choice(list_types)
                subscriber_list = SubscriberList.objects.create(
                    owner=user,
                    name=f'Test List: {list_type} for {user.first_name}',
                    description=f'A list of {list_type.lower()} for testing purposes.'
                )
                lists.append(subscriber_list)
                
        return lists

    def create_subscribers(self, count, subscriber_lists):
        """Create subscribers and add them to lists"""
        subscribers = []
        domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'example.com']
        
        for i in range(count):
            # Create subscriber
            domain = random.choice(domains)
            
            # Get a random list owner to associate with the subscriber
            list_owner = subscriber_lists[random.randint(0, len(subscriber_lists)-1)].owner
            
            # Create a timezone-aware datetime for created_at
            days_ago = random.randint(1, 365)
            created_at = timezone.now() - timezone.timedelta(days=days_ago)
            
            subscriber = Subscriber.objects.create(
                owner=list_owner,
                email=f'test_subscriber{i+1}@{domain}',
                first_name=f'Subscriber{i+1}',
                last_name=f'Test',
                is_active=random.random() > 0.1,  # 90% are active
                created_at=created_at
            )
            subscribers.append(subscriber)
            
            # Add to 1-3 random lists (but only lists owned by the same user)
            user_lists = [lst for lst in subscriber_lists if lst.owner == list_owner]
            if user_lists:
                for subscriber_list in random.sample(user_lists, min(random.randint(1, 3), len(user_lists))):
                    subscriber_list.subscribers.add(subscriber)
                
        return subscribers

    def create_email_templates(self, users):
        """Create email templates for users"""
        templates = []
        template_types = ['Newsletter', 'Promotional', 'Welcome', 'Announcement', 'Event']
        
        for user in users:
            # Each user gets 2-5 templates
            for i in range(random.randint(2, 5)):
                template_type = random.choice(template_types)
                content = self.get_template_content(template_type)
                
                template = EmailTemplate.objects.create(
                    owner=user,
                    name=f'Test Template: {template_type} {i+1}',
                    subject=f'{template_type} Template Subject',
                    content=f"Plain text version for {template_type}",
                    html_content=content
                )
                templates.append(template)
                
        return templates

    def get_template_content(self, template_type):
        """Generate HTML content based on template type"""
        if template_type == 'Newsletter':
            return """
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee;">
                    <h1 style="color: #4F46E5;">Newsletter Title</h1>
                    <p>Hello {{subscriber.first_name}},</p>
                    <p>This is our latest newsletter with updates and interesting content.</p>
                    <h2 style="color: #4F46E5;">Latest Updates</h2>
                    <ul>
                        <li>New feature launch coming soon!</li>
                        <li>Check out our latest blog post</li>
                        <li>Customer spotlight: Success story</li>
                    </ul>
                    <p>Thanks for being a subscriber!</p>
                    <p>The Team</p>
                </div>
            """
        elif template_type == 'Promotional':
            return """
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee;">
                    <h1 style="color: #4F46E5;">Special Offer!</h1>
                    <p>Hello {{subscriber.first_name}},</p>
                    <p>We're excited to offer you an exclusive discount on our premium plan!</p>
                    <div style="background-color: #4F46E5; color: white; padding: 15px; text-align: center; margin: 20px 0;">
                        <h2 style="margin: 0;">50% OFF</h2>
                        <p style="margin: 5px 0 0;">Use code: TESTCODE50</p>
                    </div>
                    <p>This offer is only available for a limited time. <a href="{{campaign.tracking_url}}" style="color: #4F46E5;">Click here</a> to claim your discount.</p>
                    <p>Thank you!</p>
                </div>
            """
        elif template_type == 'Welcome':
            return """
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee;">
                    <h1 style="color: #4F46E5;">Welcome to Our Community!</h1>
                    <p>Hello {{subscriber.first_name}},</p>
                    <p>Thank you for subscribing! We're thrilled to have you join our community.</p>
                    <p>Here's what you can expect from us:</p>
                    <ul>
                        <li>Weekly newsletters with valuable content</li>
                        <li>Exclusive offers and promotions</li>
                        <li>Industry insights and tips</li>
                    </ul>
                    <p>If you have any questions, feel free to reply to this email.</p>
                    <p>Warm regards,<br>The Team</p>
                </div>
            """
        else:
            return """
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee;">
                    <h1 style="color: #4F46E5;">Important Announcement</h1>
                    <p>Hello {{subscriber.first_name}},</p>
                    <p>We have some important news to share with you today.</p>
                    <p>This is a test email template for demonstration purposes.</p>
                    <p>Thank you for your continued support!</p>
                    <p>Best regards,<br>The Team</p>
                    <p><small>If you no longer wish to receive these emails, <a href="{{campaign.unsubscribe_url}}" style="color: #4F46E5;">unsubscribe here</a>.</small></p>
                </div>
            """

    def create_campaigns(self, count, users, subscriber_lists, templates):
        """Create test campaigns"""
        campaigns = []
        
        # Define status distribution
        statuses = ['draft', 'scheduled', 'sending', 'sent', 'sent', 'sent']  # More sent campaigns for analytics
        
        campaign_count = 0
        while campaign_count < count:
            for user in users:
                if campaign_count >= count:
                    break
                    
                # Skip if user has no lists or templates
                user_lists = [lst for lst in subscriber_lists if lst.owner == user]
                user_templates = [tpl for tpl in templates if tpl.owner == user]
                
                if not user_lists or not user_templates:
                    continue
                
                status = random.choice(statuses)
                send_date = timezone.now()
                
                if status == 'scheduled':
                    # Future date for scheduled campaigns
                    days_ahead = random.randint(1, 7)
                    send_date = timezone.now() + timezone.timedelta(days=days_ahead)
                elif status == 'sent':
                    # Past date for sent campaigns
                    days_ago = random.randint(1, 30)
                    send_date = timezone.now() - timezone.timedelta(days=days_ago)
                
                template = random.choice(user_templates)
                
                campaign = Campaign.objects.create(
                    owner=user,
                    name=f'Test Campaign {campaign_count+1}',
                    subject=f'Test Subject {campaign_count+1}',
                    slug=f'test-campaign-{campaign_count+1}',
                    content=f"Plain text content for campaign {campaign_count+1}",
                    html_content=template.html_content,
                    from_email=user.email,
                    from_name=f'{user.first_name} {user.last_name}',
                    template=template,
                    status=status,
                    schedule_time=send_date if status in ['scheduled', 'sent'] else None,
                    sent_time=send_date if status == 'sent' else None
                )
                
                # Add subscriber lists
                selected_lists = random.sample(user_lists, random.randint(1, len(user_lists)))
                campaign.lists.set(selected_lists)
                
                campaigns.append(campaign)
                campaign_count += 1
                
        return campaigns

    def generate_campaign_analytics(self, campaigns, subscribers):
        """Generate analytics data for sent campaigns"""
        for campaign in campaigns:
            if campaign.status == 'sent':
                # Get potential recipients from campaign's subscriber lists
                recipient_ids = set()
                for subscriber_list in campaign.lists.all():
                    recipient_ids.update(subscriber_list.subscribers.values_list('id', flat=True))
                
                recipients = [s for s in subscribers if s.id in recipient_ids]
                if not recipients:
                    continue
                
                # Determine how many opens and clicks to generate
                recipient_count = len(recipients)
                open_rate = random.uniform(0.15, 0.45)  # 15-45% open rate
                click_rate = random.uniform(0.05, 0.25)  # 5-25% of opens have clicks
                
                open_count = int(recipient_count * open_rate)
                opened_subscribers = random.sample(recipients, min(open_count, len(recipients)))
                
                # Create campaign analytics first
                analytics = CampaignAnalytics.objects.create(
                    campaign=campaign,
                    sent_count=recipient_count,
                    delivered_count=recipient_count - random.randint(0, 5),  # Some emails may bounce
                    open_count=open_count,
                    click_count=int(open_count * click_rate),
                    bounce_count=random.randint(0, 5),
                    complaint_count=random.randint(0, 2),
                    unsubscribe_count=random.randint(0, 3)
                )
                
                # Create opens
                for subscriber in opened_subscribers:
                    # Create timezone-aware datetime for open time
                    minutes_after_sent = random.randint(5, 1440)
                    open_time = campaign.sent_time + timezone.timedelta(minutes=minutes_after_sent)
                    if open_time > timezone.now():
                        # If the calculated open time is in the future, use a time in the past
                        open_time = timezone.now() - timezone.timedelta(minutes=random.randint(5, 60))
                    
                    email_open = EmailOpen.objects.create(
                        campaign_analytics=analytics,
                        subscriber=subscriber,
                        timestamp=open_time,
                        ip_address=f'192.168.0.{random.randint(1, 255)}',
                        user_agent=random.choice([
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15',
                            'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15'
                        ])
                    )

    def create_subscriptions(self, users):
        """Create subscription records for users with paid plans"""
        for user in users:
            if user.subscription_plan != 'free':
                # Create a timezone-aware start date
                days_ago = random.randint(1, 60)
                sub_start_date = timezone.now() - timezone.timedelta(days=days_ago)
                
                # Calculate next billing date
                next_billing_date = sub_start_date + timezone.timedelta(days=30)
                
                Subscription.objects.create(
                    user=user,
                    plan=user.subscription_plan,
                    status='active',
                    stripe_subscription_id=f'sub_test{user.id}',
                    start_date=sub_start_date,
                    next_billing_date=next_billing_date,
                    cancel_at_period_end=random.random() < 0.2,  # 20% chance of cancellation
                )

    def create_user_activities(self, users):
        """Create user activity logs"""
        activities = [
            'login',
            'campaign_created',
            'campaign_sent',
            'template_created',
            'subscriber_list_created',
            'profile_updated',
            'subscription_upgraded'
        ]
        
        for user in users:
            # Create between 5-20 activities per user
            for _ in range(random.randint(5, 20)):
                activity_type = random.choice(activities)
                
                # Create timezone-aware datetime for activity
                days_ago = random.randint(1, 30)
                activity_date = timezone.now() - timezone.timedelta(days=days_ago)
                
                UserActivity.objects.create(
                    user=user,
                    action=activity_type,
                    timestamp=activity_date,
                    details={'ip': f'192.168.0.{random.randint(1, 255)}'}
                ) 