from django import forms
from .models import Subscriber, SubscriberList, EmailTemplate, Campaign
import csv
import io
from django.utils import timezone

class SubscriberForm(forms.ModelForm):
    """
    Form for creating and updating subscribers
    """
    class Meta:
        model = Subscriber
        fields = ('email', 'first_name', 'last_name', 'is_active', 'country', 'city')
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'style': 'height: 38px;'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'style': 'height: 38px;'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'style': 'height: 38px;'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'style': 'height: 38px;'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'style': 'height: 38px;'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class SubscriberImportForm(forms.Form):
    """
    Form for importing subscribers from a CSV file
    """
    csv_file = forms.FileField(
        label='CSV File',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv', 'style': 'height: auto; padding: 8px;'})
    )
    subscriber_list = forms.ModelChoiceField(
        queryset=SubscriberList.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'style': 'height: 38px;'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['subscriber_list'].queryset = SubscriberList.objects.filter(owner=user)

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError('The file must be a CSV file.')
        
        # Validate CSV structure
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.reader(io_string)
            header = next(reader)
            
            required_fields = ['email']
            for field in required_fields:
                if field not in header:
                    raise forms.ValidationError(f'Required field {field} is missing in the CSV.')
                    
            return csv_file
        except Exception as e:
            raise forms.ValidationError(f'Error processing CSV file: {str(e)}')

class SubscriberListForm(forms.ModelForm):
    """
    Form for creating and updating subscriber lists
    """
    class Meta:
        model = SubscriberList
        fields = ('name', 'description')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class EmailTemplateForm(forms.ModelForm):
    """
    Form for creating and updating email templates
    """
    class Meta:
        model = EmailTemplate
        fields = ('name', 'subject', 'content', 'html_content')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'html_content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'id': 'html-editor'}),
        }

class CampaignForm(forms.ModelForm):
    """
    Form for creating and updating email campaigns
    """
    class Meta:
        model = Campaign
        fields = (
            'name', 'subject', 'from_email', 'from_name', 'reply_to',
            'content', 'html_content', 'lists', 'template'
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'from_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'from_name': forms.TextInput(attrs={'class': 'form-control'}),
            'reply_to': forms.EmailInput(attrs={'class': 'form-control'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'html_content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'id': 'html-editor'}),
            'lists': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'template': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['lists'].queryset = SubscriberList.objects.filter(owner=user)
            self.fields['template'].queryset = EmailTemplate.objects.filter(owner=user)

class CampaignScheduleForm(forms.ModelForm):
    """
    Form for scheduling a campaign
    """
    class Meta:
        model = Campaign
        fields = ('schedule_time',)
        widgets = {
            'schedule_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }

    def clean_schedule_time(self):
        """
        Ensure schedule_time is timezone aware
        """
        schedule_time = self.cleaned_data.get('schedule_time')
        if schedule_time and timezone.is_naive(schedule_time):
            schedule_time = timezone.make_aware(schedule_time)
        return schedule_time

class ContactForm(forms.Form):
    """
    Contact form for visitors
    """
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your Name'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Your Email'})
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'})
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Your Message', 'rows': 5})
    ) 