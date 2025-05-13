from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserActivity, Subscription, SubscriptionInvoice, SmtpSettings
from .forms import CustomUserCreationForm, CustomUserChangeForm

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ('email', 'username', 'company_name', 'subscription_plan', 'is_staff', 'is_active', 'is_verified')
    list_filter = ('subscription_plan', 'is_staff', 'is_active', 'is_verified')
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'company_name', 'profile_image')}),
        ('Subscription', {'fields': ('subscription_plan', 'usage_quota', 'usage_count')}),
        ('Stripe Integration', {'fields': ('stripe_customer_id', 'stripe_subscription_id', 'subscription_renewal', 'payment_method_id', 'has_active_payment_method')}),
        ('Permissions', {'fields': ('is_verified', 'is_staff', 'is_active', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('email', 'username', 'company_name')
    ordering = ('email',)
    actions = ['verify_users', 'upgrade_to_premium', 'upgrade_to_enterprise', 'reset_to_free', 'reset_usage_counts']
    
    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} users were successfully verified.')
    verify_users.short_description = "Mark selected users as verified"
    
    def upgrade_to_premium(self, request, queryset):
        updated = queryset.update(subscription_plan='premium', usage_quota=20000)
        self.message_user(request, f'{updated} users were upgraded to Premium plan.')
    upgrade_to_premium.short_description = "Upgrade selected users to Premium plan"
    
    def upgrade_to_enterprise(self, request, queryset):
        updated = queryset.update(subscription_plan='enterprise', usage_quota=100000)
        self.message_user(request, f'{updated} users were upgraded to Enterprise plan.')
    upgrade_to_enterprise.short_description = "Upgrade selected users to Enterprise plan"
    
    def reset_to_free(self, request, queryset):
        updated = queryset.update(subscription_plan='free', usage_quota=100)
        self.message_user(request, f'{updated} users were reset to Free plan.')
    reset_to_free.short_description = "Reset selected users to Free plan"
    
    def reset_usage_counts(self, request, queryset):
        updated = queryset.update(usage_count=0)
        self.message_user(request, f'Usage counts for {updated} users were reset to 0.')
    reset_usage_counts.short_description = "Reset usage counts to zero"

class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'timestamp', 'get_details')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__email', 'action', 'details')
    date_hierarchy = 'timestamp'
    readonly_fields = ('user', 'action', 'timestamp', 'details')
    
    def get_details(self, obj):
        if obj.details:
            return str(obj.details)
        return '-'
    get_details.short_description = 'Details'

class SubscriptionInline(admin.TabularInline):
    model = Subscription
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('plan', 'status', 'stripe_subscription_id', 'start_date', 'end_date', 'next_billing_date', 'cancel_at_period_end')

class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'next_billing_date', 'cancel_at_period_end')
    list_filter = ('plan', 'status', 'cancel_at_period_end', 'created_at')
    search_fields = ('user__email', 'stripe_subscription_id', 'stripe_invoice_id')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        (None, {'fields': ('user', 'plan', 'status')}),
        ('Stripe Information', {'fields': ('stripe_subscription_id', 'stripe_invoice_id')}),
        ('Dates', {'fields': ('start_date', 'end_date', 'next_billing_date', 'cancel_at_period_end')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)})
    )
    
    actions = ['cancel_subscriptions', 'mark_as_active']
    
    def cancel_subscriptions(self, request, queryset):
        updated = queryset.update(cancel_at_period_end=True)
        self.message_user(request, f'{updated} subscriptions have been marked to cancel at period end.')
    cancel_subscriptions.short_description = "Cancel selected subscriptions at period end"
    
    def mark_as_active(self, request, queryset):
        updated = queryset.update(status='active', cancel_at_period_end=False)
        self.message_user(request, f'{updated} subscriptions have been marked as active.')
    mark_as_active.short_description = "Mark selected subscriptions as active"

class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display = ('user', 'subscription', 'amount', 'status', 'invoice_date', 'due_date')
    list_filter = ('status', 'invoice_date', 'created_at')
    search_fields = ('user__email', 'stripe_invoice_id', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'invoice_date'
    
    fieldsets = (
        (None, {'fields': ('user', 'subscription', 'description', 'amount', 'status')}),
        ('Stripe Information', {'fields': ('stripe_invoice_id', 'invoice_pdf_url')}),
        ('Dates', {'fields': ('invoice_date', 'due_date')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)})
    )
    
    actions = ['mark_as_paid', 'mark_as_pending']
    
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(status='paid')
        self.message_user(request, f'{updated} invoices have been marked as paid.')
    mark_as_paid.short_description = "Mark selected invoices as paid"
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending')
        self.message_user(request, f'{updated} invoices have been marked as pending.')
    mark_as_pending.short_description = "Mark selected invoices as pending"

@admin.register(SmtpSettings)
class SmtpSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'host', 'port', 'from_email', 'is_active', 'updated_at')
    list_filter = ('is_active', 'use_tls', 'use_ssl')
    search_fields = ('user__email', 'host', 'username', 'from_email', 'from_name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'is_active'),
        }),
        ('SMTP Server Settings', {
            'fields': ('host', 'port', 'username', 'password', 'use_tls', 'use_ssl'),
        }),
        ('Email Settings', {
            'fields': ('from_email', 'from_name'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(SubscriptionInvoice, SubscriptionInvoiceAdmin)
