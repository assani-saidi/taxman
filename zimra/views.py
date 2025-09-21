from django.shortcuts import render, redirect
from collections import defaultdict
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from app import models as app_models
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from payments.decorators import payment_required
from .cron import auto_close_fiscal_day
from .helpers import create_excel_registration_form, send_registration_form, generate_csr_certificate_and_private_key
from .forms import ZimraRegistrationForm, ZimraDeviceForm
from .models import ZimraConfig
from .zimra import register_device, get_status, open_day, close_day, submit_receipt, check_submitted_receipts_offline, \
    submit_receipts_offline, test_submit_receipt


@login_required
@payment_required
def set_connector(request):
    tax_connector_id = int(request.GET.get('connector'))
    response = redirect('add-zimra-connector')
    response.set_cookie("connector", tax_connector_id, path="/zimra")
    return response
    
@login_required
@payment_required
def add_connector(request):
    if request.method == 'POST':
        form = ZimraRegistrationForm(request.POST)
        if form.is_valid():
            tax_connector_id = int(request.COOKIES.get('connector'))
            tax_connector = app_models.TaxConnector.objects.get(pk=tax_connector_id)
            zimra_config = ZimraConfig(
                taxpayer_tin_number=form.cleaned_data['taxpayer_tin_number'],
                taxpayer_name=form.cleaned_data['taxpayer_name'],
                taxpayer_vat_number=form.cleaned_data['taxpayer_vat_number'],
                trade_name=form.cleaned_data['trade_name'],
                phone_number=form.cleaned_data['phone_number'],
                model_name=form.cleaned_data['model_name'],
                serial_number=form.cleaned_data['serial_number'],
                organisation=request.user.organisation, 
                connector=tax_connector.tax
            )
            excel_file = create_excel_registration_form(form.cleaned_data)
            result = send_registration_form(excel_file, zimra_config.zimra_registration_contact_email, form.cleaned_data['email'])
            zimra_config.excel_registration_form = excel_file
            zimra_config.save()
            connected_tax = app_models.ConnectedTax(organisation=request.user.organisation, connector=tax_connector)
            connected_tax.status = False
            connected_tax.save()
            return redirect('dashboard')
    form = ZimraRegistrationForm()
    return render(request, 'zimra/configure.html', {'form': form})

@login_required
@payment_required
def view_details(request):
    tax_connector_id = int(request.GET.get('connector'))
    zimra_config = ZimraConfig.objects.get(connector=tax_connector_id, organisation=request.user.organisation.id)
    return render(request, 'zimra/details.html', {'config': zimra_config})

@login_required
@payment_required
def complete_registration(request):
    connected_tax_id = int(request.GET.get('connected_tax', None))
    app_connected_tax = app_models.ConnectedTax.objects.get(pk=int(connected_tax_id))
    tax_config = ZimraConfig.objects.get(organisation=request.user.organisation)
    if request.method == 'POST':
        form = ZimraDeviceForm(request.POST, instance=tax_config)
        if form.is_valid():
            zimra_config = form.save(commit=True)
            zimra_config.save()
            register_device(zimra_config)
            app_connected_tax.status = True
            app_connected_tax.save()
            return redirect('dashboard')
    form = ZimraDeviceForm(instance=tax_config)
    return render(request, 'zimra/complete_registration.html', {'form': form})


def fiscalise_invoice(request):
    invoice_id = request.GET.get('invoice_id')
    if not invoice_id:
        return HttpResponseBadRequest("Missing 'invoice_id' in query parameters.")

    try:
        invoice = app_models.Invoice.objects.get(id=invoice_id)
    except app_models.Invoice.DoesNotExist:
        return HttpResponseBadRequest("Invoice not found.")

    if invoice.status == "fiscalised":
        return JsonResponse({"message": "Invoice already fiscalised."})

    tax_config = ZimraConfig.objects.get(organisation=invoice.connected_app.organisation)

    # Fiscalise only this invoice
    result = submit_receipt(invoice, tax_config)

    return JsonResponse(result, safe=False)

def fiscalise_invoices(request):
    # for each zimra client get invoices to fiscalise
    results = []
    tax_configs = ZimraConfig.objects.all()
    for tax_config in tax_configs:
        # if tax_config.id == 2: continue
        # open_day(tax_config)
        # return JsonResponse(get_status(tax_config), safe=False)
        # return JsonResponse(check_submitted_receipts_offline(tax_config), safe=False)
        connectedapps = app_models.ConnectedApp.objects.filter(organisation__id=tax_config.organisation.id)
        connectedapps_ids = [x.id for x in connectedapps]
        invoices = app_models.Invoice.objects.filter(connected_app__id__in=connectedapps_ids).filter(Q(type="invoice") | Q(type="receipt")).exclude(status="fiscalised")
        if len(invoices) < 1: continue
        
        # Group invoices by their currency
        invoices_by_currency = defaultdict(list)
        for invoice in invoices:
            invoices_by_currency[invoice.currency].append(invoice)
        
        # # Fiscalize invoices for each currency group in offline mode
        # for currency, grouped_invoices in invoices_by_currency.items():
        #     data = submit_receipts_offline(grouped_invoices, tax_config)
        #     results.append(data)
        #
        # # Fiscalize invoices offline mode
        # r = close_day(tax_config, invoices)
        # return JsonResponse(r, safe=False)
        # check if fiscal day is open
        for invoice in invoices:
            data = submit_receipt(invoice, tax_config)
            results.append(data)
            
    print(results)
    return JsonResponse(results, safe=False)


def close_day_test(request):
    auto_close_fiscal_day()
    return HttpResponse("Executed")