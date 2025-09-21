from intuitlib.client import AuthClient
from quickbooks import QuickBooks
from intuitlib.enums import Scopes
from django.conf import settings
from quickbooks.objects.invoice import Invoice
from quickbooks.objects.taxcode import TaxCode
from quickbooks.objects.customer import Customer
from quickbooks.objects.detailline import SalesItemLine
from app import models
from django.contrib.contenttypes.models import ContentType


# Quickbooks API configuration
API_URL = settings.QUICKBOOKS_BASE_URL
API_CLIENT_ID = settings.QUICKBOOKS_CLIENT_ID
API_SECRET = settings.QUICKBOOKS_CLIENT_SECRET
API_ENVIRONMENT = settings.QUICKBOOKS_ENVIROMENT
API_REDIRECT_URL=settings.QUICKBOOKS_REDIRECT_URL
API_SCOPES = [Scopes.ACCOUNTING]

def get_auth_client():
    return AuthClient(
        client_id=API_CLIENT_ID,
        client_secret=API_SECRET,
        environment=API_ENVIRONMENT,
        redirect_uri=API_REDIRECT_URL
    )

def get_quickbooks(auth_client):
    return QuickBooks(
        auth_client=auth_client,
        refresh_token=auth_client.refresh_token,
        company_id=auth_client.realm_id,
    )


def _save_invoice(client):
    invoice = Invoice.get(183, qb=client)
    qb_customer = Customer.get(int(invoice.CustomerRef.value), qb=client)
    # qb_taxcode = TaxCode.get(qb_customer.DefaultTaxCodeRef.value)
    print(invoice.TxnTaxDetail.TaxLine[0].TaxLineDetail.__dict__)
    # print(invoice.CustomField[0].__dict__)
    # print(invoice.Line[0].SalesItemLineDetail.ItemRef.__dict__)
    # print(invoice.Line[0].SalesItemLineDetail.TaxCodeRef.__dict__)
    # print(invoice.Line[0].SalesItemLineDetail.TaxCodeRef.__dict__)
    # result = qb_customer.PrimaryTaxIdentifier
    # result = qb_customer.to_json()
    # print(result)
    return invoice.to_json()


def save_invoice(config, client, invoice_ids):
    for invoice_id in invoice_ids:
        # get invoice from quickbooks
        qb_invoice = Invoice.get(invoice_id, qb=client)
        qb_customer = Customer.get(int(qb_invoice.CustomerRef.value), qb=client)
        
        # if customer is not taxable skip
        if not qb_customer.Taxable:
            print(f"""
                  {qb_invoice.CustomerRef.name} is not taxable skipping invoice {qb_invoice.DocNumber}
            """)
            continue
        
        # We get vat from the taxman field or from notes
        customer_client_vat_number = ""
        if len(qb_invoice.CustomField) > 0:
            for field in qb_invoice.CustomField:
                if field.Name == "TaxmanFiscalise VAT":
                    customer_client_vat_number = field.StringValue
                    break
        
        if customer_client_vat_number == "":
            if qb_customer.Notes != "":
                customer_client_vat_number = qb_customer.Notes
        
        # objects needed by the app invoice
        ConnectorContentType = ContentType.objects.get_for_model(config.connector)
        connector = models.Connector.objects.get(app_model=ConnectorContentType, app_id=config.connector.id)
        connected_app = models.ConnectedApp.objects.get(organisation=config.organisation, connector=connector)
        try:
            currency = models.TaxCurrencies.objects.get(symbol=qb_invoice.CurrencyRef.value)
        except models.TaxCurrencies.DoesNotExist:
            currency = models.TaxCurrencies(
                name=qb_invoice.CurrencyRef.name,
                symbol=qb_invoice.CurrencyRef.value,
                country="ZW"
            )
            currency.save()
             
     
        # if origin id with same connected app exists skip
        if models.Invoice.objects.filter(origin_id=qb_invoice.Id, connected_app=connected_app).exists():
            print(f"""
                  Invoice {qb_invoice.DocNumber} already exists in the app
            """)
            continue
        
        # create app customer
        tax_id = customer_client_vat_number
        existing_customer = models.Customer.objects.filter(name=qb_invoice.CustomerRef.name, tax_id=tax_id).first()
        if existing_customer:
            customer = existing_customer
        else:
            customer = models.Customer(
                name=qb_invoice.CustomerRef.name,
                tax_id=tax_id,
                address=qb_customer.BillAddr.Line1
            )
            customer.save()
            
        # create tax type
        tax_line =  qb_invoice.TxnTaxDetail.TaxLine[0].TaxLineDetail
        tax_percent = tax_line.TaxPercent
        tax_fixed_amount = 0
        t_name = tax_line.TaxRateRef.name or f"VAT (quickbooks)"
        t_tax_type = "exclusive" if qb_invoice.GlobalTaxCalculation == "TaxExcluded" else "inclusive"
        t_computation_type = "percentage" if tax_line.PercentBased else "fixed_amount"
        t_tax_percent = tax_percent
        t_fixed_amount = tax_fixed_amount
        existing_tax_type = models.TaxType.objects.filter(
            name=t_name,
            tax_type=t_tax_type,
            computation_type=t_computation_type,
            tax_percent=t_tax_percent,
            fixed_amount=t_fixed_amount
        ).first()
        
        if existing_tax_type:
            tax_type = existing_tax_type
        else:
            tax_type = models.TaxType(
                name = t_name,
                tax_type = t_tax_type,
                computation_type = t_computation_type,
                tax_percent = t_tax_percent,
                fixed_amount = t_fixed_amount
            )
            tax_type.save()
         
        # create app invoice to save in app
        app_invoice = models.Invoice(
            connected_app=connected_app,
            origin_id=qb_invoice.Id,
            customer=customer,
            invoice_number=qb_invoice.DocNumber,
            type="invoice",
            status="pending",
            tax=tax_type,
            amount=qb_invoice.TotalAmt - qb_invoice.TxnTaxDetail.TotalTax,
            tax_amount=qb_invoice.TxnTaxDetail.TotalTax,
            total=qb_invoice.TotalAmt,
            currency=currency
        )
        app_invoice.save()
        
        # create products for the invoice
        for line in qb_invoice.Line:
            if not isinstance(line, SalesItemLine):
                continue
            tax_identifier = line.SalesItemLineDetail.TaxCodeRef.value
            tax_amount = 0
            if tax_identifier != "":
                tax_amount = line.Amount * (tax_percent / 100)
                tax_amount = round(tax_amount, 2)
            product = models.InvoiceProduct(
                invoice=app_invoice,
                name=line.SalesItemLineDetail.ItemRef.name,
                quantity=line.SalesItemLineDetail.Qty,
                price=line.SalesItemLineDetail.UnitPrice,
                amount=(line.SalesItemLineDetail.UnitPrice * line.SalesItemLineDetail.Qty) - tax_amount,
                tax_amount=tax_amount,
                tax="inclusive" if line.SalesItemLineDetail.TaxInclusiveAmt > 0 else "exclusive",
                total=line.Amount
            )
            product.save()
    print("process completed")