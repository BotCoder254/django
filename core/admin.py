from django.contrib import admin
from .models import SystemSetting, EmailProvider, IntegrationProvider, Audit

@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'description', 'is_public', 'updated_at')
    list_filter = ('is_public', 'updated_at')
    search_fields = ('key', 'value', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('key', 'value', 'description', 'is_public'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['make_public', 'make_private']
    
    def make_public(self, request, queryset):
        updated = queryset.update(is_public=True)
        self.message_user(request, f'{updated} settings were made public.')
    make_public.short_description = "Make selected settings public"
    
    def make_private(self, request, queryset):
        updated = queryset.update(is_public=False)
        self.message_user(request, f'{updated} settings were made private.')
    make_private.short_description = "Make selected settings private"

@admin.register(EmailProvider)
class EmailProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('provider_type', 'is_active', 'created_at')
    search_fields = ('name', 'provider_type', 'settings')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'provider_type', 'is_active'),
        }),
        ('Configuration', {
            'fields': ('settings',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['activate_provider', 'deactivate_provider']
    
    def activate_provider(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} email providers were activated.')
    activate_provider.short_description = "Activate selected email providers"
    
    def deactivate_provider(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} email providers were deactivated.')
    deactivate_provider.short_description = "Deactivate selected email providers"

@admin.register(IntegrationProvider)
class IntegrationProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('provider_type', 'is_active', 'created_at')
    search_fields = ('name', 'provider_type', 'settings')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'provider_type', 'is_active'),
        }),
        ('Configuration', {
            'fields': ('settings',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    actions = ['activate_integration', 'deactivate_integration']
    
    def activate_integration(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} integration providers were activated.')
    activate_integration.short_description = "Activate selected integration providers"
    
    def deactivate_integration(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} integration providers were deactivated.')
    deactivate_integration.short_description = "Deactivate selected integration providers"

@admin.register(Audit)
class AuditAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'content_type', 'object_id', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp', 'content_type')
    search_fields = ('user__email', 'ip_address', 'user_agent', 'changes')
    readonly_fields = ('action', 'user', 'content_type', 'object_id', 'changes', 'timestamp', 'ip_address', 'user_agent')
    date_hierarchy = 'timestamp'
    fieldsets = (
        (None, {
            'fields': ('action', 'user', 'content_type', 'object_id'),
        }),
        ('Changes', {
            'fields': ('changes',),
        }),
        ('Request Details', {
            'fields': ('timestamp', 'ip_address', 'user_agent'),
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False 