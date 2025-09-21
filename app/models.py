from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver 
from django_countries.fields import CountryField
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from datetime import datetime
import requests
from setuptools.command.build_ext import if_dl

TAX_TYPE = [
    ('free', "Taxfree"),
    ('inclusive', "Inclusive"),
    ('exclusive', "Exclusive")
]

TAX_COMPUTATION_TYPE = [
    ('percentage', "Percentage"),
    ('fixed_amount', "Fixed Amount")
]

INVOICE_STATUSES = [
    ('pending', 'Pending'),
    ('submitted', 'Submitted'),
    ('fiscalised', 'Fiscalised'),
    ('failed', 'Failed')
]

INVOICE_TYPE = [
    ('invoice', 'Invoice'),
    ('receipt', 'Receipt'),
    ('credit_note', 'Credit Note'),
    ('debit_note', 'Debit Note')
]

INVOICE_PAYMENT_TYPES = [
    ('cash', 'Cash'),
    ('bank_transfer', 'Bank Transfer'),
    ('mobile_money', 'Mobile Money'),
    ('card_payment', 'Card Payment'),
    ('other', 'Other')
]

INVOICE_PRODUCT_TYPE = [
    ('sale', 'Sale'),
    ('discount', 'Discount')
]

class TaxCurrencies(models.Model):
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=20)
    country = CountryField(null=True, blank=True)
    
    def __str__(self):
        return self.symbol
    
class Organisation(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    
    @receiver(post_save, sender=User)
    def create_user_organisation(sender, instance, created, **kwargs):
        if created:
            Organisation.objects.create(user=instance)
    
    @receiver(post_save, sender=User)
    def save_user_organisation(sender, instance, **kwargs):
        instance.organisation.save()
        
    def __str__(self):
        return self.name
 
class Connector(models.Model):
    name = models.CharField(max_length=100)
    app_model = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    app_id = models.PositiveIntegerField(null=True, blank=True)
    app = GenericForeignKey('app_model', 'app_id')

    def user_connected_apps(self, user_id):
        return self.connected_apps.count()

    def __str__(self):
        return self.name

class TaxConnector(models.Model):
    name = models.CharField(max_length=100)
    tax_model = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    tax_id = models.PositiveIntegerField(null=True, blank=True)
    tax = GenericForeignKey('tax_model', 'tax_id') 
    
    def __str__(self):
        return f"{self.name} - {self.tax.country}" 

class ConnectedTax(models.Model):
    connector = models.ForeignKey(TaxConnector, on_delete=models.CASCADE)
    organisation = models.OneToOneField(Organisation, on_delete=models.CASCADE)
    status = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.connector.tax.name}"
    
class ConnectedApp(models.Model):
    connector = models.ForeignKey(Connector, on_delete=models.CASCADE, related_name='connected_apps')
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    status = models.BooleanField(default=True)
     
    def __str__(self):
        return self.connector.name

class TaxType(models.Model):
    name = models.CharField(max_length=100)
    tax_type = models.CharField(max_length=100, choices=TAX_TYPE, default='free')
    computation_type = models.CharField(max_length=100, choices=TAX_COMPUTATION_TYPE, default="percentage", null=True, blank=True)
    tax_percent = models.FloatField(null=True, blank=True)
    fixed_amount = models.FloatField(null=True, blank=True)
    
    def calculate_tax(self, amount: float):
        return self.tax_percent * amount if self.computation_type == "percentage" else self.fixed_amount

    def __str__(self):
        return f"{self.name} - As Fixed Amount - {self.fixed_amount}" if self.computation_type == "fixed_amount" else f"{self.name} - As Percentage - {self.tax_percent}%"
    
class InvoiceProduct(models.Model): 
    invoice = models.ForeignKey("Invoice", on_delete=models.CASCADE, related_name='invoiceproducts')
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=100, choices=INVOICE_PRODUCT_TYPE, default='sale')
    description = models.TextField(null=True, blank=True)
    hs_code = models.CharField(max_length=100, null=True, blank=True)
    quantity = models.FloatField()
    price = models.DecimalField(max_digits=30, decimal_places=2)
    amount = models.DecimalField(max_digits=30, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=30, decimal_places=2)
    tax = models.CharField(max_length=100, choices=TAX_TYPE, default='free')
    total = models.DecimalField(max_digits=30, decimal_places=2)
    
    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.name}"
 
class Invoice(models.Model):    
    connected_app = models.ForeignKey(ConnectedApp, on_delete=models.CASCADE)
    origin_id = models.IntegerField()
    invoice_number = models.CharField(max_length=100)
    date = models.DateTimeField(null=True, blank=True, default=datetime.now)
    tax = models.ForeignKey(TaxType, on_delete=models.SET_NULL, null=True, blank=True)
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    type = models.CharField(max_length=100, choices=INVOICE_TYPE, default='invoice')
    status = models.CharField(max_length=100, choices=INVOICE_STATUSES, default='pending')
    failure_reason = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(max_digits=30, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=30, decimal_places=2)
    total = models.DecimalField(max_digits=30, decimal_places=2)
    payment_type = models.CharField(max_length=100, choices=INVOICE_PAYMENT_TYPES, default='cash')
    reversed_invoice = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    currency = models.ForeignKey(TaxCurrencies, on_delete=models.SET_NULL, null=True, blank=True)
    qr_code_url = models.URLField(null=True, blank=True)
    sent_data = models.JSONField(null=True, blank=True)
    tax_success_data = models.JSONField(null=True, blank=True)
    tax_failure_data = models.JSONField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    
    def lines_tax(self):
        return sum([product.tax_amount for product in self.invoiceproducts.all()])
    
    def lines_amount(self):
        return sum([product.amount for product in self.invoiceproducts.all()])
    
    def lines_total(self):
        return sum([product.total for product in self.invoiceproducts.all()])

    @property
    def qr_code(self, size=None):
        if size is None:
            size = [150, 150]
        size = f"{size[0]}x{size[1]}"
        qr_code_api_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}&data={self.qr_code_url}"
        return qr_code_api_image_url if self.qr_code_url else None

    @property
    def organisation(self):
        return self.connected_app.organisation or False
    
    def __str__(self):
        return self.invoice_number
    
class Customer(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(null=True, blank=True)
    tax_id = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name