from django.contrib import admin
from .models import (
    Subscriber, 
    SubscriberList, 
    EmailTemplate, 
    Campaign, 
    CampaignAnalytics, 
    EmailEvent,
    Notification,
    UserActivity
)

class SubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'owner', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'owner__email')
    list_per_page = 50

class SubscriberListAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'subscriber_count', 'created_at')
    search_fields = ('name', 'owner__email')
    list_filter = ('created_at',)

class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'owner', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'subject', 'owner__email')

class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'status', 'owner', 'created_at', 'schedule_time', 'sent_time')
    list_filter = ('status', 'created_at', 'schedule_time', 'sent_time')
    search_fields = ('name', 'subject', 'owner__email')
    prepopulated_fields = {'slug': ('name',)}

class CampaignAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'sent_count', 'delivered_count', 'open_count', 'click_count', 'last_updated')
    search_fields = ('campaign__name',)

class EmailEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'campaign', 'subscriber', 'timestamp')
    list_filter = ('event_type', 'timestamp')
    search_fields = ('campaign__name', 'subscriber__email')

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'message', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__email', 'message')
    list_per_page = 50

class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'description', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__email', 'description')
    list_per_page = 50

# Register the models
admin.site.register(Subscriber, SubscriberAdmin)
admin.site.register(SubscriberList, SubscriberListAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(Campaign, CampaignAdmin)
admin.site.register(CampaignAnalytics, CampaignAnalyticsAdmin)
admin.site.register(EmailEvent, EmailEventAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
