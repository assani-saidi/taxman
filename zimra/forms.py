from django import forms
from .models import Region, Station, ZimraConfig 
 
class ZimraRegistrationForm(forms.Form):
    taxpayer_tin_number = forms.CharField(max_length=100)
    taxpayer_name = forms.CharField(max_length=100)
    taxpayer_vat_number = forms.CharField(max_length=100)
    taxpayer_email = forms.EmailField()
    trade_name = forms.CharField(max_length=100)
    phone_number = forms.CharField(max_length=100)
    email = forms.EmailField()
    province = forms.CharField(max_length=100)
    street = forms.CharField(max_length=100)
    house_number = forms.CharField(max_length=100)
    city = forms.CharField(max_length=100)
    region = forms.ModelChoiceField(queryset=Region.objects.all())
    station = forms.ModelChoiceField(queryset=Station.objects.all())
    serial_number = forms.CharField(max_length=100)
    model_name = forms.CharField(max_length=100, initial='Server', disabled=True)
    supplier = forms.CharField(max_length=100, initial='Self (Server to Server)', disabled=True)
    
class ZimraDeviceForm(forms.ModelForm):
    
    class Meta:
        model = ZimraConfig
        fields = [
            'device_id', 'activation_key'
        ]