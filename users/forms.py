from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import CustomUser, SmtpSettings

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    """
    A form that creates a user, with no privileges, from the given email and password.
    """
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'})
    )
    company_name = forms.CharField(
        max_length=255, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Company Name'})
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'company_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }

class CustomAuthenticationForm(AuthenticationForm):
    """
    Custom authentication form with styled form fields
    """
    username = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'})
    )

class UserProfileForm(forms.ModelForm):
    """
    Form for updating user profile information
    """
    first_name = forms.CharField(
        max_length=30, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    company_name = forms.CharField(
        max_length=255, 
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    profile_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'company_name', 'profile_image')

class CustomPasswordChangeForm(PasswordChangeForm):
    """
    Custom password change form with styled form fields
    """
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current Password'})
    )
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password'})
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'})
    )

class CustomUserChangeForm(UserChangeForm):
    password = None  # Don't show the password field
    
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'company_name', 'profile_image')
        widgets = {
            'profile_image': forms.FileInput(),
        }

class SmtpSettingsForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(), required=True)
    
    class Meta:
        model = SmtpSettings
        fields = ('host', 'port', 'username', 'password', 'use_tls', 'use_ssl', 'from_email', 'from_name', 'is_active')
        widgets = {
            'host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., smtp.gmail.com'}),
            'port': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '587'}),
            'username': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'App password for Gmail'}),
            'from_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'from_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name or Company'}),
        }
        
    def clean(self):
        cleaned_data = super().clean()
        use_tls = cleaned_data.get('use_tls')
        use_ssl = cleaned_data.get('use_ssl')
        
        if use_tls and use_ssl:
            raise ValidationError("You cannot enable both TLS and SSL at the same time.")
            
        return cleaned_data 