from django import forms
from .models import OdooUserConfig

class OdooConfigForm(forms.ModelForm):
    class Meta:
        model = OdooUserConfig
        fields = ['url', 'port', 'database', 'email', 'password']
        
    def __init__(self, *args, **kwargs):
        super(OdooConfigForm, self).__init__(*args, **kwargs)
        self.fields['port'].initial = 80