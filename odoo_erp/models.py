from django.db import models
from app.models import Connector, Organisation, ConnectedApp
from django.contrib.contenttypes.fields import GenericRelation

class OdooConnector(models.Model):

    CONNECTION_TYPES = [ 
        ('Online', 'online'),
        ('On premise', 'offline'),
        ('SH', 'sh'),
    ]
    
    VERSIONS = [
        ("v15", "v15"),
        ("v16", "v16"),
        ("v17", "v17")
    ]
    
    name = models.CharField(max_length=100, default="quickbooks")
    connection_type = models.CharField(max_length=10, choices=CONNECTION_TYPES, default='online')
    connectors = GenericRelation(Connector)
    
    version = models.CharField(max_length=10, choices=VERSIONS)
    
    def __str__(self):
        return f"{self.name} - {self.connection_type} - {self.version}"

class OdooUserConfig(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    connector = models.ForeignKey(OdooConnector, on_delete=models.CASCADE)
    connected_app = models.ForeignKey(ConnectedApp, on_delete=models.CASCADE, related_name='connected_app')
    url = models.URLField()
    port = models.IntegerField(default=80)
    database = models.CharField(max_length=100)
    database_uuid = models.CharField(max_length=800, null=True, blank=True)
    email = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ('connector', 'organisation', 'database_uuid')
    
    def __str__(self):
        return f"{self.connector.name} - Configuration - {self.organisation.name}"