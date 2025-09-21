from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from app.models import Connector, Organisation

class QuickbookConnector(models.Model):
    
    CONNECTION_TYPES = [ 
        ('Online', 'online'),
        ('Desktop', 'desktop')
    ]
    
    name = models.CharField(max_length=100, default="quickbooks")
    connection_type = models.CharField(max_length=10, choices=CONNECTION_TYPES, default='online')
    connectors = GenericRelation(Connector)
    region = models.CharField(max_length=100, default='GB')
    
    
    def __str__(self):
        return f"{self.name} - {self.connection_type} - {self.region} version"

class QuickbookUserConfig(models.Model):
    connector = models.ForeignKey(QuickbookConnector, on_delete=models.CASCADE)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    realm_id = models.CharField(max_length=200)
    refresh_token = models.CharField(max_length=200)
    
    class Meta:
        unique_together = ('connector', 'organisation', 'realm_id')
    
    def __str__(self):
        return f"{self.connector.name} - Configuration - {self.organisation.name}"