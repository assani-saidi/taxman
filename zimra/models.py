from django.db import models
from app import models as app_models
from django_countries.fields import CountryField
from django.contrib.contenttypes.fields import GenericRelation
from app import models as app_models
import copy

zimra_invoice_validation_errors = [
    {"code": "RCPT010", "color": "Red", "requiresPreviousReceipt": False, "text": "Wrong currency code is used"},
    {"code": "RCPT011", "color": "Red", "requiresPreviousReceipt": True, "text": "Receipt counter is not sequential."},
    {"code": "RCPT012", "color": "Red", "requiresPreviousReceipt": True,
     "text": "Receipt global number is not sequential."},
    {"code": "RCPT013", "color": "Red", "requiresPreviousReceipt": False, "text": "Invoice number is not unique"},
    {"code": "RCPT014", "color": "Yellow", "requiresPreviousReceipt": False,
     "text": "Receipt date is earlier than fiscal day opening date"},
    {"code": "RCPT015", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Credited/debited invoice data is not provided"},
    {"code": "RCPT016", "color": "Red", "requiresPreviousReceipt": False, "text": "No receipt lines provided"},
    {"code": "RCPT017", "color": "Red", "requiresPreviousReceipt": False, "text": "Taxes information is not provided"},
    {"code": "RCPT018", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Payment information is not provided"},
    {"code": "RCPT019", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Invoice total amount is not equal to sum of all invoice lines"},
    {"code": "RCPT020", "color": "Red", "requiresPreviousReceipt": False, "text": "Invoice signature is not valid"},
    {"code": "RCPT021", "color": "Red", "requiresPreviousReceipt": False,
     "text": "VAT tax is used in invoice while taxpayer is not VAT taxpayer"},
    {"code": "RCPT022", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Invoice sales line price must be greater than 0 (less than 0 for Credit note), discount line price must be less than 0 (greater than 0 for Credit note)"},
    {"code": "RCPT023", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Invoice line quantity must be positive"},
    {"code": "RCPT024", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Invoice line total is not equal to unit price * quantity"},
    {"code": "RCPT025", "color": "Red", "requiresPreviousReceipt": False, "text": "Invalid tax is used"},
    {"code": "RCPT026", "color": "Red", "requiresPreviousReceipt": False, "text": "Incorrectly calculated tax amount"},
    {"code": "RCPT027", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Incorrectly calculated total sales amount (including tax)"},
    {"code": "RCPT028", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Payment amount must be greater than or equal 0 (less than or equal to 0 for Credit note)"},
    {"code": "RCPT029", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Credited/debited invoice information provided for regular invoice"},
    {"code": "RCPT030", "color": "Red", "requiresPreviousReceipt": True,
     "text": "Invoice date is earlier than previously submitted receipt date"},
    {"code": "RCPT031", "color": "Yellow", "requiresPreviousReceipt": False,
     "text": "Invoice is submitted with the future date"},
    {"code": "RCPT032", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Credit / debit note refers to non-existing invoice"},
    {"code": "RCPT033", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Credited/debited invoice is issued more than 12 months ago"},
    {"code": "RCPT034", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Note for credit/debit note is not provided"},
    {"code": "RCPT035", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Total credit note amount exceeds original invoice amount"},
    {"code": "RCPT036", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Credit/debit note uses other taxes than are used in the original invoice"},
    {"code": "RCPT037", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Invoice total amount is not equal to sum of all invoice lines and taxes applied"},
    {"code": "RCPT038", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Invoice total amount is not equal to sum of sales amount including tax in tax table"},
    {"code": "RCPT039", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Invoice total amount is not equal to sum of all payment amounts"},
    {"code": "RCPT040", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Invoice total amount must be greater than or equal to 0 (less than or equal to 0 for Credit note)"},
    {"code": "RCPT041", "color": "Yellow", "requiresPreviousReceipt": False,
     "text": "Invoice is issued after fiscal day end"},
    {"code": "RCPT042", "color": "Red", "requiresPreviousReceipt": False,
     "text": "Credit/debit note uses other currency than is used in the original invoice"},
    {"code": "RCPT048", "color": "Red", "requiresPreviousReceipt": False,
     "text": "HSCode required and must be either 4 or 8 digits long"}]

def default_zimra_invoice_validation_errors():
    return copy.deepcopy(zimra_invoice_validation_errors)

class Region(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Station(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class ZimraConnector(models.Model):
    name = models.CharField(max_length=100, default="zimra")
    connectors = GenericRelation(app_models.TaxConnector)
    country = CountryField(null=True, blank=True, default='ZW')

    def __str__(self):
        return self.name


class ZimraConfig(models.Model):
    # Internal Operational fields
    organisation = models.ForeignKey(app_models.Organisation, on_delete=models.CASCADE)
    connector = models.ForeignKey(ZimraConnector, on_delete=models.CASCADE)

    # pre regitration fields 
    excel_registration_form = models.FileField(upload_to='files/', null=True, blank=True)
    zimra_registration_contact_email = models.EmailField(max_length=100, null=True, blank=True,
                                                         default="tsilongwe4324234@zimra.co.zw")

    # post registration fields
    taxpayer_tin_number = models.CharField(max_length=100, null=True, blank=True)
    taxpayer_name = models.CharField(max_length=100, null=True, blank=True)
    taxpayer_vat_number = models.CharField(max_length=100, null=True, blank=True)
    trade_name = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=100, null=True, blank=True)
    model_name = models.CharField(max_length=100, null=True, blank=True)
    model_version_no = models.CharField(max_length=100, null=True, blank=True)
    platform = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=100, null=True, blank=True)
    serial_number = models.CharField(max_length=100, null=True, blank=True)
    device_id = models.CharField(max_length=100, null=True, blank=True)
    activation_key = models.CharField(max_length=100, null=True, blank=True)

    # api identification fields
    certificate = models.FileField(upload_to='certificates/', null=True, blank=True)
    certificate_key = models.FileField(upload_to='certificates/', null=True, blank=True)

    # fiscalisation tracking fields
    # fiscalisation fields from zimra api
    receipt_counter = models.IntegerField(blank=True, null=True, default=0)
    receipt_global_counter = models.IntegerField(blank=True, null=True, default=0)
    receipt_previous_hash = models.TextField(null=True, blank=True, default="")
    file_counter = models.IntegerField(blank=True, null=True, default=0)
    zimra_api_device_information = models.JSONField(null=True, blank=True)
    zimra_fiscal_day_information = models.JSONField(null=True, blank=True)

    # utility fields
    zimra_invoice_validation_errors = models.JSONField(null=True, blank=True, default=default_zimra_invoice_validation_errors)

    def __str__(self):
        return f"{self.organisation.name} - ZIMRA - Configuration"


class ZimraFiscalDay(models.Model):
    pass
