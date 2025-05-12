from django.contrib.auth import get_user_model
from .models import Subscriber, Campaign, EmailTemplate, UserActivity

def admin_stats(request):
    """
    Context processor to provide statistics for the admin dashboard.
    """
    # Only process if we're in the admin and the user is staff
    if request.path.startswith('/admin/') and request.user.is_staff:
        User = get_user_model()
        return {
            'subscriber_count': Subscriber.objects.count(),
            'campaign_count': Campaign.objects.count(),
            'template_count': EmailTemplate.objects.count(),
            'user_count': User.objects.count(),
            'recent_activities': UserActivity.objects.order_by('-timestamp')[:5],
        }
    return {} 