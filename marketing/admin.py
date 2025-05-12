from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    SubscriberList, Subscriber, Campaign, EmailTemplate,
    CampaignAnalytics, Link, EmailOpen, LinkClick,
    EmailEvent, Notification, UserActivity
)
from .actions import export_as_csv, export_as_json, export_as_excel

class SubscriberInline(admin.TabularInline):
    model = Subscriber.lists.through
    extra = 0
    verbose_name = "Subscriber"
    verbose_name_plural = "Subscribers"
    classes = ['collapse']

@admin.register(SubscriberList)
class SubscriberListAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'get_subscriber_count', 'created_at', 'updated_at')
    list_filter = ('owner', 'created_at')
    search_fields = ('name', 'owner__email', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'owner', 'description'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    inlines = [SubscriberInline]
    actions = [export_as_csv, export_as_json, export_as_excel]
    
    def get_subscriber_count(self, obj):
        return obj.subscribers.count()
    get_subscriber_count.short_description = 'Subscribers'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _subscriber_count=Count('subscribers', distinct=True)
        )
        return queryset

@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'owner', 'is_active', 'get_list_count', 'created_at')
    list_filter = ('is_active', 'created_at', 'updated_at', 'owner')
    search_fields = ('email', 'first_name', 'last_name', 'country', 'city')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('email', 'owner', 'first_name', 'last_name', 'country', 'city'),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
        ('Subscriber Lists', {
            'fields': ('lists',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['mark_as_active', 'mark_as_inactive', export_as_csv, export_as_json, export_as_excel]
    
    def get_list_count(self, obj):
        return obj.lists.count()
    get_list_count.short_description = 'Lists'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            _list_count=Count('lists', distinct=True)
        )
        return queryset
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} subscribers were marked as active.')
    mark_as_active.short_description = "Mark selected subscribers as active"
    
    def mark_as_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} subscribers were marked as inactive.')
    mark_as_inactive.short_description = "Mark selected subscribers as inactive"

class LinkInline(admin.TabularInline):
    model = Link
    extra = 0
    classes = ['collapse']

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'subject', 'created_at', 'display_html_preview')
    list_filter = ('owner', 'created_at')
    search_fields = ('name', 'subject', 'html_content', 'content')
    readonly_fields = ('created_at', 'updated_at', 'display_html_content')
    fieldsets = (
        (None, {
            'fields': ('name', 'owner', 'subject'),
        }),
        ('Content', {
            'fields': ('display_html_content', 'html_content', 'content'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = [export_as_csv, export_as_json]
    
    def display_html_preview(self, obj):
        if obj.html_content:
            return format_html('<span style="color: green;">HTML Available</span>')
        return format_html('<span style="color: red;">No HTML</span>')
    display_html_preview.short_description = 'HTML Content'
    
    def display_html_content(self, obj):
        if obj.html_content:
            return format_html('<div style="max-width:600px; border:1px solid #ddd; padding:10px;">{}</div>', obj.html_content)
        return format_html('<span style="color: red;">No HTML content available</span>')
    display_html_content.short_description = 'Preview'

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'status', 'get_list_name', 'get_template_name', 'schedule_time', 'created_at')
    list_filter = ('status', 'owner', 'created_at', 'schedule_time')
    search_fields = ('name', 'owner__email', 'subject')
    readonly_fields = ('created_at', 'updated_at', 'get_analytics_link')
    fieldsets = (
        (None, {
            'fields': ('name', 'owner', 'subject', 'from_name', 'from_email'),
        }),
        ('Campaign Setup', {
            'fields': ('status', 'lists', 'template', 'schedule_time'),
        }),
        ('Content', {
            'fields': ('content', 'html_content'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
        }),
        ('Analytics', {
            'fields': ('get_analytics_link',),
            'classes': ('collapse',),
        }),
    )
    inlines = [LinkInline]
    actions = ['mark_as_draft', 'mark_as_scheduled', 'mark_as_sent', 'duplicate_campaign', export_as_csv, export_as_json, export_as_excel]
    
    def get_list_name(self, obj):
        list_names = ", ".join([list.name for list in obj.lists.all()[:3]])
        if obj.lists.count() > 3:
            list_names += f" and {obj.lists.count() - 3} more"
        return list_names or "-"
    get_list_name.short_description = 'Subscriber Lists'
    
    def get_template_name(self, obj):
        if obj.template:
            return obj.template.name
        return "-"
    get_template_name.short_description = 'Email Template'
    
    def get_analytics_link(self, obj):
        if obj.id:
            url = reverse('admin:marketing_campaignanalytics_changelist') + f'?campaign__id__exact={obj.id}'
            return format_html('<a href="{}">View Campaign Analytics</a>', url)
        return "Save campaign first to view analytics"
    get_analytics_link.short_description = 'Campaign Analytics'
    
    def mark_as_draft(self, request, queryset):
        updated = queryset.update(status='draft')
        self.message_user(request, f'{updated} campaigns were marked as draft.')
    mark_as_draft.short_description = "Mark selected campaigns as draft"
    
    def mark_as_scheduled(self, request, queryset):
        updated = queryset.update(status='scheduled')
        self.message_user(request, f'{updated} campaigns were marked as scheduled.')
    mark_as_scheduled.short_description = "Mark selected campaigns as scheduled"
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.update(status='sent')
        self.message_user(request, f'{updated} campaigns were marked as sent.')
    mark_as_sent.short_description = "Mark selected campaigns as sent"
    
    def duplicate_campaign(self, request, queryset):
        for campaign in queryset:
            campaign.pk = None
            campaign.name = f"Copy of {campaign.name}"
            campaign.status = 'draft'
            campaign.save()
        self.message_user(request, f'{queryset.count()} campaigns were duplicated.')
    duplicate_campaign.short_description = "Duplicate selected campaigns"

class EmailOpenInline(admin.TabularInline):
    model = EmailOpen
    extra = 0
    readonly_fields = ('subscriber', 'timestamp', 'ip_address', 'user_agent')
    classes = ['collapse']

class LinkClickInline(admin.TabularInline):
    model = LinkClick
    extra = 0
    readonly_fields = ('subscriber', 'link', 'timestamp', 'ip_address', 'user_agent')
    classes = ['collapse']

@admin.register(CampaignAnalytics)
class CampaignAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'sent_count', 'open_count', 'click_count', 'bounce_count', 'unsubscribe_count')
    list_filter = ('campaign__status', 'campaign__owner')
    search_fields = ('campaign__name', 'campaign__subject')
    readonly_fields = ('campaign', 'sent_count', 'open_count', 'click_count', 'bounce_count', 'unsubscribe_count', 'open_rate', 'click_rate', 'last_updated')
    fieldsets = (
        (None, {
            'fields': ('campaign',),
        }),
        ('Email Metrics', {
            'fields': ('sent_count', 'open_count', 'open_rate'),
        }),
        ('Engagement Metrics', {
            'fields': ('click_count', 'click_rate'),
        }),
        ('Negative Metrics', {
            'fields': ('bounce_count', 'unsubscribe_count'),
        }),
        ('Timestamps', {
            'fields': ('last_updated',),
            'classes': ('collapse',),
        }),
    )
    inlines = [EmailOpenInline]
    actions = [export_as_csv, export_as_json, export_as_excel]
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ('url', 'campaign', 'click_count')
    list_filter = ('campaign',)
    search_fields = ('url', 'campaign__name')
    readonly_fields = ('click_count',)
    actions = [export_as_csv, export_as_json]

@admin.register(EmailOpen)
class EmailOpenAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'campaign_analytics', 'timestamp', 'ip_address')
    list_filter = ('timestamp', 'campaign_analytics__campaign')
    search_fields = ('subscriber__email', 'ip_address', 'user_agent')
    readonly_fields = ('subscriber', 'campaign_analytics', 'timestamp', 'ip_address', 'user_agent')
    date_hierarchy = 'timestamp'
    actions = [export_as_csv, export_as_json, export_as_excel]

@admin.register(LinkClick)
class LinkClickAdmin(admin.ModelAdmin):
    list_display = ('subscriber', 'link', 'timestamp', 'ip_address')
    list_filter = ('timestamp', 'link__campaign')
    search_fields = ('subscriber__email', 'link__url', 'ip_address', 'user_agent')
    readonly_fields = ('subscriber', 'link', 'timestamp', 'ip_address', 'user_agent')
    date_hierarchy = 'timestamp'
    actions = [export_as_csv, export_as_json, export_as_excel]

@admin.register(EmailEvent)
class EmailEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'campaign', 'subscriber', 'timestamp')
    list_filter = ('event_type', 'timestamp', 'campaign')
    search_fields = ('campaign__name', 'subscriber__email')
    readonly_fields = ('event_type', 'campaign', 'subscriber', 'timestamp', 'metadata')
    date_hierarchy = 'timestamp'
    fieldsets = (
        (None, {
            'fields': ('event_type', 'campaign', 'subscriber'),
        }),
        ('Event Data', {
            'fields': ('metadata',),
        }),
        ('Event Details', {
            'fields': ('timestamp',),
        }),
    )
    actions = [export_as_csv, export_as_json, export_as_excel]

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'message', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__email', 'message')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('user', 'notification_type', 'message', 'is_read'),
        }),
        ('Related Object', {
            'fields': ('related_object_type', 'related_object_id'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
        }),
    )
    actions = ['mark_as_read', 'mark_as_unread', export_as_csv, export_as_json]
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications were marked as read.')
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} notifications were marked as unread.')
    mark_as_unread.short_description = "Mark selected notifications as unread"

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'get_details')
    list_filter = ('action', 'timestamp', 'user')
    search_fields = ('user__email', 'action', 'description')
    date_hierarchy = 'timestamp'
    readonly_fields = ('user', 'action', 'timestamp', 'description', 'metadata')
    actions = [export_as_csv, export_as_json]
    
    def get_details(self, obj):
        if obj.description:
            return obj.description
        return '-'
    get_details.short_description = 'Details'
