from django import forms
from .models import User, Invoice
from django.contrib.auth.forms import UserCreationForm

class UserRegisterForm(UserCreationForm):
    organisation_name = forms.CharField(max_length=100)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'password1', 'password2']

class UserLoginForm(forms.Form):
    organisation_name = forms.CharField(max_length=100, required=False)
    email = forms.EmailField(max_length=100)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

class UserProfileForm(forms.ModelForm):
    organisation_name = forms.CharField(max_length=100)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'password']
    
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        user = kwargs.pop('instance', None)
        if user and user.organisation:
            self.fields['organisation_name'].initial = user.organisation.name


class InvoiceForm(forms.ModelForm):
    custom_date = forms.DateField(label="Date", disabled=True, required=False)
    custom_modified = forms.DateTimeField(label="Modified", disabled=True, required=False)
    class Meta:
        model = Invoice
        fields = ['origin_id', 'invoice_number', 'tax', 'customer', 'type', 'currency',
                  'amount', 'tax_amount', 'total', 'status', 'failure_reason', 'reversed_invoice']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        if instance:
            self.fields['custom_date'].initial = instance.date
            self.fields['custom_modified'].initial = instance.modified
        for field in self.fields.values():
            field.disabled = True