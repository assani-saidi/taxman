from django.contrib import admin
from .models import Region, Station, ZimraConfig, ZimraConnector

admin.site.register([ZimraConnector, ZimraConfig, Region, Station])