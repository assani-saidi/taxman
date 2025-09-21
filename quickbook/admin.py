from django.contrib import admin
from .models import QuickbookConnector, QuickbookUserConfig

admin.site.register([QuickbookConnector, QuickbookUserConfig])
