"""
URL configuration for email_marketing_platform project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from marketing import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('marketing.urls')),
    path('accounts/', include('users.urls')),
    path('automations/', views.automation_dashboard, name='automation_dashboard'),
    path('automations/create/', views.create_automation, name='create_automation'),
    path('automations/<int:pk>/edit/', views.edit_automation, name='edit_automation'),
    path('automations/<int:pk>/delete/', views.delete_automation, name='delete_automation'),
    path('automations/<int:pk>/stats/', views.automation_stats, name='automation_stats'),
    path('automations/<int:pk>/test/', views.test_automation, name='test_automation'),
    path('automations/template/<str:template>/', views.create_automation_from_template, name='create_automation_from_template'),
    path('campaigns/<int:pk>/test/', views.test_campaign, name='test_campaign'),
    path('health/', views.health_check, name='health_check'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_URL)
# In production, the static files are handled by whitenoise middleware
