from django.contrib import admin
from .models import OdooConnector, OdooUserConfig

admin.site.register([OdooConnector, OdooUserConfig])
