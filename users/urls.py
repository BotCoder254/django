from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Authentication routes
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
    
    # Password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='auth/password_reset_form.html',
        email_template_name='auth/password_reset_email.html',
        subject_template_name='auth/password_reset_subject.txt'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='auth/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # User profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/change-password/', views.change_password, name='change_password'),
    
    # Email verification
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    
    # Subscription management
    path('subscription/', views.subscription, name='subscription'),
    path('subscription/upgrade/', views.upgrade_subscription, name='upgrade_subscription'),
    path('subscription/success/', views.subscription_success, name='subscription_success'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/update-payment/', views.update_payment_method, name='update_payment_method'),
    
    # Stripe webhook
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),

    # Add these to urlpatterns
    path('settings/smtp/', views.smtp_settings, name='smtp_settings'),
    path('settings/smtp/test/', views.test_smtp_connection, name='test_smtp_connection'),
] 