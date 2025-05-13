from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm, CustomPasswordChangeForm
from .models import CustomUser, UserActivity
from django.urls import reverse

def user_login(request):
    """
    User login view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            
            # Record the login activity
            UserActivity.objects.create(
                user=user,
                action='login',
                details={'ip': request.META.get('REMOTE_ADDR')}
            )
            
            # Redirect to next URL if provided, otherwise dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
    else:
        form = CustomAuthenticationForm()
    
    return render(request, 'auth/login.html', {'form': form})

def user_logout(request):
    """
    Handle user logout with GET request
    """
    if request.user.is_authenticated:
        logout(request)
    return redirect('home')

def register(request):
    """
    User registration view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Send verification email
            send_verification_email(request, user)
            
            # Log in the user
            login(request, user)
            
            # Record registration activity
            UserActivity.objects.create(
                user=user,
                action='register',
                details={'ip': request.META.get('REMOTE_ADDR')}
            )
            
            messages.success(request, 'Your account has been created. Please check your email to verify your account.')
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'auth/register.html', {'form': form})

@login_required
def profile(request):
    """
    User profile view
    """
    # Get user activities for display
    activities = request.user.activities.all()[:10]
    
    return render(request, 'users/profile.html', {
        'user': request.user,
        'activities': activities
    })

@login_required
def edit_profile(request):
    """
    Edit user profile view
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'users/edit_profile.html', {'form': form})

@login_required
def change_password(request):
    """
    Change password view
    """
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Update the session to prevent logging out
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            
            # Record password change activity
            UserActivity.objects.create(
                user=request.user,
                action='change_password',
                details={'ip': request.META.get('REMOTE_ADDR')}
            )
            
            return redirect('profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'users/change_password.html', {'form': form})

def verify_email(request, uidb64, token):
    """
    Verify email with token
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None
    
    if user is not None and default_token_generator.check_token(user, token):
        user.is_verified = True
        user.save()
        
        # Record verification activity
        UserActivity.objects.create(
            user=user,
            action='email_verified',
            details={'ip': request.META.get('REMOTE_ADDR')}
        )
        
        messages.success(request, 'Your email has been verified. Thank you!')
    else:
        messages.error(request, 'The verification link is invalid or has expired.')
    
    return redirect('login')

@login_required
def resend_verification(request):
    """
    Resend email verification link
    """
    if request.user.is_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('profile')
    
    send_verification_email(request, request.user)
    messages.success(request, 'A new verification email has been sent to your email address.')
    return redirect('profile')

@login_required
def subscription(request):
    """
    View subscription details
    """
    return render(request, 'users/subscription.html', {'user': request.user})

@login_required
def upgrade_subscription(request):
    """
    Upgrade subscription view
    """
    # This would normally integrate with a payment processor
    
    if request.method == 'POST':
        plan = request.POST.get('plan')
        if plan in ['basic', 'premium', 'enterprise']:
            request.user.subscription_plan = plan
            
            # Set quota based on the plan
            if plan == 'basic':
                request.user.usage_quota = 5000
            elif plan == 'premium':
                request.user.usage_quota = 20000
            elif plan == 'enterprise':
                request.user.usage_quota = 100000
            
            request.user.save()
            
            # Record subscription change
            UserActivity.objects.create(
                user=request.user,
                action='subscription_changed',
                details={'plan': plan}
            )
            
            messages.success(request, f'Your subscription has been upgraded to {plan.title()}!')
            return redirect('subscription')
    
    return render(request, 'users/upgrade_subscription.html')

# Helper functions
def send_verification_email(request, user):
    """
    Send verification email to the user
    """
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    verification_url = request.build_absolute_uri(
        reverse('verify_email', kwargs={'uidb64': uid, 'token': token})
    )
    
    subject = 'Verify Your Email Address'
    context = {
        'user': user,
        'verification_url': verification_url,
    }
    
    # Render both HTML and plain text versions
    html_message = render_to_string('auth/email_verification.html', context)
    text_message = render_to_string('auth/email_verification.txt', context)
    
    # Send email with both HTML and text versions
    send_mail(
        subject,
        text_message,  # Plain text version
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,  # HTML version
    )
