from django.db import models
from django.conf import settings
from django.utils.text import slugify
import json

class Subscriber(models.Model):
    """
    Model to store email subscribers information
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscribers')
    email = models.EmailField(max_length=255)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom fields stored as JSON
    custom_fields = models.JSONField(null=True, blank=True)
    
    # Location data
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    
    # Demographic data
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    
    class Meta:
        unique_together = ('owner', 'email')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} ({self.owner.email})"
    
    def get_custom_field(self, field_name):
        """Helper method to get a custom field value"""
        if not self.custom_fields:
            return None
        return self.custom_fields.get(field_name)

class SubscriberList(models.Model):
    """
    Model to group subscribers into lists
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriber_lists')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    subscribers = models.ManyToManyField(Subscriber, blank=True, related_name='lists')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def subscriber_count(self):
        return self.subscribers.count()

class EmailTemplate(models.Model):
    """
    Model to store reusable email templates
    """
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_templates')
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    html_content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class Campaign(models.Model):
    """
    Model for email marketing campaigns
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ]
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaigns')
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    from_email = models.EmailField(max_length=255)
    from_name = models.CharField(max_length=100)
    reply_to = models.EmailField(max_length=255, blank=True)
    
    content = models.TextField()
    html_content = models.TextField(blank=True)
    
    lists = models.ManyToManyField(SubscriberList, related_name='campaigns')
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    schedule_time = models.DateTimeField(null=True, blank=True)
    sent_time = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class CampaignAnalytics(models.Model):
    """
    Model to store campaign performance metrics
    """
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name='analytics')
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    open_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    bounce_count = models.PositiveIntegerField(default=0)
    unsubscribe_count = models.PositiveIntegerField(default=0)
    complaint_count = models.PositiveIntegerField(default=0)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = 'Campaign Analytics'
    
    def __str__(self):
        return f"Analytics for {self.campaign.name}"
    
    @property
    def open_rate(self):
        if self.delivered_count == 0:
            return 0
        return (self.open_count / self.delivered_count) * 100
    
    @property
    def click_rate(self):
        if self.delivered_count == 0:
            return 0
        return (self.click_count / self.delivered_count) * 100

class EmailEvent(models.Model):
    """
    Model to track individual email events
    """
    EVENT_TYPES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('complained', 'Complained'),
        ('unsubscribed', 'Unsubscribed'),
    ]
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='events')
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(null=True, blank=True)  # Store additional event data
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.event_type} - {self.subscriber.email} - {self.campaign.name}"

class Notification(models.Model):
    """
    Model to store user notifications
    """
    NOTIFICATION_TYPES = [
        ('campaign_sent', 'Campaign Sent'),
        ('campaign_scheduled', 'Campaign Scheduled'),
        ('campaign_error', 'Campaign Error'),
        ('subscriber_added', 'Subscriber Added'),
        ('subscriber_removed', 'Subscriber Removed'),
        ('list_created', 'List Created'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='system')
    is_read = models.BooleanField(default=False)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)  # For linking to campaigns, subscribers, etc.
    related_object_type = models.CharField(max_length=50, blank=True)  # e.g., 'campaign', 'subscriber', etc.
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} - {self.user.email}"
    
    @classmethod
    def create_notification(cls, user, message, notification_type='system', related_object=None):
        """
        Helper method to create notifications
        """
        notification = cls(
            user=user,
            message=message,
            notification_type=notification_type
        )
        
        if related_object:
            notification.related_object_id = related_object.id
            notification.related_object_type = related_object.__class__.__name__.lower()
            
        notification.save()
        return notification

class UserActivity(models.Model):
    """
    Model to track user activities in the platform
    """
    ACTIVITY_TYPES = [
        ('campaign_created', 'Campaign Created'),
        ('campaign_sent', 'Campaign Sent'),
        ('campaign_scheduled', 'Campaign Scheduled'),
        ('subscriber_added', 'Subscriber Added'),
        ('subscriber_imported', 'Subscribers Imported'),
        ('list_created', 'List Created'),
        ('template_created', 'Template Created'),
        ('login', 'User Login'),
        ('other', 'Other Activity'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='marketing_activities')
    action = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(null=True, blank=True)  # Additional data
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'User Activities'
    
    def __str__(self):
        return f"{self.user.email} - {self.action} - {self.timestamp}"
    
    @classmethod
    def log_activity(cls, user, action, description, metadata=None):
        """
        Helper method to log user activities
        """
        return cls.objects.create(
            user=user,
            action=action,
            description=description,
            metadata=metadata
        )

class Segment(models.Model):
    """
    Model to create audience segments based on conditions
    """
    CONDITION_TYPES = [
        ('all', 'Match All Conditions'),
        ('any', 'Match Any Condition'),
    ]
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='segments')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    condition_type = models.CharField(max_length=10, choices=CONDITION_TYPES, default='all')
    conditions = models.JSONField(default=dict, help_text="JSON structure of filter conditions")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def apply_segment(self, subscribers_queryset):
        """
        Apply segment filters to a queryset of subscribers
        """
        if not self.conditions:
            return subscribers_queryset
        
        conditions = self.conditions.get('conditions', [])
        if not conditions:
            return subscribers_queryset
        
        # Start with all or filter based on condition type
        filtered_queryset = subscribers_queryset
        
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if not all([field, operator]):
                continue
                
            # Handle different field types
            if field in ['first_name', 'last_name', 'email', 'country', 'city', 'state', 'gender']:
                # Standard fields
                if operator == 'equals':
                    kwargs = {field: value}
                elif operator == 'contains':
                    kwargs = {f"{field}__icontains": value}
                elif operator == 'starts_with':
                    kwargs = {f"{field}__istartswith": value}
                elif operator == 'ends_with':
                    kwargs = {f"{field}__iendswith": value}
                else:
                    continue
                    
                if self.condition_type == 'any':
                    filtered_queryset = filtered_queryset | subscribers_queryset.filter(**kwargs)
                else:
                    filtered_queryset = filtered_queryset.filter(**kwargs)
            
            elif field == 'age':
                # Numeric comparison
                try:
                    val = int(value)
                    if operator == 'equals':
                        kwargs = {'age': val}
                    elif operator == 'greater_than':
                        kwargs = {'age__gt': val}
                    elif operator == 'less_than':
                        kwargs = {'age__lt': val}
                    elif operator == 'between':
                        range_values = value.split(',')
                        if len(range_values) == 2:
                            min_val = int(range_values[0])
                            max_val = int(range_values[1])
                            kwargs = {'age__range': (min_val, max_val)}
                        else:
                            continue
                    else:
                        continue
                        
                    if self.condition_type == 'any':
                        filtered_queryset = filtered_queryset | subscribers_queryset.filter(**kwargs)
                    else:
                        filtered_queryset = filtered_queryset.filter(**kwargs)
                except (ValueError, TypeError):
                    continue
            
            elif field == 'custom_field':
                # Custom field filtering is more complex and might require custom logic
                field_name = condition.get('field_name')
                if not field_name:
                    continue
                
                # For custom fields, we need to filter using a more complex approach
                # This is a simplified version and might need adjustment based on your database
                if operator == 'equals':
                    # Convert the search to a JSON contains operation
                    json_condition = {f"custom_fields__{field_name}": value}
                    
                    if self.condition_type == 'any':
                        filtered_queryset = filtered_queryset | subscribers_queryset.filter(**json_condition)
                    else:
                        filtered_queryset = filtered_queryset.filter(**json_condition)
        
        return filtered_queryset

class ABTestCampaign(models.Model):
    """
    Model for A/B testing campaigns
    """
    TEST_TYPES = [
        ('subject', 'Subject Line'),
        ('content', 'Email Content'),
        ('sender', 'Sender Name/Email'),
        ('time', 'Send Time'),
    ]
    
    STATUS_CHOICES = [
        ('setup', 'Setup'),
        ('running', 'Running'),
        ('complete', 'Complete'),
        ('cancelled', 'Cancelled'),
    ]
    
    WINNER_CRITERIA = [
        ('open_rate', 'Open Rate'),
        ('click_rate', 'Click Rate'),
        ('conversion', 'Conversion Rate'),
    ]
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ab_tests')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    test_type = models.CharField(max_length=20, choices=TEST_TYPES)
    sample_size = models.IntegerField(default=20, help_text="Percentage of subscribers to test with")
    winner_criteria = models.CharField(max_length=20, choices=WINNER_CRITERIA, default='open_rate')
    wait_time = models.IntegerField(default=24, help_text="Hours to wait before selecting winner")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='setup')
    start_time = models.DateTimeField(null=True, blank=True)
    winner_selected_time = models.DateTimeField(null=True, blank=True)
    winner_variant = models.ForeignKey('ABTestVariant', null=True, blank=True, on_delete=models.SET_NULL, related_name='won_tests')
    
    lists = models.ManyToManyField(SubscriberList, related_name='ab_tests')
    segments = models.ManyToManyField(Segment, related_name='ab_tests', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'A/B Test Campaign'
        verbose_name_plural = 'A/B Test Campaigns'
    
    def __str__(self):
        return self.name

class ABTestVariant(models.Model):
    """
    Model for A/B test variants
    """
    ab_test = models.ForeignKey(ABTestCampaign, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)  # e.g., "Variant A", "Variant B"
    
    # For subject line tests
    subject = models.CharField(max_length=255, blank=True)
    
    # For content tests
    content = models.TextField(blank=True)
    html_content = models.TextField(blank=True)
    
    # For sender tests
    from_name = models.CharField(max_length=100, blank=True)
    from_email = models.EmailField(blank=True)
    
    # For time tests
    send_time = models.DateTimeField(null=True, blank=True)
    
    # Results
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    open_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.ab_test.name} - {self.name}"
    
    @property
    def open_rate(self):
        if self.delivered_count == 0:
            return 0
        return (self.open_count / self.delivered_count) * 100
    
    @property
    def click_rate(self):
        if self.delivered_count == 0:
            return 0
        return (self.click_count / self.delivered_count) * 100
