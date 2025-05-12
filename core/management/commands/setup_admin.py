import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from core.models import SystemSetting, EmailProvider

User = get_user_model()

class Command(BaseCommand):
    help = 'Sets up initial admin user and essential settings'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, default='admin@emailpro.com', help='Admin email')
        parser.add_argument('--password', type=str, default='admin123', help='Admin password')
        parser.add_argument('--username', type=str, default='admin', help='Admin username')

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.HEADING('Starting EmailPro Admin setup...'))
        
        # Create superuser if doesn't exist
        email = options['email']
        password = options['password']
        username = options['username']
        
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='Admin',
                last_name='User',
                company_name='EmailPro',
                is_verified=True,
                subscription_plan='enterprise',
                usage_quota=1000000
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser created with email {email}'))
        else:
            self.stdout.write(self.style.WARNING(f'Superuser with email {email} already exists'))
        
        # Create essential system settings
        system_settings = [
            ('app_name', 'EmailPro', 'Application name displayed in the UI', True),
            ('max_upload_size', '5', 'Maximum upload size in MB', True),
            ('default_from_email', 'no-reply@emailpro.com', 'Default from email for system messages', True),
            ('default_from_name', 'EmailPro', 'Default from name for system messages', True),
            ('contact_email', 'support@emailpro.com', 'Contact email address for support', True),
            ('max_daily_emails_free', '100', 'Maximum daily emails for free tier', True),
            ('max_daily_emails_premium', '20000', 'Maximum daily emails for premium tier', True),
            ('max_daily_emails_enterprise', '100000', 'Maximum daily emails for enterprise tier', True),
            ('free_trial_days', '14', 'Free trial period in days', True),
            ('maintenance_mode', 'false', 'Enable maintenance mode', False),
        ]
        
        setting_count = 0
        for key, value, description, is_public in system_settings:
            obj, created = SystemSetting.objects.update_or_create(
                key=key,
                defaults={
                    'value': value,
                    'description': description,
                    'is_public': is_public
                }
            )
            if created:
                setting_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {setting_count} system settings'))
        
        # Configure default email provider
        default_provider, created = EmailProvider.objects.update_or_create(
            name='SMTP Provider',
            defaults={
                'provider_type': 'smtp',
                'is_active': True,
                'settings': {
                    'host': 'smtp.example.com',
                    'port': 587,
                    'username': 'smtp_user',
                    'password': 'smtp_password',
                    'use_tls': True
                }
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created default email provider'))
        else:
            self.stdout.write(self.style.WARNING('Default email provider already exists'))
        
        self.stdout.write(self.style.SUCCESS('EmailPro Admin setup completed successfully!'))
        self.stdout.write('\n')
        self.stdout.write(self.style.HEADING('You can now log in with:'))
        self.stdout.write(f'URL: http://127.0.0.1:8000/admin/')
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write('\n')
        self.stdout.write(self.style.WARNING('IMPORTANT: Change the default password after first login for security!')) 