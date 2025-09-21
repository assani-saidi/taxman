from django.contrib import admin
from .models import TaxType, Organisation, Customer, TaxCurrencies, ConnectedTax, TaxConnector, Connector, ConnectedApp, InvoiceProduct, Invoice


class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'connectedtax')
    search_fields = ('name', 'user', 'connectedtax')
    list_filter = ('name', 'user', 'connectedtax')
    ordering = ('name', 'user', 'connectedtax')

admin.site.register(Organisation, OrganisationAdmin)


class ConnectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'app', 'app_id', 'app_model')
    search_fields = ('name', 'app')
    list_filter = ('name', 'app_model')
    ordering = ('name', 'app_model')

admin.site.register(Connector, ConnectorAdmin)

class TaxConnectorAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax', 'tax_id', 'tax_model')
    search_fields = ('name', 'tax',)
    list_filter = ('name', 'tax_model',)
    ordering = ('name', 'tax_model',)

admin.site.register(TaxConnector, TaxConnectorAdmin)

class ConnectedTaxAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'connector', 'status')
    search_fields = ('organisation', 'connector', 'status')
    list_filter = ('organisation', 'connector', 'status')
    ordering = ('organisation', 'connector', 'status')

admin.site.register(ConnectedTax, ConnectedTaxAdmin)

class ConnectedAppAdmin(admin.ModelAdmin):
    list_display = ('organisation', 'connector', 'status')
    search_fields = ('organisation', 'connector', 'status')
    list_filter = ('organisation', 'connector', 'status')
    ordering = ('organisation', 'connector', 'status')

admin.site.register(ConnectedApp, ConnectedAppAdmin)

class InvoiceProductAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'name', 'hs_code', 'quantity', 'amount', 'tax_amount', 'total')
    search_fields = ('invoice', 'name', 'hs_code', 'quantity', 'amount', 'tax_amount', 'total')
    list_filter = ('invoice', 'name', 'hs_code', 'quantity', 'amount', 'tax_amount', 'total')
    ordering = ('invoice', 'name', 'hs_code', 'quantity', 'amount', 'tax_amount', 'total')

admin.site.register(InvoiceProduct, InvoiceProductAdmin)

class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('connected_app', 'customer', 'tax', 'origin_id', 'date', 'invoice_number', 'type', 'status', 'total', 'currency',)
    search_fields = ('connected_app', 'customer', 'tax', 'origin_id', 'date', 'invoice_number','type', 'status', 'total', 'currency',)
    list_filter = ('connected_app', 'customer', 'tax', 'origin_id', 'date', 'invoice_number','type', 'status', 'total', 'currency',)
    ordering = ('connected_app', 'customer', 'tax', 'origin_id', 'date', 'invoice_number','type', 'status', 'total', 'currency',)

admin.site.register(Invoice, InvoiceAdmin) 
admin.site.register(TaxCurrencies)
admin.site.register(TaxType)

class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax_id', 'address')
    search_fields = ('name', 'tax_id')
    list_filter = ('name', 'tax_id')
    ordering = ('name', 'tax_id')

admin.site.register(Customer, CustomerAdmin)