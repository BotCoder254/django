from django.urls import path
from . import views

urlpatterns = [
    # Landing page and public routes
    path('', views.landing_page, name='home'),
    path('features/', views.features, name='features'),
    path('pricing/', views.pricing, name='pricing'),
    path('contact/', views.contact, name='contact'),
    
    # Dashboard and authenticated routes
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Notifications
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/mark-read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/mark-read/<int:pk>/', views.mark_notification_read, name='mark_notification_read'),
    
    # API endpoints
    path('api/notifications/', views.get_notifications, name='api_notifications'),
    
    # Email Editor
    path('email-editor/', views.email_editor, name='email_editor'),
    path('email-editor/<int:template_id>/', views.email_editor, name='email_editor_template'),
    path('api/save-email-template/', views.save_email_template, name='save_email_template'),
    
    # A/B Testing
    path('ab-tests/create/', views.create_ab_test, name='create_ab_test'),
    path('ab-tests/<int:pk>/', views.ab_test_detail, name='ab_test_detail'),
    path('ab-tests/<int:pk>/edit/', views.edit_ab_test, name='edit_ab_test'),
    path('ab-tests/<int:pk>/start/', views.start_ab_test, name='start_ab_test'),
    path('ab-tests/<int:pk>/cancel/', views.cancel_ab_test, name='cancel_ab_test'),
    
    # Segments
    path('segments/', views.segment_list, name='segment_list'),
    path('segments/create/', views.create_segment, name='create_segment'),
    path('segments/<int:pk>/edit/', views.edit_segment, name='edit_segment'),
    path('segments/<int:pk>/delete/', views.delete_segment, name='delete_segment'),
    
    # Subscribers management
    path('subscribers/', views.subscriber_list, name='subscriber_list'),
    path('subscribers/add/', views.add_subscriber, name='add_subscriber'),
    path('subscribers/<int:pk>/edit/', views.edit_subscriber, name='edit_subscriber'),
    path('subscribers/<int:pk>/delete/', views.delete_subscriber, name='delete_subscriber'),
    path('subscribers/import/', views.import_subscribers, name='import_subscribers'),
    
    # Subscriber lists
    path('subscriber-lists/', views.subscriber_lists, name='subscriber_lists'),
    path('subscriber-lists/add/', views.add_subscriber_list, name='add_subscriber_list'),
    path('subscriber-lists/<int:pk>/', views.subscriber_list_detail, name='subscriber_list_detail'),
    path('subscriber-lists/<int:pk>/edit/', views.edit_subscriber_list, name='edit_subscriber_list'),
    path('subscriber-lists/<int:pk>/delete/', views.delete_subscriber_list, name='delete_subscriber_list'),
    
    # Email templates
    path('templates/', views.email_templates, name='email_templates'),
    path('templates/add/', views.add_email_template, name='add_email_template'),
    path('templates/<int:pk>/', views.email_template_detail, name='email_template_detail'),
    path('templates/<int:pk>/edit/', views.edit_email_template, name='edit_email_template'),
    path('templates/<int:pk>/delete/', views.delete_email_template, name='delete_email_template'),
    
    # Campaigns
    path('campaigns/', views.campaigns, name='campaigns'),
    path('campaigns/add/', views.add_campaign, name='add_campaign'),
    path('campaigns/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<int:pk>/edit/', views.edit_campaign, name='edit_campaign'),
    path('campaigns/<int:pk>/delete/', views.delete_campaign, name='delete_campaign'),
    path('campaigns/<int:pk>/schedule/', views.schedule_campaign, name='schedule_campaign'),
    path('campaigns/<int:pk>/send/', views.send_campaign, name='send_campaign'),
    path('campaigns/<int:pk>/analytics/', views.campaign_analytics, name='campaign_analytics'),
] 