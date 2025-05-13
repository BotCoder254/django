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
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm, CustomPasswordChangeForm, SmtpSettingsForm
from .models import CustomUser, UserActivity, Subscription, SubscriptionInvoice, SmtpSettings
from django.urls import reverse
import stripe
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator

# Stripe configuration
stripe.api_key = settings.STRIPE_SECRET_KEY

# Define price IDs for each plan
STRIPE_PRICE_IDS = {
    'basic': 'price_1ROFmxCTLeMMvOE0kfWAbUZq',
    'premium': 'price_1ROFo4CTLeMMvOE0qMgz5mf6',
    'enterprise': 'price_1ROFp6CTLeMMvOE0qa53yQlq',
}

# Plan features and limits
PLAN_FEATURES = {
    'free': {
        'emails_per_month': 100,
        'features': ['Single User', 'Basic Analytics', 'Email Support']
    },
    'basic': {
        'emails_per_month': 5000,
        'features': ['5 Users', 'Advanced Analytics', 'Priority Email Support', 'Custom Templates']
    },
    'premium': {
        'emails_per_month': 20000,
        'features': ['10 Users', 'Advanced Analytics', 'Priority Email Support', 'Custom Templates', 'API Access', 'Dedicated Account Manager']
    },
    'enterprise': {
        'emails_per_month': 100000,
        'features': ['Unlimited Users', 'Advanced Analytics', '24/7 Phone Support', 'Custom Templates', 'API Access', 'Dedicated Account Manager', 'White Labeling', 'Custom Integration']
    }
}

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
    # Get user activities with pagination (3 items per page)
    activities_list = request.user.activities.all().order_by('-timestamp')
    paginator = Paginator(activities_list, 3)
    page_number = request.GET.get('page')
    activities = paginator.get_page(page_number)
    
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
    user = request.user
    
    # Get subscription data for the user
    active_subscription = None
    try:
        active_subscription = Subscription.objects.filter(
            user=user, 
            status='active'
        ).latest('created_at')
    except Subscription.DoesNotExist:
        pass
    
    # Get latest invoices
    recent_invoices = SubscriptionInvoice.objects.filter(
        user=user
    ).order_by('-invoice_date')[:5]
    
    # Calculate usage percentage
    usage_percentage = user.get_usage_percentage()
    
    # Get plan features
    plan_features = PLAN_FEATURES.get(user.subscription_plan, PLAN_FEATURES['free'])
    
    context = {
        'user': user,
        'subscription': active_subscription,
        'recent_invoices': recent_invoices,
        'usage_percentage': usage_percentage,
        'plan_features': plan_features,
        'subscription_renewal': user.subscription_renewal,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    
    return render(request, 'users/subscription.html', context)

@login_required
def upgrade_subscription(request):
    user = request.user
    
    if request.method == 'POST':
        plan = request.POST.get('plan')
        
        if plan in ['basic', 'premium', 'enterprise']:
            try:
                # If user doesn't have a Stripe customer ID yet, create one
                if not user.stripe_customer_id:
                    try:
                        print(f"Creating Stripe customer for user: {user.email}")
                        customer = stripe.Customer.create(
                            email=user.email,
                            name=f"{user.first_name} {user.last_name}",
                            metadata={
                                'user_id': user.id
                            }
                        )
                        user.stripe_customer_id = customer.id
                        user.save()
                        print(f"Created Stripe customer: {customer.id}")
                    except Exception as e:
                        print(f"Error creating Stripe customer: {str(e)}")
                        messages.error(request, f"Error creating customer profile: {str(e)}")
                        return redirect('subscription')
                else:
                    print(f"Using existing Stripe customer: {user.stripe_customer_id}")
                    # Verify customer exists and is valid
                    try:
                        stripe.Customer.retrieve(user.stripe_customer_id)
                    except stripe.error.InvalidRequestError:
                        print(f"Invalid customer ID, creating new customer")
                        # Customer doesn't exist, create a new one
                        customer = stripe.Customer.create(
                            email=user.email,
                            name=f"{user.first_name} {user.last_name}",
                            metadata={
                                'user_id': user.id
                            }
                        )
                        user.stripe_customer_id = customer.id
                        user.save()
                
                # Verify the price ID exists
                price_id = STRIPE_PRICE_IDS.get(plan)
                if not price_id:
                    messages.error(request, f"Invalid plan price ID for plan: {plan}")
                    return redirect('subscription')
                
                print(f"Using price ID: {price_id} for plan: {plan}")
                
                # Verify the price exists in Stripe
                try:
                    stripe.Price.retrieve(price_id)
                except stripe.error.InvalidRequestError as e:
                    print(f"Invalid price ID: {price_id}, error: {str(e)}")
                    messages.error(request, f"The selected plan is currently unavailable. Please contact support.")
                    return redirect('subscription')
                
                # Create a checkout session with expanded properties for better debugging
                print(f"Creating checkout session for user: {user.email}, plan: {plan}")
                checkout_session = stripe.checkout.Session.create(
                    customer=user.stripe_customer_id,
                    payment_method_types=['card'],
                    line_items=[{
                        'price': price_id,
                        'quantity': 1,
                    }],
                    mode='subscription',
                    success_url=request.build_absolute_uri(reverse('subscription_success')) + f'?session_id={{CHECKOUT_SESSION_ID}}&plan={plan}',
                    cancel_url=request.build_absolute_uri(reverse('subscription')),
                    expand=['payment_intent'],
                )
                
                # Store session ID temporarily
                request.session['checkout_session_id'] = checkout_session.id
                request.session['selected_plan'] = plan
                
                print(f"Created checkout session: {checkout_session.id}, URL: {checkout_session.url}")
                
                # Redirect to Stripe Checkout
                return redirect(checkout_session.url)
                
            except stripe.error.CardError as e:
                # Since it's a decline, stripe.error.CardError will be caught
                print(f"Card error: {str(e)}")
                error_msg = f"Your card was declined: {e.user_message}" if hasattr(e, 'user_message') else "Your card was declined."
                messages.error(request, error_msg)
                return redirect('subscription')
            except stripe.error.RateLimitError as e:
                # Too many requests made to the API too quickly
                print(f"Rate limit error: {str(e)}")
                messages.error(request, "Too many payment requests. Please try again in a moment.")
                return redirect('subscription')
            except stripe.error.InvalidRequestError as e:
                # Invalid parameters were supplied to Stripe's API
                print(f"Invalid request error: {str(e)}")
                messages.error(request, "There was an issue with your payment information. Please check your details and try again.")
                return redirect('subscription')
            except stripe.error.AuthenticationError as e:
                # Authentication with Stripe's API failed
                print(f"Authentication error: {str(e)}")
                messages.error(request, "We're having trouble connecting to our payment processor. Please try again later.")
                return redirect('subscription')
            except stripe.error.APIConnectionError as e:
                # Network communication with Stripe failed
                print(f"API connection error: {str(e)}")
                messages.error(request, "We're having trouble connecting to our payment processor. Please check your internet connection and try again.")
                return redirect('subscription')
            except stripe.error.StripeError as e:
                # Display a very generic error to the user
                print(f"Stripe error: {str(e)}")
                error_msg = f"Payment processing error: {e.user_message}" if hasattr(e, 'user_message') else "An unexpected error occurred with the payment processor."
                messages.error(request, error_msg)
                return redirect('subscription')
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                messages.error(request, f'An unexpected error occurred. Our team has been notified.')
                return redirect('subscription')
                
        else:
            messages.error(request, 'Invalid subscription plan selected')
            return redirect('subscription')
    
    # For GET requests - display the upgrade options
    context = {
        'user': user,
        'plans': {
            'basic': PLAN_FEATURES['basic'],
            'premium': PLAN_FEATURES['premium'],
            'enterprise': PLAN_FEATURES['enterprise'],
        },
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }
    
    return render(request, 'users/upgrade_subscription.html', context)

@login_required
def subscription_success(request):
    session_id = request.GET.get('session_id')
    plan = request.GET.get('plan')
    
    if not session_id:
        messages.error(request, 'Missing checkout session ID')
        return redirect('subscription')
    
    try:
        print(f"Processing subscription success for session: {session_id}, plan: {plan}")
        
        # Retrieve session from Stripe
        try:
            session = stripe.checkout.Session.retrieve(
                session_id,
                expand=['subscription', 'subscription.default_payment_method']
            )
            print(f"Retrieved checkout session, status: {session.status}")
        except stripe.error.InvalidRequestError as e:
            print(f"Error retrieving session: {str(e)}")
            messages.error(request, 'Unable to verify subscription details. If your payment was successful, it may take a few minutes to reflect in your account.')
            return redirect('subscription')
        
        if session.status != 'complete':
            print(f"Session is not complete: {session.status}")
            messages.warning(request, 'Your payment is being processed. It may take a few minutes to update your subscription.')
            return redirect('subscription')
        
        # Update user's subscription information
        user = request.user
        
        # Set subscription details
        user.subscription_plan = plan
        
        # Set usage quota based on plan
        if plan == 'basic':
            user.usage_quota = 5000
        elif plan == 'premium':
            user.usage_quota = 20000
        elif plan == 'enterprise':
            user.usage_quota = 100000
        
        # Reset usage count for new billing period
        user.usage_count = 0
        
        # Update Stripe subscription ID
        if hasattr(session, 'subscription') and session.subscription:
            user.stripe_subscription_id = session.subscription.id if isinstance(session.subscription, dict) else session.subscription
            
            # Retrieve the subscription to get more details if needed
            subscription_object = None
            try:
                if isinstance(session.subscription, str):
                    subscription_object = stripe.Subscription.retrieve(session.subscription)
                else:
                    subscription_object = session.subscription
                
                # Get renewal date from subscription
                current_period_end = subscription_object.current_period_end
                renewal_date = timezone.datetime.fromtimestamp(
                    current_period_end, tz=timezone.utc
                )
                user.subscription_renewal = renewal_date
            except Exception as e:
                print(f"Error retrieving subscription details: {str(e)}")
                # Use default renewal date as fallback
                user.subscription_renewal = timezone.now() + timezone.timedelta(days=30)
        else:
            print("Warning: No subscription found in session")
            # Use default renewal date
            user.subscription_renewal = timezone.now() + timezone.timedelta(days=30)
        
        # Update payment method status
        user.has_active_payment_method = True
        
        user.save()
        print(f"Updated user subscription details for {user.email}")
        
        # Create a Subscription record if it doesn't already exist
        try:
            # Check if subscription already exists (could have been created by webhook)
            existing_sub = Subscription.objects.filter(
                user=user,
                stripe_subscription_id=user.stripe_subscription_id,
                status='active'
            ).exists()
            
            if not existing_sub and user.stripe_subscription_id:
                # Create a new subscription record
                new_subscription = Subscription.objects.create(
                    user=user,
                    plan=plan,
                    status='active',
                    stripe_subscription_id=user.stripe_subscription_id,
                    start_date=timezone.now(),
                    next_billing_date=user.subscription_renewal,
                )
                print(f"Created new subscription record for {user.email}")
                
                # Log user activity
                UserActivity.objects.create(
                    user=user, 
                    action='subscription_upgraded',
                    details={
                        'plan': plan,
                        'previous_plan': user.subscription_plan,
                        'stripe_subscription_id': user.stripe_subscription_id
                    }
                )
            else:
                print(f"Subscription record already exists or missing subscription ID")
        except Exception as e:
            print(f"Error creating subscription record: {str(e)}")
        
        messages.success(request, f'Successfully upgraded to {plan.title()} plan!')
        
    except Exception as e:
        print(f"Unexpected error in subscription_success: {str(e)}")
        messages.error(request, 'An error occurred while processing your subscription. If your payment was successful, it may take a few minutes to reflect in your account.')
    
    return redirect('subscription')

@login_required
def cancel_subscription(request):
    if request.method == 'POST':
        user = request.user
        
        if not user.stripe_subscription_id:
            messages.error(request, 'No active subscription found')
            return redirect('subscription')
        
        try:
            # Get the subscription from Stripe
            subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
            
            # Cancel the subscription at period end
            stripe.Subscription.modify(
                user.stripe_subscription_id,
                cancel_at_period_end=True
            )
            
            # Update the subscription in our database
            user_subscription = Subscription.objects.get(
                user=user,
                stripe_subscription_id=user.stripe_subscription_id,
                status='active'
            )
            user_subscription.cancel_at_period_end = True
            user_subscription.save()
            
            # Log the activity
            UserActivity.objects.create(
                user=user,
                action='subscription_cancelled',
                details={
                    'plan': user.subscription_plan,
                    'effective_cancellation_date': subscription.current_period_end
                }
            )
            
        except Subscription.DoesNotExist:
            messages.error(request, 'Subscription not found in our records')
        except Exception as e:
            messages.error(request, f'Error cancelling subscription: {str(e)}')
    
    return redirect('subscription')

@login_required
def update_payment_method(request):
    user = request.user
    
    try:
        # Create a SetupIntent for updating payment method
        setup_intent = stripe.SetupIntent.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
        )
        
        return JsonResponse({
            'client_secret': setup_intent.client_secret,
            'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    print(f"Received webhook with signature header: {sig_header is not None}")
    
    if not sig_header:
        print("Error: No Stripe signature header found in the request")
        return HttpResponse(status=400)
    
    try:
        print(f"Attempting to construct event with webhook secret: {settings.STRIPE_WEBHOOK_SECRET[:6]}...")
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        print(f"Successfully parsed webhook event type: {event.type}")
    except ValueError as e:
        # Invalid payload
        print(f"Invalid webhook payload: {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Invalid webhook signature: {str(e)}")
        print(f"Check if the STRIPE_WEBHOOK_SECRET in settings.py is correct.")
        return HttpResponse(status=400)
    
    # Handle the event
    if event.type == 'checkout.session.completed':
        # Handle checkout session completed event
        session = event.data.object
        print(f"Checkout session completed: {session.id}")
        
        if session.mode == 'subscription':
            try:
                # Find the user by customer ID
                customer_id = session.customer
                subscription_id = session.subscription
                
                print(f"Processing successful subscription: customer={customer_id}, subscription={subscription_id}")
                
                try:
                    user = CustomUser.objects.get(stripe_customer_id=customer_id)
                    
                    # Get the plan from session metadata or other source
                    if 'selected_plan' in session.metadata:
                        plan = session.metadata.selected_plan
                    else:
                        # Try to determine the plan from the subscription
                        sub_details = stripe.Subscription.retrieve(subscription_id)
                        price_id = sub_details.items.data[0].price.id
                        # Find the plan key by price ID value
                        plan = next((k for k, v in STRIPE_PRICE_IDS.items() if v == price_id), 'basic')
                    
                    print(f"Plan determined: {plan}")
                    
                    # Update user's subscription details
                    user.subscription_plan = plan
                    
                    # Set usage quota based on plan
                    if plan == 'basic':
                        user.usage_quota = 5000
                    elif plan == 'premium':
                        user.usage_quota = 20000
                    elif plan == 'enterprise':
                        user.usage_quota = 100000
                    
                    # Reset usage count for new billing period
                    user.usage_count = 0
                    
                    # Update Stripe subscription ID
                    user.stripe_subscription_id = subscription_id
                    
                    # Set renewal date (30 days from now as default)
                    user.subscription_renewal = timezone.now() + timezone.timedelta(days=30)
                    
                    # Update payment method status
                    user.has_active_payment_method = True
                    
                    user.save()
                    
                    # Create a Subscription record
                    sub = Subscription.objects.create(
                        user=user,
                        plan=plan,
                        status='active',
                        stripe_subscription_id=subscription_id,
                        start_date=timezone.now(),
                        next_billing_date=timezone.now() + timezone.timedelta(days=30),
                    )
                    
                    print(f"Created subscription record for user: {user.email}")
                    
                    # Log user activity
                    UserActivity.objects.create(
                        user=user, 
                        action='subscription_upgraded',
                        details={
                            'plan': plan,
                            'subscription_id': subscription_id
                        }
                    )
                    
                except CustomUser.DoesNotExist:
                    print(f"Could not find user with Stripe customer ID: {customer_id}")
                
            except Exception as e:
                print(f"Error processing checkout.session.completed: {str(e)}")
    
    elif event.type == 'invoice.paid':
        # Handle successful payment
        invoice = event.data.object
        subscription_id = invoice.subscription
        customer_id = invoice.customer
        
        print(f"Processing paid invoice: {invoice.id} for subscription: {subscription_id}")
        
        try:
            user = CustomUser.objects.get(stripe_customer_id=customer_id)
            subscription = Subscription.objects.get(
                stripe_subscription_id=subscription_id,
                user=user
            )
            
            # Create invoice record
            SubscriptionInvoice.objects.create(
                user=user,
                subscription=subscription,
                stripe_invoice_id=invoice.id,
                amount=invoice.amount_paid / 100.0,  # Convert from cents
                status='paid',
                description=f"Payment for {subscription.plan.title()} plan",
                invoice_date=timezone.now(),
                due_date=timezone.now(),
                invoice_pdf_url=invoice.invoice_pdf,
            )
            
            # Reset usage count for new billing period
            user.reset_usage_count()
            
            # Update next billing date
            subscription.next_billing_date = timezone.datetime.fromtimestamp(
                invoice.period_end, tz=timezone.utc
            ) + timezone.timedelta(days=1)
            subscription.save()
            
            # Update user's renewal date
            user.subscription_renewal = subscription.next_billing_date
            user.save()
            
            # Log activity
            UserActivity.objects.create(
                user=user,
                action='payment_successful',
                details={
                    'invoice_id': invoice.id,
                    'amount': invoice.amount_paid / 100.0,
                    'plan': subscription.plan
                }
            )
            print(f"Successfully processed paid invoice for user: {user.email}")
            
        except CustomUser.DoesNotExist:
            print(f"Could not find user with Stripe customer ID: {customer_id}")
        except Subscription.DoesNotExist:
            print(f"Could not find subscription with ID: {subscription_id} for user with Stripe customer ID: {customer_id}")
        except Exception as e:
            print(f"Error processing paid invoice: {str(e)}")
    
    elif event.type == 'invoice.payment_failed':
        # Handle failed payment
        invoice = event.data.object
        subscription_id = invoice.subscription
        customer_id = invoice.customer
        
        try:
            user = CustomUser.objects.get(stripe_customer_id=customer_id)
            subscription = Subscription.objects.get(
                stripe_subscription_id=subscription_id,
                user=user
            )
            
            # Create invoice record
            SubscriptionInvoice.objects.create(
                user=user,
                subscription=subscription,
                stripe_invoice_id=invoice.id,
                amount=invoice.amount_due / 100.0,  # Convert from cents
                status='failed',
                description=f"Failed payment for {subscription.plan.title()} plan",
                invoice_date=timezone.now(),
                due_date=timezone.datetime.fromtimestamp(
                    invoice.next_payment_attempt, tz=timezone.utc
                ) if invoice.next_payment_attempt else timezone.now() + timezone.timedelta(days=3),
            )
            
            # Log activity
            UserActivity.objects.create(
                user=user,
                action='payment_failed',
                details={
                    'invoice_id': invoice.id,
                    'amount': invoice.amount_due / 100.0,
                    'plan': subscription.plan
                }
            )
            
        except (CustomUser.DoesNotExist, Subscription.DoesNotExist):
            # Log this error somewhere
            pass
    
    elif event.type == 'customer.subscription.deleted':
        # Handle subscription cancellation
        subscription = event.data.object
        customer_id = subscription.customer
        
        try:
            user = CustomUser.objects.get(stripe_customer_id=customer_id)
            user_subscription = Subscription.objects.get(
                stripe_subscription_id=subscription.id,
                user=user
            )
            
            # Update subscription status
            user_subscription.status = 'cancelled'
            user_subscription.end_date = timezone.datetime.fromtimestamp(
                subscription.ended_at, tz=timezone.utc
            ) if subscription.ended_at else timezone.now()
            user_subscription.save()
            
            # Downgrade user to free plan
            user.subscription_plan = 'free'
            user.usage_quota = 100
            user.save()
            
            # Log activity
            UserActivity.objects.create(
                user=user,
                action='subscription_ended',
                details={
                    'plan': user_subscription.plan,
                    'subscription_id': subscription.id
                }
            )
            
        except (CustomUser.DoesNotExist, Subscription.DoesNotExist):
            # Log this error somewhere
            pass
    
    return HttpResponse(status=200)

def pricing(request):
    """View for the pricing page accessible to all users"""
    # Determine if user is authenticated to show different CTAs
    is_authenticated = request.user.is_authenticated
    current_plan = request.user.subscription_plan if is_authenticated else None
    
    context = {
        'plans': PLAN_FEATURES,
        'is_authenticated': is_authenticated,
        'current_plan': current_plan,
    }
    
    return render(request, 'marketing/pricing.html', context)

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

@login_required
def smtp_settings(request):
    """
    View for managing SMTP settings
    """
    try:
        smtp_settings = SmtpSettings.objects.get(user=request.user)
    except SmtpSettings.DoesNotExist:
        smtp_settings = None
    
    if request.method == 'POST':
        if smtp_settings:
            form = SmtpSettingsForm(request.POST, instance=smtp_settings)
        else:
            form = SmtpSettingsForm(request.POST)
        
        if form.is_valid():
            smtp_config = form.save(commit=False)
            smtp_config.user = request.user
            smtp_config.save()
            
            messages.success(request, 'SMTP settings updated successfully.')
            return redirect('smtp_settings')
    else:
        if smtp_settings:
            form = SmtpSettingsForm(instance=smtp_settings)
        else:
            # Set default values based on settings.py
            initial_data = {
                'host': settings.EMAIL_HOST,
                'port': settings.EMAIL_PORT,
                'username': settings.EMAIL_HOST_USER,
                'password': '',  # Don't prefill password
                'use_tls': settings.EMAIL_USE_TLS,
                'from_email': settings.DEFAULT_FROM_EMAIL,
                'from_name': request.user.get_full_name() or request.user.username
            }
            form = SmtpSettingsForm(initial=initial_data)
    
    context = {
        'form': form,
        'smtp_settings': smtp_settings
    }
    
    return render(request, 'users/smtp_settings.html', context)

@login_required
def test_smtp_connection(request):
    """
    Test SMTP connection with current settings
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    try:
        smtp_settings = SmtpSettings.objects.get(user=request.user)
        
        # Test connection
        import smtplib
        from email.mime.text import MIMEText
        
        try:
            # Create test connection
            if smtp_settings.use_ssl:
                server = smtplib.SMTP_SSL(smtp_settings.host, smtp_settings.port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_settings.host, smtp_settings.port, timeout=10)
                
                if smtp_settings.use_tls:
                    server.starttls()
            
            # Login
            server.login(smtp_settings.username, smtp_settings.password)
            
            # Send test email if requested
            if 'send_test' in request.POST:
                msg = MIMEText('This is a test email from your EmailPro application.')
                msg['Subject'] = 'EmailPro SMTP Test'
                msg['From'] = f"{smtp_settings.from_name} <{smtp_settings.from_email}>"
                msg['To'] = request.user.email
                
                server.send_message(msg)
                
                # Log activity
                UserActivity.objects.create(
                    user=request.user,
                    action='smtp_test',
                    description='Sent SMTP test email',
                    ip_address=get_client_ip(request)
                )
                
                success_message = 'SMTP connection successful. Test email sent to your email address.'
            else:
                success_message = 'SMTP connection successful.'
            
            # Close connection
            server.quit()
            
            return JsonResponse({'success': True, 'message': success_message})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Connection failed: {str(e)}'})
        
    except SmtpSettings.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'SMTP settings not found. Please save your settings first.'})
