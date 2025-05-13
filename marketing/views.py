from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Avg, F, Q
from django.http import JsonResponse, HttpResponse
from django.core.mail import send_mail, EmailMultiAlternatives, EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.urls import reverse
from django.conf import settings
from django.utils.timesince import timesince

import json
import uuid
import random
import string
import datetime
import smtplib
import os
from datetime import timedelta

from .models import (
    Subscriber, 
    SubscriberList, 
    EmailTemplate, 
    Campaign, 
    CampaignAnalytics, 
    EmailEvent,
    Notification,
    UserActivity,
    ABTestCampaign,
    ABTestVariant,
    Segment,
    Automation,
    AutomationStep
)
from .forms import (
    SubscriberForm,
    SubscriberImportForm,
    SubscriberListForm,
    EmailTemplateForm,
    CampaignForm,
    CampaignScheduleForm,
    ContactForm
)
from users.models import SmtpSettings
from .utils import send_email_with_settings

def get_client_ip(request):
    """
    Get the client IP address from the request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# Health check endpoint for monitoring
def health_check(request):
    """
    Health check endpoint for deployment monitoring
    """
    return JsonResponse({"status": "healthy", "timestamp": timezone.now().isoformat()})

# Public views for landing page and marketing pages
def landing_page(request):
    """
    Landing page view
    """
    return render(request, 'marketing/landing_page.html')

def features(request):
    """
    Features page view
    """
    return render(request, 'marketing/features.html')

def pricing(request):
    """
    Pricing page view
    """
    return render(request, 'marketing/pricing.html')

def contact(request):
    """
    Contact page view
    """
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            # Format message with sender info
            formatted_message = f"Name: {name}\nEmail: {email}\n\n{message}"
            
            # Get first admin user as recipient
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()
            
            if admin_user:
                # Send the contact email using utility
                send_email_with_settings(
                    user=admin_user,
                    subject=f"Contact Form: {subject}",
                    message=formatted_message,
                    to_emails=settings.DEFAULT_FROM_EMAIL,
                    headers={'Reply-To': email}
                )
            else:
                # Fallback to direct send_mail if no admin user exists
                send_mail(
                    f"Contact Form: {subject}",
                    formatted_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.DEFAULT_FROM_EMAIL],  # Send to admin email
                    fail_silently=False,
                )
            
            messages.success(request, 'Your message has been sent. We will get back to you soon!')
            return redirect('contact')
    else:
        form = ContactForm()
    
    return render(request, 'marketing/contact.html', {'form': form})

@login_required
def ab_testing(request):
    """
    View to display all A/B tests
    """
    # Get all A/B tests for the current user
    ab_tests = ABTestCampaign.objects.filter(owner=request.user).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        ab_tests = ab_tests.filter(name__icontains=search_query)
    
    # Status filter
    status_filter = request.GET.get('status', '')
    if status_filter and status_filter != 'all':
        ab_tests = ab_tests.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(ab_tests, 10)  # Show 10 tests per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': ab_tests.count(),
    }
    
    return render(request, 'marketing/ab_testing.html', context)

# Dashboard view
@login_required
def dashboard(request):
    """
    Dashboard view showing analytics and recent activities
    """
    # Get date range filters if provided
    today = timezone.now().date()
    default_start_date = today - timedelta(days=30)
    
    start_date = request.GET.get('start_date', default_start_date.isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    
    try:
        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
    except ValueError:
        start_date = default_start_date
        end_date = today
    
    # Create timezone-aware datetime objects for filtering
    start_datetime = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
    end_datetime = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))
    
    # Previous period for growth calculation
    period_days = (end_date - start_date).days
    prev_start_date = start_date - timedelta(days=period_days)
    prev_end_date = start_date - timedelta(days=1)
    
    # Create timezone-aware datetime objects for prev period
    prev_start_datetime = timezone.make_aware(datetime.datetime.combine(prev_start_date, datetime.time.min))
    prev_end_datetime = timezone.make_aware(datetime.datetime.combine(prev_end_date, datetime.time.max))
    
    # Get counts for different entities
    subscriber_count = Subscriber.objects.filter(owner=request.user).count()
    list_count = SubscriberList.objects.filter(owner=request.user).count()
    campaign_count = Campaign.objects.filter(owner=request.user).count()
    template_count = EmailTemplate.objects.filter(owner=request.user).count()
    
    # Calculate growth rates
    prev_subscriber_count = Subscriber.objects.filter(
        owner=request.user, 
        created_at__gte=prev_start_date,
        created_at__lt=start_date
    ).count()
    current_subscriber_count = Subscriber.objects.filter(
        owner=request.user, 
        created_at__gte=start_date,
        created_at__lt=end_date
    ).count()
    
    if prev_subscriber_count > 0:
        subscriber_growth = ((current_subscriber_count - prev_subscriber_count) / prev_subscriber_count) * 100
    else:
        subscriber_growth = 100 if current_subscriber_count > 0 else 0
        
    prev_campaign_count = Campaign.objects.filter(
        owner=request.user, 
        created_at__gte=prev_start_date,
        created_at__lt=start_date
    ).count()
    current_campaign_count = Campaign.objects.filter(
        owner=request.user, 
        created_at__gte=start_date,
        created_at__lt=end_date
    ).count()
    
    if prev_campaign_count > 0:
        campaign_growth = ((current_campaign_count - prev_campaign_count) / prev_campaign_count) * 100
    else:
        campaign_growth = 100 if current_campaign_count > 0 else 0
    
    # Get recent campaigns
    recent_campaigns = Campaign.objects.filter(owner=request.user).order_by('-created_at')[:5]
    
    # Get analytics data for charts
    campaign_analytics = CampaignAnalytics.objects.filter(
        campaign__owner=request.user,
        campaign__sent_time__gte=start_datetime,
        campaign__sent_time__lt=end_datetime
    )
    
    # Calculate avg open and click rates
    if campaign_analytics.exists():
        avg_open_rate = campaign_analytics.aggregate(
            avg_rate=Avg(F('open_count') * 100.0 / F('delivered_count'))
        )['avg_rate'] or 0
        
        avg_click_rate = campaign_analytics.aggregate(
            avg_rate=Avg(F('click_count') * 100.0 / F('delivered_count'))
        )['avg_rate'] or 0
    else:
        avg_open_rate = 0
        avg_click_rate = 0
    
    # Calculate open rate and click rate changes
    prev_campaign_analytics = CampaignAnalytics.objects.filter(
        campaign__owner=request.user,
        campaign__sent_time__gte=prev_start_datetime,
        campaign__sent_time__lt=start_datetime
    )
    
    if prev_campaign_analytics.exists():
        prev_avg_open_rate = prev_campaign_analytics.aggregate(
            avg_rate=Avg(F('open_count') * 100.0 / F('delivered_count'))
        )['avg_rate'] or 0
        
        if prev_avg_open_rate > 0:
            open_rate_change = ((avg_open_rate - prev_avg_open_rate) / prev_avg_open_rate) * 100
        else:
            open_rate_change = 100 if avg_open_rate > 0 else 0
            
        prev_avg_click_rate = prev_campaign_analytics.aggregate(
            avg_rate=Avg(F('click_count') * 100.0 / F('delivered_count'))
        )['avg_rate'] or 0
        
        if prev_avg_click_rate > 0:
            click_rate_change = ((avg_click_rate - prev_avg_click_rate) / prev_avg_click_rate) * 100
        else:
            click_rate_change = 100 if avg_click_rate > 0 else 0
    else:
        open_rate_change = 0
        click_rate_change = 0
    
    # Prepare chart data
    chart_start_date = start_date
    chart_end_date = end_date
    
    # Generate date range for chart (maximum 30 points to avoid cluttering)
    date_range = (chart_end_date - chart_start_date).days + 1
    step = max(1, date_range // 30)
    
    chart_dates = []
    open_rates = []
    click_rates = []
    
    current_date = chart_start_date
    while current_date <= chart_end_date:
        chart_dates.append(current_date.strftime('%Y-%m-%d'))
        
        # Get campaigns sent on this date
        day_campaigns = Campaign.objects.filter(
            owner=request.user,
            sent_time__date=current_date,
            status='sent'
        )
        
        if day_campaigns.exists():
            day_analytics = CampaignAnalytics.objects.filter(campaign__in=day_campaigns)
            
            # Calculate daily rates
            day_open_rate = day_analytics.aggregate(
                avg_rate=Avg(F('open_count') * 100.0 / F('delivered_count'))
            )['avg_rate'] or 0
            
            day_click_rate = day_analytics.aggregate(
                avg_rate=Avg(F('click_count') * 100.0 / F('delivered_count'))
            )['avg_rate'] or 0
        else:
            day_open_rate = 0
            day_click_rate = 0
        
        open_rates.append(round(day_open_rate, 1))
        click_rates.append(round(day_click_rate, 1))
        
        current_date += timedelta(days=step)
    
    # Convert chart data to JSON for JavaScript
    chart_dates_json = json.dumps(chart_dates)
    open_rates_json = json.dumps(open_rates)
    click_rates_json = json.dumps(click_rates)
    
    # Get user's subscription status
    has_subscription = request.user.subscription_plan != 'free'
    
    # Get unread notifications count
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
    
    # Get recent notifications
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Get recent activity with pagination (3 items per page)
    activities_list = UserActivity.objects.filter(user=request.user).order_by('-timestamp')
    activities_paginator = Paginator(activities_list, 3)
    activities_page_number = request.GET.get('activities_page', 1)
    recent_activities = activities_paginator.get_page(activities_page_number)
    
    context = {
        'subscriber_count': subscriber_count,
        'list_count': list_count,
        'campaign_count': campaign_count,
        'template_count': template_count,
        'subscriber_growth': round(subscriber_growth, 1),
        'campaign_growth': round(campaign_growth, 1),
        'avg_open_rate': avg_open_rate,
        'avg_click_rate': avg_click_rate,
        'open_rate_change': round(open_rate_change, 1),
        'click_rate_change': round(click_rate_change, 1),
        'recent_campaigns': recent_campaigns,
        'chart_dates': chart_dates_json,
        'open_rates': open_rates_json,
        'click_rates': click_rates_json,
        'user': request.user,
        'has_subscription': has_subscription,
        'unread_notifications_count': unread_notifications_count,
        'notifications': notifications,
        'recent_activities': recent_activities,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
    }
    
    return render(request, 'marketing/dashboard.html', context)

# Subscriber views
@login_required
def subscriber_list(request):
    """
    List all subscribers
    """
    subscribers = Subscriber.objects.filter(owner=request.user).order_by('-created_at')
    
    # Filter by list if provided
    list_id = request.GET.get('list')
    if list_id:
        subscribers = subscribers.filter(lists__id=list_id)
    
    # Search functionality
    search = request.GET.get('search')
    if search:
        subscribers = subscribers.filter(
            email__icontains=search
        ) | subscribers.filter(
            first_name__icontains=search
        ) | subscribers.filter(
            last_name__icontains=search
        )
    
    # Pagination
    paginator = Paginator(subscribers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all subscriber lists for filter dropdown
    subscriber_lists = SubscriberList.objects.filter(owner=request.user)
    
    context = {
        'page_obj': page_obj,
        'subscriber_lists': subscriber_lists,
        'search': search,
        'list_id': list_id,
    }
    
    return render(request, 'marketing/subscriber_list.html', context)

@login_required
def add_subscriber(request):
    """
    Add a new subscriber
    """
    if request.method == 'POST':
        form = SubscriberForm(request.POST)
        if form.is_valid():
            subscriber = form.save(commit=False)
            subscriber.owner = request.user
            
            # Check if subscriber already exists
            if Subscriber.objects.filter(owner=request.user, email=subscriber.email).exists():
                messages.error(request, f'Subscriber with email {subscriber.email} already exists.')
                return render(request, 'marketing/add_subscriber.html', {'form': form})
            
            subscriber.save()
            
            # Add to selected lists if provided
            list_ids = request.POST.getlist('lists')
            if list_ids:
                for list_id in list_ids:
                    try:
                        subscriber_list = SubscriberList.objects.get(id=list_id, owner=request.user)
                        subscriber_list.subscribers.add(subscriber)
                    except SubscriberList.DoesNotExist:
                        pass
            
            # Create notification
            Notification.create_notification(
                user=request.user,
                message=f"New subscriber added: {subscriber.email}",
                notification_type='subscriber_added',
                related_object=subscriber
            )
            
            # Log activity
            UserActivity.log_activity(
                user=request.user,
                action='subscriber_added',
                description=f"Added new subscriber: {subscriber.email}",
                metadata={'subscriber_id': subscriber.id}
            )
            
            messages.success(request, 'Subscriber added successfully.')
            
            # Check if should add another
            if 'add_another' in request.POST:
                return redirect('add_subscriber')
            
            return redirect('subscriber_list')
    else:
        form = SubscriberForm()
    
    # Get all subscriber lists for the user
    subscriber_lists = SubscriberList.objects.filter(owner=request.user)
    
    return render(request, 'marketing/add_subscriber.html', {
        'form': form,
        'subscriber_lists': subscriber_lists
    })

@login_required
def edit_subscriber(request, pk):
    """
    Edit a subscriber
    """
    subscriber = get_object_or_404(Subscriber, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = SubscriberForm(request.POST, instance=subscriber)
        if form.is_valid():
            form.save()
            
            # Update lists
            list_ids = request.POST.getlist('lists')
            subscriber_lists = SubscriberList.objects.filter(owner=request.user)
            
            # Remove from all lists first
            for subscriber_list in subscriber_lists:
                subscriber_list.subscribers.remove(subscriber)
            
            # Add to selected lists
            for list_id in list_ids:
                try:
                    subscriber_list = SubscriberList.objects.get(id=list_id, owner=request.user)
                    subscriber_list.subscribers.add(subscriber)
                except SubscriberList.DoesNotExist:
                    pass
            
            messages.success(request, 'Subscriber updated successfully.')
            return redirect('subscriber_list')
    else:
        form = SubscriberForm(instance=subscriber)
    
    # Get all subscriber lists for the user
    subscriber_lists = SubscriberList.objects.filter(owner=request.user)
    
    # Get lists this subscriber belongs to
    subscriber_list_ids = subscriber.lists.values_list('id', flat=True)
    
    return render(request, 'marketing/edit_subscriber.html', {
        'form': form,
        'subscriber': subscriber,
        'subscriber_lists': subscriber_lists,
        'subscriber_list_ids': subscriber_list_ids
    })

@login_required
def delete_subscriber(request, pk):
    """
    Delete a subscriber
    """
    subscriber = get_object_or_404(Subscriber, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        subscriber.delete()
        messages.success(request, 'Subscriber deleted successfully.')
        return redirect('subscriber_list')
    
    return render(request, 'marketing/delete_subscriber.html', {'subscriber': subscriber})

@login_required
def import_subscribers(request, list_id=None):
    """
    Import subscribers from a CSV file
    """
    # Get the list if list_id is provided
    subscriber_list = None
    if list_id:
        subscriber_list = get_object_or_404(SubscriberList, pk=list_id, owner=request.user)
    
    if request.method == 'POST':
        form = SubscriberImportForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Process the CSV file
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            # Count new and existing subscribers
            new_subscribers = 0
            existing_subscribers = 0
            
            for row in reader:
                email = row.get('email', '').strip()
                if not email:
                    continue
                
                # Check if subscriber already exists
                subscriber, created = Subscriber.objects.get_or_create(
                    owner=request.user,
                    email=email,
                    defaults={
                        'first_name': row.get('first_name', '').strip(),
                        'last_name': row.get('last_name', '').strip(),
                        'is_active': True
                    }
                )
                
                if created:
                    new_subscribers += 1
                else:
                    existing_subscribers += 1
                
                # Add to the selected list if provided
                if subscriber_list:
                    subscriber_list.subscribers.add(subscriber)
            
            # Create notification
            if subscriber_list:
                message = f"Imported {new_subscribers} new subscribers to list: {subscriber_list.name}"
            else:
                message = f"Imported {new_subscribers} new subscribers"
                
            Notification.create_notification(
                user=request.user,
                message=message,
                notification_type='subscriber_import'
            )
            
            # Log activity
            UserActivity.log_activity(
                user=request.user,
                action='subscriber_import',
                description=message,
                metadata={
                    'imported': new_subscribers,
                    'existing': existing_subscribers,
                    'list_id': subscriber_list.id if subscriber_list else None
                }
            )
            
            messages.success(
                request, 
                f'Successfully processed CSV file. Imported: {new_subscribers}, Existing: {existing_subscribers}'
            )
            
            if subscriber_list:
                return redirect('subscriber_list_detail', pk=subscriber_list.id)
            else:
                return redirect('subscribers')
    else:
        form = SubscriberImportForm(user=request.user)
    
    return render(request, 'marketing/import_subscribers.html', {
        'form': form,
        'subscriber_list': subscriber_list
    })

# Subscriber list views
@login_required
def subscriber_lists(request):
    """
    List all subscriber lists
    """
    lists = SubscriberList.objects.filter(owner=request.user).order_by('name')
    return render(request, 'marketing/subscriber_lists.html', {'lists': lists})

@login_required
def add_subscriber_list(request):
    """
    Add a new subscriber list
    """
    if request.method == 'POST':
        form = SubscriberListForm(request.POST)
        if form.is_valid():
            subscriber_list = form.save(commit=False)
            subscriber_list.owner = request.user
            subscriber_list.save()
            
            # Create notification
            Notification.create_notification(
                user=request.user,
                message=f"New list created: {subscriber_list.name}",
                notification_type='list_created',
                related_object=subscriber_list
            )
            
            # Log activity
            UserActivity.log_activity(
                user=request.user,
                action='list_created',
                description=f"Created new list: {subscriber_list.name}",
                metadata={'list_id': subscriber_list.id}
            )
            
            messages.success(request, 'Subscriber list created successfully.')
            return redirect('subscriber_lists')
    else:
        form = SubscriberListForm()
    
    return render(request, 'marketing/add_subscriber_list.html', {'form': form})

@login_required
def subscriber_list_detail(request, pk):
    """
    View details of a subscriber list
    """
    subscriber_list = get_object_or_404(SubscriberList, pk=pk, owner=request.user)
    subscribers = subscriber_list.subscribers.all()
    
    # Get active subscribers count
    active_subscribers = subscriber_list.subscribers.filter(is_active=True).count()
    
    # Pagination
    paginator = Paginator(subscribers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'marketing/subscriber_list_detail.html', {
        'list': subscriber_list,
        'page_obj': page_obj,
        'subscribers': subscribers,
        'active_subscribers': active_subscribers
    })

@login_required
def edit_subscriber_list(request, pk):
    """
    Edit a subscriber list
    """
    subscriber_list = get_object_or_404(SubscriberList, pk=pk, owner=request.user)
    
    # Get count of active subscribers
    active_subscribers = subscriber_list.subscribers.filter(is_active=True).count()
    
    if request.method == 'POST':
        form = SubscriberListForm(request.POST, instance=subscriber_list)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subscriber list updated successfully.')
            return redirect('subscriber_lists')
    else:
        form = SubscriberListForm(instance=subscriber_list)
    
    return render(request, 'marketing/edit_subscriber_list.html', {
        'form': form,
        'list': subscriber_list,
        'active_subscribers': active_subscribers
    })

@login_required
def delete_subscriber_list(request, pk):
    """
    Delete a subscriber list
    """
    subscriber_list = get_object_or_404(SubscriberList, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        subscriber_list.delete()
        messages.success(request, 'Subscriber list deleted successfully.')
        return redirect('subscriber_lists')
    
    return render(request, 'marketing/delete_subscriber_list.html', {'list': subscriber_list})

# Email template views
@login_required
def email_templates(request):
    """
    List all email templates
    """
    templates = EmailTemplate.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'marketing/email_templates.html', {'templates': templates})

@login_required
def add_email_template(request):
    """
    Add a new email template
    """
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.owner = request.user
            template.save()
            
            # Create notification
            Notification.create_notification(
                user=request.user,
                message=f"New template created: {template.name}",
                notification_type='system',
                related_object=template
            )
            
            # Log activity
            UserActivity.log_activity(
                user=request.user,
                action='template_created',
                description=f"Created new template: {template.name}",
                metadata={'template_id': template.id}
            )
            
            messages.success(request, 'Email template created successfully.')
            return redirect('email_templates')
    else:
        form = EmailTemplateForm()
    
    return render(request, 'marketing/add_email_template.html', {'form': form})

@login_required
def email_template_detail(request, pk):
    """
    View details of an email template
    """
    template = get_object_or_404(EmailTemplate, pk=pk, owner=request.user)
    return render(request, 'marketing/email_template_detail.html', {'template': template})

@login_required
def edit_email_template(request, pk):
    """
    Edit an email template
    """
    template = get_object_or_404(EmailTemplate, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = EmailTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, 'Email template updated successfully.')
            return redirect('email_templates')
    else:
        form = EmailTemplateForm(instance=template)
    
    return render(request, 'marketing/edit_email_template.html', {
        'form': form,
        'template': template
    })

@login_required
def delete_email_template(request, pk):
    """
    Delete an email template
    """
    template = get_object_or_404(EmailTemplate, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'Email template deleted successfully.')
        return redirect('email_templates')
    
    return render(request, 'marketing/delete_email_template.html', {'template': template})

# Campaign views
@login_required
def campaigns(request):
    """
    List all campaigns
    """
    campaigns = Campaign.objects.filter(owner=request.user).order_by('-created_at')
    return render(request, 'marketing/campaigns.html', {'campaigns': campaigns})

@login_required
def add_campaign(request):
    """
    Add a new campaign
    """
    if request.method == 'POST':
        form = CampaignForm(request.POST, user=request.user)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.owner = request.user
            campaign.save()
            
            # Save many-to-many relationships
            form.save_m2m()
            
            # Create analytics record
            CampaignAnalytics.objects.create(campaign=campaign)
            
            # Create notification
            Notification.create_notification(
                user=request.user,
                message=f"New campaign created: {campaign.name}",
                notification_type='system',
                related_object=campaign
            )
            
            # Log activity
            UserActivity.log_activity(
                user=request.user,
                action='campaign_created',
                description=f"Created new campaign: {campaign.name}",
                metadata={'campaign_id': campaign.id}
            )
            
            messages.success(request, 'Campaign created successfully.')
            return redirect('campaigns')
    else:
        form = CampaignForm(user=request.user)
    
    return render(request, 'marketing/add_campaign.html', {'form': form})

@login_required
def campaign_detail(request, pk):
    """
    View details of a campaign
    """
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    
    # Get analytics if available
    try:
        analytics = campaign.analytics
    except CampaignAnalytics.DoesNotExist:
        analytics = CampaignAnalytics.objects.create(campaign=campaign)
    
    # Get subscriber lists
    lists = campaign.lists.all()
    
    # Calculate total subscribers
    subscriber_count = 0
    for subscriber_list in lists:
        subscriber_count += subscriber_list.subscribers.count()
    
    return render(request, 'marketing/campaign_detail.html', {
        'campaign': campaign,
        'analytics': analytics,
        'lists': lists,
        'subscriber_count': subscriber_count
    })

@login_required
def edit_campaign(request, pk):
    """
    Edit a campaign
    """
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    
    # Only allow editing if campaign is in draft status
    if campaign.status != 'draft':
        messages.error(request, 'You can only edit campaigns in draft status.')
        return redirect('campaign_detail', pk=campaign.pk)
    
    if request.method == 'POST':
        form = CampaignForm(request.POST, instance=campaign, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Campaign updated successfully.')
            return redirect('campaign_detail', pk=campaign.pk)
    else:
        form = CampaignForm(instance=campaign, user=request.user)
    
    return render(request, 'marketing/edit_campaign.html', {
        'form': form,
        'campaign': campaign
    })

@login_required
def delete_campaign(request, pk):
    """
    Delete a campaign
    """
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        campaign.delete()
        messages.success(request, 'Campaign deleted successfully.')
        return redirect('campaigns')
    
    return render(request, 'marketing/delete_campaign.html', {'campaign': campaign})

@login_required
def schedule_campaign(request, pk):
    """
    Schedule a campaign for sending
    """
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    
    # Only allow scheduling if campaign is in draft status
    if campaign.status != 'draft':
        messages.error(request, 'You can only schedule campaigns in draft status.')
        return redirect('campaign_detail', pk=campaign.pk)
    
    if request.method == 'POST':
        form = CampaignScheduleForm(request.POST, instance=campaign)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.status = 'scheduled'
            campaign.save()
            
            # Create notification
            Notification.objects.create(
                user=request.user,
                message=f"Campaign scheduled: {campaign.name}",
                notification_type='campaign_scheduled',
                related_object_id=campaign.id,
                related_object_type='campaign'
            )
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action='campaign_scheduled',
                description=f"Scheduled campaign: {campaign.name} for {campaign.schedule_time}",
                metadata={
                    'campaign_id': campaign.id,
                    'schedule_time': campaign.schedule_time.isoformat() if campaign.schedule_time else None
                }
            )
            
            messages.success(request, 'Campaign scheduled successfully.')
            return redirect('campaign_detail', pk=campaign.pk)
    else:
        form = CampaignScheduleForm(instance=campaign)
    
    return render(request, 'marketing/schedule_campaign.html', {
        'form': form,
        'campaign': campaign
    })

@login_required
def send_campaign(request, pk):
    """
    Send campaign to all subscribers in the selected lists
    """
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    
    if campaign.status in ['sent', 'sending']:
        messages.error(request, "This campaign has already been sent or is currently sending.")
        return redirect('campaign_detail', pk=campaign.pk)
    
    # Set campaign as sending
    campaign.status = 'sending'
    campaign.save()
    
    # Log activity
    UserActivity.objects.create(
        user=request.user,
        action='campaign_sent',
        description=f'Campaign "{campaign.name}" sent',
        metadata={'campaign_id': campaign.pk}
    )
    
    try:
        # Get all subscribers from all lists
        all_subscribers = set()
        for email_list in campaign.lists.all():
            subscribers = email_list.subscribers.filter(is_active=True)
            all_subscribers.update(subscribers)
        
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
                    user=request.user,
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
                        metadata={'subscriber_id': subscriber.id, 'campaign_id': campaign.id}
                    )
            except Exception as e:
                # Log error
                print(f"Error sending to {subscriber.email}: {str(e)}")
                continue
        
        # Update campaign status
        campaign.status = 'sent'
        campaign.sent_time = timezone.now()
        campaign.save()
        
        messages.success(request, f"Campaign sent successfully to {sent_count} subscribers.")
    except Exception as e:
        campaign.status = 'draft'
        campaign.save()
        messages.error(request, f"Failed to send campaign: {str(e)}")
    
    return redirect('campaign_detail', pk=campaign.pk)

@login_required
def campaign_analytics(request, pk):
    """
    View detailed analytics for a campaign
    """
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    
    # Get analytics
    try:
        analytics = campaign.analytics
    except CampaignAnalytics.DoesNotExist:
        analytics = CampaignAnalytics.objects.create(campaign=campaign)
    
    # Get events for this campaign
    events = EmailEvent.objects.filter(campaign=campaign).order_by('-timestamp')
    
    # Group events by type for chart data
    event_data = {
        'sent': events.filter(event_type='sent').count(),
        'delivered': events.filter(event_type='delivered').count(),
        'opened': events.filter(event_type='opened').count(),
        'clicked': events.filter(event_type='clicked').count(),
        'bounced': events.filter(event_type='bounced').count(),
        'complained': events.filter(event_type='complained').count(),
        'unsubscribed': events.filter(event_type='unsubscribed').count(),
    }
    
    # Paginate events
    paginator = Paginator(events, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'marketing/campaign_analytics.html', {
        'campaign': campaign,
        'analytics': analytics,
        'event_data': event_data,
        'page_obj': page_obj
    })

# Notification views
@login_required
def notification_list(request):
    """
    List all notifications for a user
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Count unread notifications
    unread_count = notifications.filter(is_read=False).count()
    
    return render(request, 'marketing/notification_list.html', {
        'page_obj': page_obj,
        'unread_count': unread_count
    })

@login_required
def mark_notification_read(request, pk):
    """
    Mark a specific notification as read
    """
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    
    if not notification.is_read:
        notification.is_read = True
        notification.save()
    
    # Check if redirect_url is specified in POST or GET
    redirect_url = request.POST.get('redirect_url') or request.GET.get('redirect_url')
    
    if redirect_url:
        return redirect(redirect_url)
    
    return redirect('notification_list')

@login_required
def mark_notifications_read(request):
    """
    Mark all notifications as read
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    messages.success(request, 'All notifications marked as read.')
    
    # Check if redirect_url is specified
    redirect_url = request.POST.get('redirect_url') or request.GET.get('redirect_url')
    
    if redirect_url:
        return redirect(redirect_url)
    
    return redirect('notification_list')

# API endpoints for notifications (for ajax calls)
@login_required
def get_notifications(request):
    """
    Get recent notifications as JSON
    """
    count = int(request.GET.get('count', 5))
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:count]
    
    data = [{
        'id': notification.id,
        'message': notification.message,
        'notification_type': notification.notification_type,
        'is_read': notification.is_read,
        'created_at': notification.created_at.isoformat(),
        'time_ago': str((timezone.now() - notification.created_at).days) + " days ago"
    } for notification in notifications]
    
    return JsonResponse({
        'notifications': data,
        'unread_count': Notification.objects.filter(user=request.user, is_read=False).count()
    })

# Email Editor and Advanced Campaign Management Views
@login_required
def email_editor(request, template_id=None):
    """
    Drag and drop email editor view
    """
    template = None
    if template_id:
        template = get_object_or_404(EmailTemplate, pk=template_id, owner=request.user)
    
    return render(request, 'marketing/email_editor.html', {
        'template': template
    })

@login_required
def save_email_template(request):
    """
    API endpoint to save email templates from the editor
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    try:
        data = json.loads(request.body)
        name = data.get('name')
        subject = data.get('subject')
        description = data.get('description', '')
        html_content = data.get('html_content', '')
        
        if not name or not subject or not html_content:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        # Create or update template
        template_id = data.get('template_id')
        if template_id:
            template = get_object_or_404(EmailTemplate, pk=template_id, owner=request.user)
            template.name = name
            template.subject = subject
            template.html_content = html_content
            template.content = html_content  # Also store as plain text for fallback
        else:
            template = EmailTemplate(
                owner=request.user,
                name=name,
                subject=subject,
                html_content=html_content,
                content=html_content  # Also store as plain text for fallback
            )
        
        template.save()
        
        # Log activity
        UserActivity.log_activity(
            user=request.user,
            action='template_created' if not template_id else 'template_updated',
            description=f"{'Created' if not template_id else 'Updated'} email template: {name}",
            metadata={'template_id': template.id}
        )
        
        return JsonResponse({'success': True, 'template_id': template.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def upload_template_asset(request):
    """
    API endpoint to upload assets for email templates
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'})
    
    files = []
    for key, file in request.FILES.items():
        # Save file to media directory
        file_path = f'template_assets/{request.user.id}/{file.name}'
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Save the file
        with open(full_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Add file info to response
        file_url = f'{settings.MEDIA_URL}{file_path}'
        files.append({
            'src': file_url,
            'name': file.name,
            'type': file.content_type
        })
    
    return JsonResponse({'success': True, 'files': files})

@login_required
def template_preview(request, pk):
    """
    Preview an email template
    """
    template = get_object_or_404(EmailTemplate, pk=pk, owner=request.user)
    return render(request, 'marketing/template_preview.html', {'template': template})

@login_required
def create_ab_test(request):
    """
    Create a new A/B test campaign
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        test_type = request.POST.get('test_type')
        sample_size = request.POST.get('sample_size', 20)
        winner_criteria = request.POST.get('winner_criteria', 'open_rate')
        wait_time = request.POST.get('wait_time', 24)
        list_ids = request.POST.getlist('lists')
        segment_ids = request.POST.getlist('segments')
        
        # Create the A/B test campaign
        ab_test = ABTestCampaign(
            owner=request.user,
            name=name,
            description=description,
            test_type=test_type,
            sample_size=sample_size,
            winner_criteria=winner_criteria,
            wait_time=wait_time,
            status='setup'
        )
        ab_test.save()
        
        # Add selected lists
        for list_id in list_ids:
            try:
                subscriber_list = SubscriberList.objects.get(id=list_id, owner=request.user)
                ab_test.lists.add(subscriber_list)
            except SubscriberList.DoesNotExist:
                pass
        
        # Add selected segments
        for segment_id in segment_ids:
            try:
                segment = Segment.objects.get(id=segment_id, owner=request.user)
                ab_test.segments.add(segment)
            except Segment.DoesNotExist:
                pass
        
        # Create default variants based on test type
        variant_a = ABTestVariant(
            ab_test=ab_test,
            name='Variant A'
        )
        variant_a.save()
        
        variant_b = ABTestVariant(
            ab_test=ab_test,
            name='Variant B'
        )
        variant_b.save()
        
        # Log activity
        UserActivity.log_activity(
            user=request.user,
            action='ab_test_created',
            description=f"Created A/B test: {name}",
            metadata={'ab_test_id': ab_test.id}
        )
        
        return redirect('edit_ab_test', pk=ab_test.id)
    
    # GET request - show form
    subscriber_lists = SubscriberList.objects.filter(owner=request.user)
    segments = Segment.objects.filter(owner=request.user)
    
    return render(request, 'marketing/create_ab_test.html', {
        'subscriber_lists': subscriber_lists,
        'segments': segments,
        'test_types': ABTestCampaign.TEST_TYPES,
        'winner_criteria': ABTestCampaign.WINNER_CRITERIA
    })

@login_required
def edit_ab_test(request, pk):
    """
    Edit an A/B test campaign
    """
    ab_test = get_object_or_404(ABTestCampaign, pk=pk, owner=request.user)
    
    # Only allow editing if the test is in setup status
    if ab_test.status != 'setup':
        messages.error(request, 'This A/B test cannot be edited because it is already running or completed.')
        return redirect('ab_test_detail', pk=ab_test.pk)
    
    variants = ab_test.variants.all()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        sample_size = request.POST.get('sample_size', 20)
        winner_criteria = request.POST.get('winner_criteria', 'open_rate')
        wait_time = request.POST.get('wait_time', 24)
        list_ids = request.POST.getlist('lists')
        segment_ids = request.POST.getlist('segments')
        
        # Update the A/B test campaign
        ab_test.name = name
        ab_test.description = description
        ab_test.sample_size = sample_size
        ab_test.winner_criteria = winner_criteria
        ab_test.wait_time = wait_time
        ab_test.save()
        
        # Update selected lists
        ab_test.lists.clear()
        for list_id in list_ids:
            try:
                subscriber_list = SubscriberList.objects.get(id=list_id, owner=request.user)
                ab_test.lists.add(subscriber_list)
            except SubscriberList.DoesNotExist:
                pass
        
        # Update selected segments
        ab_test.segments.clear()
        for segment_id in segment_ids:
            try:
                segment = Segment.objects.get(id=segment_id, owner=request.user)
                ab_test.segments.add(segment)
            except Segment.DoesNotExist:
                pass
        
        # Update variants based on test type
        for variant in variants:
            variant_prefix = f"variant_{variant.id}_"
            
            if ab_test.test_type == 'subject':
                variant.subject = request.POST.get(f"{variant_prefix}subject", '')
            elif ab_test.test_type == 'content':
                variant.html_content = request.POST.get(f"{variant_prefix}html_content", '')
                variant.content = request.POST.get(f"{variant_prefix}content", '')
            elif ab_test.test_type == 'sender':
                variant.from_name = request.POST.get(f"{variant_prefix}from_name", '')
                variant.from_email = request.POST.get(f"{variant_prefix}from_email", '')
            elif ab_test.test_type == 'time':
                send_time_str = request.POST.get(f"{variant_prefix}send_time", '')
                if send_time_str:
                    try:
                        # Parse datetime from string format and make it timezone-aware
                        naive_dt = datetime.datetime.strptime(send_time_str, '%Y-%m-%dT%H:%M')
                        variant.send_time = timezone.make_aware(naive_dt)
                    except ValueError:
                        pass
            
            variant.save()
        
        messages.success(request, 'A/B test updated successfully.')
        return redirect('ab_test_detail', pk=ab_test.pk)
    
    # GET request - show form with existing data
    subscriber_lists = SubscriberList.objects.filter(owner=request.user)
    segments = Segment.objects.filter(owner=request.user)
    
    selected_list_ids = [list.id for list in ab_test.lists.all()]
    selected_segment_ids = [segment.id for segment in ab_test.segments.all()]
    
    return render(request, 'marketing/edit_ab_test.html', {
        'ab_test': ab_test,
        'variants': variants,
        'subscriber_lists': subscriber_lists,
        'selected_list_ids': selected_list_ids,
        'segments': segments,
        'selected_segment_ids': selected_segment_ids,
        'winner_criteria': ABTestCampaign.WINNER_CRITERIA
    })

@login_required
def ab_test_detail(request, pk):
    """
    View A/B test details and results
    """
    ab_test = get_object_or_404(ABTestCampaign, pk=pk, owner=request.user)
    variants = ab_test.variants.all()
    
    # Calculate total audience size
    total_audience = 0
    for subscriber_list in ab_test.lists.all():
        list_subscribers = subscriber_list.subscribers.filter(is_active=True).count()
        
        # Apply segments if any
        if ab_test.segments.exists():
            for segment in ab_test.segments.all():
                segmented_subscribers = segment.apply_segment(subscriber_list.subscribers.filter(is_active=True)).count()
                list_subscribers = min(list_subscribers, segmented_subscribers)
        
        total_audience += list_subscribers
    
    # Prepare variant data for JavaScript
    variant_data = []
    for variant in variants:
        variant_data.append({
            'name': variant.name,
            'openRate': float(variant.open_rate) if variant.open_rate else 0,
            'clickRate': float(variant.click_rate) if variant.click_rate else 0,
            'conversionRate': 0  # Placeholder for future feature
        })
    
    import json
    
    context = {
        'ab_test': ab_test,
        'variants': variants,
        'total_audience': total_audience,
        'variant_data_json': json.dumps(variant_data)
    }
    
    return render(request, 'marketing/ab_test_detail.html', context)

@login_required
def start_ab_test(request, pk):
    """
    Start an A/B test campaign
    """
    ab_test = get_object_or_404(ABTestCampaign, pk=pk, owner=request.user)
    
    if ab_test.status != 'setup':
        messages.error(request, 'This A/B test cannot be started because it is already running or completed.')
        return redirect('ab_test_detail', pk=ab_test.pk)
    
    # Check if variants are properly configured
    variants = ab_test.variants.all()
    test_ready = True
    
    if ab_test.test_type == 'subject':
        for variant in variants:
            if not variant.subject:
                test_ready = False
                break
    elif ab_test.test_type == 'content':
        for variant in variants:
            if not variant.html_content:
                test_ready = False
                break
    elif ab_test.test_type == 'sender':
        for variant in variants:
            if not variant.from_name or not variant.from_email:
                test_ready = False
                break
    elif ab_test.test_type == 'time':
        for variant in variants:
            if not variant.send_time:
                test_ready = False
                break
    
    if not test_ready:
        messages.error(request, 'All variants must be properly configured before starting the test.')
        return redirect('edit_ab_test', pk=ab_test.pk)
    
    # Update status and start time
    ab_test.status = 'running'
    ab_test.start_time = timezone.now()
    ab_test.save()
    
    # In a real application, you would queue this for async processing with Celery
    # For demo purposes, we'll just update the status
    
    # Create notification
    Notification.create_notification(
        user=request.user,
        message=f"A/B test started: {ab_test.name}",
        notification_type='campaign_scheduled',
        related_object=ab_test
    )
    
    # Log activity
    UserActivity.log_activity(
        user=request.user,
        action='ab_test_started',
        description=f"Started A/B test: {ab_test.name}",
        metadata={'ab_test_id': ab_test.id}
    )
    
    messages.success(request, 'A/B test started successfully.')
    return redirect('ab_test_detail', pk=ab_test.pk)

@login_required
def cancel_ab_test(request, pk):
    """
    Cancel an A/B test campaign
    """
    ab_test = get_object_or_404(ABTestCampaign, pk=pk, owner=request.user)
    
    if ab_test.status not in ['setup', 'running']:
        messages.error(request, 'This A/B test cannot be cancelled because it is already completed.')
        return redirect('ab_test_detail', pk=ab_test.pk)
    
    # Update status
    ab_test.status = 'cancelled'
    ab_test.save()
    
    # Create notification
    Notification.create_notification(
        user=request.user,
        message=f"A/B test cancelled: {ab_test.name}",
        notification_type='campaign_error',
        related_object=ab_test
    )
    
    # Log activity
    UserActivity.log_activity(
        user=request.user,
        action='ab_test_cancelled',
        description=f"Cancelled A/B test: {ab_test.name}",
        metadata={'ab_test_id': ab_test.id}
    )
    
    messages.success(request, 'A/B test cancelled successfully.')
    return redirect('ab_test_detail', pk=ab_test.pk)

# Segment Management Views
@login_required
def segment_list(request):
    """
    List all audience segments
    """
    segments = Segment.objects.filter(owner=request.user).order_by('name')
    return render(request, 'marketing/segment_list.html', {'segments': segments})

@login_required
def create_segment(request):
    """
    Create a new audience segment
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        condition_type = request.POST.get('condition_type', 'all')
        
        # Process conditions from form
        conditions = []
        condition_count = int(request.POST.get('condition_count', 0))
        
        for i in range(condition_count):
            field = request.POST.get(f'condition_{i}_field')
            operator = request.POST.get(f'condition_{i}_operator')
            value = request.POST.get(f'condition_{i}_value')
            
            if field and operator and value:
                condition = {
                    'field': field,
                    'operator': operator,
                    'value': value
                }
                
                # If it's a custom field, also get the field name
                if field == 'custom_field':
                    field_name = request.POST.get(f'condition_{i}_field_name')
                    if field_name:
                        condition['field_name'] = field_name
                
                conditions.append(condition)
        
        # Create the segment
        segment = Segment(
            owner=request.user,
            name=name,
            description=description,
            condition_type=condition_type,
            conditions={'conditions': conditions}
        )
        segment.save()
        
        # Create notification
        Notification.create_notification(
            user=request.user,
            message=f"New segment created: {segment.name}",
            notification_type='system',
            related_object=segment
        )
        
        # Log activity
        UserActivity.log_activity(
            user=request.user,
            action='other',
            description=f"Created segment: {segment.name}",
            metadata={'segment_id': segment.id}
        )
        
        messages.success(request, 'Segment created successfully.')
        return redirect('segment_list')
    
    # GET request - show form
    return render(request, 'marketing/create_segment.html')

@login_required
def edit_segment(request, pk):
    """
    Edit an audience segment
    """
    segment = get_object_or_404(Segment, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        condition_type = request.POST.get('condition_type', 'all')
        
        # Process conditions from form
        conditions = []
        condition_count = int(request.POST.get('condition_count', 0))
        
        for i in range(condition_count):
            field = request.POST.get(f'condition_{i}_field')
            operator = request.POST.get(f'condition_{i}_operator')
            value = request.POST.get(f'condition_{i}_value')
            
            if field and operator and value:
                condition = {
                    'field': field,
                    'operator': operator,
                    'value': value
                }
                
                # If it's a custom field, also get the field name
                if field == 'custom_field':
                    field_name = request.POST.get(f'condition_{i}_field_name')
                    if field_name:
                        condition['field_name'] = field_name
                
                conditions.append(condition)
        
        # Update the segment
        segment.name = name
        segment.description = description
        segment.condition_type = condition_type
        segment.conditions = {'conditions': conditions}
        segment.save()
        
        messages.success(request, 'Segment updated successfully.')
        return redirect('segment_list')
    
    # GET request - show form with existing data
    existing_conditions = segment.conditions.get('conditions', [])
    
    return render(request, 'marketing/edit_segment.html', {
        'segment': segment,
        'conditions': existing_conditions
    })

@login_required
def delete_segment(request, pk):
    """
    Delete an audience segment
    """
    segment = get_object_or_404(Segment, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        segment.delete()
        messages.success(request, 'Segment deleted successfully.')
        return redirect('segment_list')
    
    return render(request, 'marketing/delete_segment.html', {'segment': segment})

@login_required
def cancel_campaign(request, pk):
    """
    Cancel a scheduled campaign
    """
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    
    # Only allow cancellation if campaign is in scheduled status
    if campaign.status != 'scheduled':
        messages.error(request, 'You can only cancel campaigns that are scheduled.')
        return redirect('campaign_detail', pk=campaign.pk)
    
    if request.method == 'POST':
        campaign.status = 'draft'
        campaign.schedule_time = None
        campaign.save()
        
        # Create notification
        Notification.create_notification(
            user=request.user,
            message=f"Campaign cancelled: {campaign.name}",
            notification_type='system',
            related_object=campaign
        )
        
        # Log activity
        UserActivity.log_activity(
            user=request.user,
            action='other',
            description=f"Cancelled scheduled campaign: {campaign.name}",
            metadata={'campaign_id': campaign.id}
        )
        
        messages.success(request, 'Campaign schedule cancelled successfully.')
        return redirect('campaign_detail', pk=campaign.pk)
    
    return render(request, 'marketing/cancel_campaign.html', {
        'campaign': campaign
    })

@login_required
def subscriber_activity(request, pk):
    """
    View activity for a specific subscriber
    """
    subscriber = get_object_or_404(Subscriber, pk=pk, owner=request.user)
    
    # Get all events for this subscriber
    events = EmailEvent.objects.filter(subscriber=subscriber).order_by('-timestamp')
    
    # Get all opens
    opens = EmailOpen.objects.filter(subscriber=subscriber).order_by('-timestamp')
    
    # Get all link clicks
    clicks = LinkClick.objects.filter(subscriber=subscriber).order_by('-timestamp')
    
    # Paginate events
    paginator = Paginator(events, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'marketing/subscriber_activity.html', {
        'subscriber': subscriber,
        'events': page_obj,
        'opens_count': opens.count(),
        'clicks_count': clicks.count(),
        'campaigns_count': events.values('campaign').distinct().count()
    })

# Automation views
@login_required
def automation_dashboard(request):
    """
    Display automation dashboard with all automations
    """
    automations = Automation.objects.filter(owner=request.user).order_by('-created_at')
    
    return render(request, 'marketing/automation_dashboard.html', {
        'automations': automations
    })

@login_required
def create_automation(request):
    """
    Create a new automation workflow
    """
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        trigger_type = request.POST.get('trigger_type')
        
        if not name or not trigger_type:
            messages.error(request, 'Please provide a name and trigger type for your automation.')
            return redirect('create_automation')
        
        # Create the automation
        automation = Automation.objects.create(
            owner=request.user,
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_details={},  # Default empty details
            is_active=False  # Default to inactive until fully configured
        )
        
        # Create default steps based on trigger type
        if trigger_type == 'subscription':
            # Create a welcome email step
            AutomationStep.objects.create(
                automation=automation,
                name='Welcome Email',
                step_type='email',
                position=0,
                config={
                    'subject': 'Welcome to our newsletter!',
                    'content': 'Thank you for subscribing to our newsletter.'
                }
            )
        
        # Log activity
        UserActivity.log_activity(
            user=request.user,
            action='other',
            description=f"Created automation: {name}",
            metadata={'automation_id': automation.id}
        )
        
        messages.success(request, 'Automation created successfully. Now add some steps to your workflow.')
        return redirect('edit_automation', pk=automation.id)
    
    # For GET request - show creation form
    trigger_types = Automation.TRIGGER_TYPES
    
    return render(request, 'marketing/create_automation.html', {
        'trigger_types': trigger_types
    })

@login_required
def edit_automation(request, pk):
    """
    Edit an existing automation workflow
    """
    automation = get_object_or_404(Automation, pk=pk, owner=request.user)
    steps = automation.steps.all().order_by('position')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        trigger_type = request.POST.get('trigger_type')
        is_active = request.POST.get('is_active') == 'on'
        
        if not name or not trigger_type:
            messages.error(request, 'Please provide a name and trigger type for your automation.')
            return redirect('edit_automation', pk=automation.id)
        
        # Update automation details
        automation.name = name
        automation.description = description
        automation.trigger_type = trigger_type
        automation.is_active = is_active
        automation.save()
        
        # Handle trigger-specific details
        if trigger_type == 'inactivity':
            days = request.POST.get('inactive_days', 30)
            automation.trigger_details = {'days': int(days)}
            automation.save()
        elif trigger_type == 'birthday':
            days_before = request.POST.get('days_before', 0)
            automation.trigger_details = {'days_before': int(days_before)}
            automation.save()
        
        messages.success(request, 'Automation updated successfully.')
        return redirect('automation_dashboard')
    
    # For GET request - show edit form
    trigger_types = Automation.TRIGGER_TYPES
    
    return render(request, 'marketing/edit_automation.html', {
        'automation': automation,
        'steps': steps,
        'trigger_types': trigger_types
    })

@login_required
def delete_automation(request, pk):
    """
    Delete an automation workflow
    """
    automation = get_object_or_404(Automation, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        automation_name = automation.name
        automation.delete()
        
        # Log activity
        UserActivity.log_activity(
            user=request.user,
            action='other',
            description=f"Deleted automation: {automation_name}",
            metadata={}
        )
        
        messages.success(request, 'Automation deleted successfully.')
        return redirect('automation_dashboard')
    
    return render(request, 'marketing/delete_automation.html', {
        'automation': automation
    })

@login_required
def automation_stats(request, pk):
    """
    View statistics for an automation
    """
    automation = get_object_or_404(Automation, pk=pk, owner=request.user)
    steps = automation.steps.all().order_by('position')
    
    # Toggle automation activation if requested
    if request.method == 'POST' and 'toggle_activation' in request.POST:
        automation.is_active = not automation.is_active
        automation.save()
        
        status = "activated" if automation.is_active else "deactivated"
        messages.success(request, f'Automation {status} successfully.')
        
        # Create notification
        Notification.create_notification(
            user=request.user,
            message=f"Automation {status}: {automation.name}",
            notification_type='system',
            related_object=automation
        )
        
        # Log activity
        UserActivity.log_activity(
            user=request.user,
            action='other',
            description=f"{status.capitalize()} automation: {automation.name}",
            metadata={'automation_id': automation.id}
        )
        
        return redirect('automation_stats', pk=automation.id)
    
    # Get step-specific stats
    total_subscribers = random.randint(100, 500)  # In a real app, you would get this from the database
    completed_subscribers = random.randint(0, total_subscribers)
    total_emails_sent = 0
    total_opens = 0
    total_clicks = 0
    
    # Calculate stats for each step
    step_stats = []
    for step in steps:
        if step.step_type == 'email':
            # In a real app, you would calculate these from the database
            sent = random.randint(50, 200)
            opened = int(sent * random.uniform(0.3, 0.6))
            clicked = int(opened * random.uniform(0.1, 0.3))
            
            total_emails_sent += sent
            total_opens += opened
            total_clicks += clicked
            
            step_stats.append({
                'step': step,
                'delay_days': step.config.get('days', 0),
                'email_subject': step.config.get('subject', ''),
                'sent_count': sent,
                'sent_percentage': round((sent / total_subscribers) * 100 if total_subscribers > 0 else 0, 1),
                'open_rate': round((opened / sent) * 100 if sent > 0 else 0, 1),
                'click_rate': round((clicked / sent) * 100 if sent > 0 else 0, 1)
            })
    
    # Generate random activity data
    recent_activity = []
    activity_types = ['email_sent', 'email_opened', 'link_clicked', 'subscriber_added', 'subscriber_completed']
    
    for _ in range(10):
        activity_type = random.choice(activity_types)
        
        if activity_type == 'email_sent':
            message = f"Email sent to subscriber"
        elif activity_type == 'email_opened':
            message = f"Subscriber opened email"
        elif activity_type == 'link_clicked':
            message = f"Subscriber clicked link in email"
        elif activity_type == 'subscriber_added':
            message = f"New subscriber added to automation"
        elif activity_type == 'subscriber_completed':
            message = f"Subscriber completed automation"
        
        # Generate random timestamp within last week
        random_days = random.randint(0, 7)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        timestamp = timezone.now() - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
        
        recent_activity.append({
            'type': activity_type,
            'message': message,
            'timestamp': timestamp,
            'subscriber': {
                'email': f"user{random.randint(1, 100)}@example.com"
            }
        })
    
    # Sort by timestamp (newest first)
    recent_activity.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Calculate overall metrics
    open_rate = round((total_opens / total_emails_sent) * 100 if total_emails_sent > 0 else 0, 1)
    click_rate = round((total_clicks / total_emails_sent) * 100 if total_emails_sent > 0 else 0, 1)
    completed_percentage = round((completed_subscribers / total_subscribers) * 100 if total_subscribers > 0 else 0, 1)
    avg_emails_per_subscriber = round(total_emails_sent / completed_subscribers, 1) if completed_subscribers > 0 else 0
    
    context = {
        'automation': automation,
        'steps': steps,
        'step_stats': step_stats,
        'total_subscribers': total_subscribers,
        'completed_subscribers': completed_subscribers,
        'completed_percentage': completed_percentage,
        'total_emails_sent': total_emails_sent,
        'avg_emails_per_subscriber': avg_emails_per_subscriber,
        'total_opens': total_opens,
        'total_clicks': total_clicks,
        'open_rate': open_rate,
        'click_rate': click_rate,
        'recent_activity': recent_activity
    }
    
    return render(request, 'marketing/automation_stats.html', context)

@login_required
def test_automation(request, pk):
    automation = get_object_or_404(Automation, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        email = request.POST.get('test_email')
        
        if not email:
            messages.error(request, "Please provide a test email address.")
            return redirect('test_automation', pk=automation.pk)
        
        try:
            # Get all steps in the automation
            steps = automation.steps.all().order_by('position')
            steps_count = steps.count()
            email_steps_count = 0
            
            # Send a test email for each step
            for step in steps:
                if step.step_type == 'email':
                    email_steps_count += 1
                    # Get step details from config
                    config = step.config
                    subject = config.get('subject', f'Step {step.position} - {automation.name}')
                    content = config.get('content', '')
                    
                    # Replace personalization tags with sample data
                    sample_data = {
                        'email': email,
                        'first_name': 'Test',
                        'last_name': 'User',
                    }
                    
                    for field, value in sample_data.items():
                        content = content.replace('{{' + field + '}}', value)
                    
                    # Add test prefix to subject
                    test_subject = f"[TEST] {subject}"
                    
                    # Send email using utility function
                    success = send_email_with_settings(
                        user=request.user,
                        subject=test_subject,
                        message=content,
                        to_emails=email,
                        html_content=content,  # Use same content as HTML
                        headers={'X-Test-Email': 'true', 'X-Automation-Step': str(step.position)}
                    )
                    
                    if not success:
                        messages.warning(request, f"Failed to send test email for step {step.position}. Check your email settings.")
            
            # Log activity
            UserActivity.objects.create(
                user=request.user,
                action='automation_tested',
                description=f'Test emails sent for automation "{automation.name}"',
                metadata={'automation_id': automation.pk, 'test_email': email}
            )
            
            messages.success(request, f"Test emails for all {email_steps_count} email steps sent successfully to {email}.")
        except Exception as e:
            messages.error(request, f"Failed to send test emails: {str(e)}")
        
        return redirect('automation_stats', pk=automation.pk)
    
    return render(request, 'marketing/test_automation.html', {
        'automation': automation
    })

@login_required
def test_campaign(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        email = request.POST.get('test_email')
        
        if not email:
            messages.error(request, "Please provide a test email address.")
            return redirect('test_campaign', pk=campaign.pk)
        
        try:
            # Personalize content
            html_content = campaign.html_content
            text_content = campaign.content
            
            # Replace personalization tags with sample data
            sample_data = {
                'email': email,
                'first_name': 'Test',
                'last_name': 'User',
            }
            
            for field, value in sample_data.items():
                html_content = html_content.replace('{{' + field + '}}', value)
                text_content = text_content.replace('{{' + field + '}}', value)
            
            # Add test prefix to subject
            test_subject = f"[TEST] {campaign.subject}"
            
            # Send email using utility function
            success = send_email_with_settings(
                user=request.user,
                subject=test_subject,
                message=text_content,
                to_emails=email,
                html_content=html_content,
                reply_to=campaign.reply_to,
                from_name=campaign.from_name,
                from_email=campaign.from_email,
                headers={'X-Test-Email': 'true'}
            )
            
            if success:
                # Log activity
                UserActivity.objects.create(
                    user=request.user,
                    action='campaign_tested',
                    description=f'Test email sent for campaign "{campaign.name}"',
                    metadata={'campaign_id': campaign.pk, 'test_email': email}
                )
                
                messages.success(request, f"Test email sent successfully to {email}.")
            else:
                messages.error(request, "Failed to send test email. Check your email settings.")
                
        except Exception as e:
            messages.error(request, f"Failed to send test email: {str(e)}")
        
        return redirect('campaign_detail', pk=campaign.pk)
    
    return render(request, 'marketing/test_campaign.html', {
        'campaign': campaign
    })

@login_required
def create_automation_from_template(request, template):
    """
    Create an automation from a predefined template
    """
    # Define templates with default configurations
    templates = {
        'welcome': {
            'name': 'Welcome Series',
            'description': 'A 3-part welcome series for new subscribers',
            'trigger_type': 'subscription',
            'steps': [
                {
                    'name': 'Welcome Email',
                    'step_type': 'email',
                    'position': 0,
                    'config': {
                        'subject': 'Welcome to our community!',
                        'content': 'Thank you for subscribing to our newsletter. We\'re excited to have you join our community! Here\'s what you can expect from us:\n\n- Regular updates on our products and services\n- Exclusive content and offers for subscribers\n- Tips and best practices in our industry\n\nFeel free to reply to this email if you have any questions!'
                    }
                },
                {
                    'name': 'Wait 3 Days',
                    'step_type': 'wait',
                    'position': 1,
                    'config': {
                        'days': 3
                    }
                },
                {
                    'name': 'Value Email',
                    'step_type': 'email',
                    'position': 2,
                    'config': {
                        'subject': 'Here\'s what you might have missed',
                        'content': 'Hello again!\n\nWe wanted to share some valuable resources with you that might be helpful:\n\n1. Our comprehensive guide to getting started\n2. Popular articles from our blog\n3. Case studies from successful customers\n\nClick the links above to learn more, and don\'t hesitate to reach out if you need any assistance!'
                    }
                },
                {
                    'name': 'Wait 4 Days',
                    'step_type': 'wait',
                    'position': 3,
                    'config': {
                        'days': 4
                    }
                },
                {
                    'name': 'Final Email',
                    'step_type': 'email',
                    'position': 4,
                    'config': {
                        'subject': 'Special offer for new subscribers',
                        'content': 'Hello there!\n\nAs a valued new subscriber, we\'d like to offer you a special discount on our premium plan. Use the code WELCOME20 at checkout to get 20% off your first purchase.\n\nThis offer is valid for 7 days, so don\'t miss out!\n\nBest regards,\nThe Team'
                    }
                }
            ]
        },
        're_engagement': {
            'name': 'Re-engagement Campaign',
            'description': 'Win back inactive subscribers',
            'trigger_type': 'inactivity',
            'trigger_details': {'days': 60},
            'steps': [
                {
                    'name': 'Re-engagement Email',
                    'step_type': 'email',
                    'position': 0,
                    'config': {
                        'subject': 'We miss you!',
                        'content': 'Hi there,\n\nWe noticed it\'s been a while since you\'ve engaged with our content. We miss you and wanted to check in!\n\nWe\'ve been working on some exciting new features and content that we think you\'ll love. Click below to see what\'s new.\n\nWe hope to see you back soon!'
                    }
                },
                {
                    'name': 'Wait 5 Days',
                    'step_type': 'wait',
                    'position': 1,
                    'config': {
                        'days': 5
                    }
                },
                {
                    'name': 'Final Re-engagement Email',
                    'step_type': 'email',
                    'position': 2,
                    'config': {
                        'subject': 'Last chance: Special offer inside',
                        'content': 'Hi there,\n\nWe\'d hate to see you go, but we understand that interests change over time.\n\nBefore you make your final decision, we\'d like to offer you a special discount of 30% on any of our plans. Just use the code COMEBACK30 at checkout.\n\nIf we don\'t hear from you in the next week, we\'ll respect your inbox and pause our emails. You can resubscribe anytime!\n\nBest regards,\nThe Team'
                    }
                }
            ]
        },
        'post_purchase': {
            'name': 'Post-Purchase Follow-up',
            'description': 'Thank customers and request reviews',
            'trigger_type': 'purchase',
            'steps': [
                {
                    'name': 'Thank You Email',
                    'step_type': 'email',
                    'position': 0,
                    'config': {
                        'subject': 'Thank you for your purchase!',
                        'content': 'Dear valued customer,\n\nThank you for your recent purchase! We\'re thrilled that you chose our product and hope it exceeds your expectations.\n\nYour order is being processed and will be shipped shortly. You\'ll receive tracking information as soon as it\'s available.\n\nIf you have any questions about your order, please don\'t hesitate to contact our customer support team.\n\nBest regards,\nThe Team'
                    }
                },
                {
                    'name': 'Wait 3 Days',
                    'step_type': 'wait',
                    'position': 1,
                    'config': {
                        'days': 3
                    }
                },
                {
                    'name': 'Review Request',
                    'step_type': 'email',
                    'position': 2,
                    'config': {
                        'subject': 'How are you enjoying your recent purchase?',
                        'content': 'Hi there!\n\nWe hope you\'re enjoying your recent purchase!\n\nYour feedback is incredibly valuable to us. If you have a moment, we\'d appreciate it if you could leave a review of your experience. This helps other customers make informed decisions and helps us improve our products and services.\n\nThank you for your support!\n\nBest regards,\nThe Team'
                    }
                }
            ]
        },
        'birthday': {
            'name': 'Birthday Celebration',
            'description': 'Send special offers on customer birthdays',
            'trigger_type': 'birthday',
            'steps': [
                {
                    'name': 'Birthday Greeting',
                    'step_type': 'email',
                    'position': 0,
                    'config': {
                        'subject': 'Happy Birthday! 🎂 A special gift inside',
                        'content': 'Happy Birthday!\n\nWe wanted to wish you a fantastic birthday and thank you for being part of our community. To celebrate your special day, we\'re giving you a gift!\n\nUse the code BIRTHDAY25 to get 25% off your next purchase. This code is valid for 7 days.\n\nHave a wonderful day!\n\nBest wishes,\nThe Team'
                    }
                }
            ]
        },
        'product_education': {
            'name': 'Product Education Series',
            'description': 'Help customers get the most out of your product',
            'trigger_type': 'purchase',
            'steps': [
                {
                    'name': 'Getting Started Guide',
                    'step_type': 'email',
                    'position': 0,
                    'config': {
                        'subject': 'Getting Started with Your New Product',
                        'content': 'Welcome to the family!\n\nWe\'re excited that you\'ve chosen our product. To help you get started quickly, we\'ve put together a comprehensive guide.\n\nIn this email, we\'ll cover the basics of setting up your product and some initial configuration steps. By the end, you\'ll be ready to start using your new purchase!\n\nIf you have any questions, our support team is always ready to help.'
                    }
                },
                {
                    'name': 'Wait 2 Days',
                    'step_type': 'wait',
                    'position': 1,
                    'config': {
                        'days': 2
                    }
                },
                {
                    'name': 'Tips and Tricks',
                    'step_type': 'email',
                    'position': 2,
                    'config': {
                        'subject': 'Pro Tips for Getting More from Your Product',
                        'content': 'Hi there!\n\nNow that you\'ve had some time to explore the basic features, we wanted to share some pro tips to help you get even more value from your purchase.\n\nHere are 5 power-user tips that many customers don\'t discover right away:\n\n1. Keyboard shortcuts for faster navigation\n2. Advanced customization options\n3. Integration capabilities with other tools\n4. Automation features to save time\n5. Analytics dashboards to track performance\n\nTry these out and let us know what you think!'
                    }
                },
                {
                    'name': 'Wait 4 Days',
                    'step_type': 'wait',
                    'position': 3,
                    'config': {
                        'days': 4
                    }
                },
                {
                    'name': 'Advanced Features',
                    'step_type': 'email',
                    'position': 4,
                    'config': {
                        'subject': 'Unlock Advanced Features You Might Have Missed',
                        'content': 'Hello again!\n\nBy now, you\'re probably comfortable with the main features of our product. It\'s time to dive into some of the more advanced capabilities that can take your experience to the next level.\n\nIn this guide, we\'ll explore:\n\n- Advanced reporting and analytics\n- Team collaboration features\n- Custom automation workflows\n- API integrations\n- White-labeling options\n\nReady to become a power user? Let\'s get started!'
                    }
                }
            ]
        },
        'cart_abandonment': {
            'name': 'Cart Abandonment Recovery',
            'description': 'Recover abandoned shopping carts',
            'trigger_type': 'abandoned_cart',
            'steps': [
                {
                    'name': 'First Reminder',
                    'step_type': 'email',
                    'position': 0,
                    'config': {
                        'subject': 'You left something in your cart',
                        'content': 'Hi there,\n\nLooks like you left some items in your shopping cart! We\'ve saved them for you in case you want to complete your purchase.\n\nJust click the button below to return to your cart. If you have any questions about these products, our customer service team is happy to help.\n\nHappy shopping!'
                    }
                },
                {
                    'name': 'Wait 1 Day',
                    'step_type': 'wait',
                    'position': 1,
                    'config': {
                        'days': 1
                    }
                },
                {
                    'name': 'Special Offer',
                    'step_type': 'email',
                    'position': 2,
                    'config': {
                        'subject': 'Special offer for your cart items',
                        'content': 'Hello again,\n\nWe noticed you still have items in your cart. To make your decision easier, we\'re offering a 10% discount on these items.\n\nUse code CART10 at checkout to claim your discount. This offer is valid for 24 hours only!\n\nClick below to complete your purchase and save money today.'
                    }
                },
                {
                    'name': 'Wait 1 Day',
                    'step_type': 'wait',
                    'position': 3,
                    'config': {
                        'days': 1
                    }
                },
                {
                    'name': 'Final Reminder',
                    'step_type': 'email',
                    'position': 4,
                    'config': {
                        'subject': 'Last chance: Your cart will expire soon',
                        'content': 'Hi there,\n\nThis is a friendly reminder that your shopping cart will expire soon. Don\'t miss out on the items you carefully selected!\n\nIf you\'re having any issues with the checkout process, our support team is ready to assist you.\n\nComplete your purchase now to secure your items.'
                    }
                }
            ]
        }
    }
    
    # Check if the requested template exists
    if template not in templates:
        messages.error(request, 'Template not found.')
        return redirect('automation_dashboard')
    
    # Get the template configuration
    template_config = templates[template]
    
    # Create the automation
    automation = Automation.objects.create(
        owner=request.user,
        name=template_config['name'],
        description=template_config['description'],
        trigger_type=template_config['trigger_type'],
        trigger_details=template_config.get('trigger_details', {}),
        is_active=False
    )
    
    # Create the steps
    for step_config in template_config['steps']:
        AutomationStep.objects.create(
            automation=automation,
            name=step_config['name'],
            step_type=step_config['step_type'],
            position=step_config['position'],
            config=step_config['config']
        )
    
    # Log activity
    UserActivity.objects.create(
        user=request.user,
        action='other',
        description=f"Created automation from template: {template_config['name']}",
        metadata={'automation_id': automation.id, 'template': template}
    )
    
    messages.success(request, f'Automation created successfully from the {template_config["name"]} template.')
    return redirect('edit_automation', pk=automation.id)