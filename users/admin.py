from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser, UserActivity

class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email', 'company_name', 'profile_image')}),
        (_('Subscription'), {'fields': ('subscription_plan', 'usage_quota', 'is_verified')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'company_name', 'subscription_plan'),
        }),
    )
    list_display = ('email', 'username', 'first_name', 'last_name', 'company_name', 'subscription_plan', 'usage_quota', 'is_verified', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'company_name')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'subscription_plan', 'is_verified')
    ordering = ('-date_joined',)
    actions = ['verify_users', 'upgrade_to_premium', 'upgrade_to_enterprise', 'reset_to_free']
    
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

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
