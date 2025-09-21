from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from payments.decorators import payment_required

from zimra.models import ZimraConfig
from .forms import OdooConfigForm
from app.models import ConnectedApp, Connector
from django.contrib import messages
from django.http import HttpResponse 
from .models import OdooUserConfig
from .odooerp import create_invoice, create_receipt, run_preliminary_checks, run_post_check_actions, get_extra_database_information
import json

@login_required
@payment_required
def set_connector(request):
    connector_id = request.GET.get('connector', None)
    response = redirect('add-odoo-connector')
    response.set_cookie("connector", connector_id, path="/odoo")
    return response

@login_required
@payment_required
def add_connector(request):
    user = request.user
    if request.method == 'POST':
        form = OdooConfigForm(request.POST)
        if form.is_valid():
            connector_id = int(request.COOKIES.get('connector'))
            user_connector = Connector.objects.get(pk=connector_id)
            odoo_user_config = form.save(commit=False)
            odoo_user_config.organisation = user.organisation
            odoo_user_config.connector = user_connector.app
            checks_results = run_preliminary_checks(odoo_user_config)
            if checks_results[0]:
                # odoo_user_config.save()
                database_information = get_extra_database_information(odoo_user_config)
                db_uuid = database_information['uuid']
                if OdooUserConfig.objects.filter(database_uuid=db_uuid, organisation=user.organisation).exists():
                    messages.error(request, "This database is already linked to your account!")
                    print("Database UUID already exists in the system!")
                    return redirect('add-odoo-connector')
                odoo_user_config.database_uuid = db_uuid
                # odoo_user_config.save()
                action_results = run_post_check_actions(odoo_user_config, checks_results[1])
                if action_results[0]:
                    user_connected_app = ConnectedApp(
                        connector = user_connector,
                        organisation = user.organisation
                    )
                    user_connected_app.save()
                    odoo_user_config.connected_app = user_connected_app
                    odoo_user_config.save()
                return redirect('dashboard')
            else:
                messages.error(request, checks_results[2])
                print(checks_results[2])
                return redirect('add-odoo-connector')
        else:
            messages.error(request, "Invalid odoo credentials")
            print("Invalid odoo credentials")
            return redirect('add-connector')
    else:
        form = OdooConfigForm()
        data = {}
        data['form'] = form
        data['user'] = user
        return render(request, 'odoo_erp/configure.html', data)

def fiscalise(request):
    if request.method == 'POST':
        organisation = request.GET.get('organisation', None)
        database_uuid = request.GET.get('uuid', None)
        module = request.GET.get('module', None)
        odoo_invoice_data = json.loads(request.body)
        config = OdooUserConfig.objects.get(organisation__id=int(organisation), database_uuid=database_uuid)
        zimra_config = ZimraConfig.objects.get(organisation__id=int(organisation))
        result = None
        if module == "sales":
            result = create_invoice(config=config, data=odoo_invoice_data, zimra_config=zimra_config)
        elif module == "pos":
            result = create_receipt(config=config, data=odoo_invoice_data)
        else:
            pass
        return HttpResponse(result)

@csrf_exempt
def test(request):
    data = {'_action': 'Send Webhook Notification(#701)', '_id': 35, '_model': 'account.move', 'amount_total': 368.0, 'currency_id': 1, 'id': 35, 'invoice_date': '2024-07-17', 'invoice_line_ids': [93], 'move_type': 'out_invoice', 'name': 'INV/2024/00010', 'partner_id': 14, 'x_taxman_fiscalise': True, 'payment_state': 'in_payment'}
    config = OdooUserConfig.objects.get(organisation=request.user.organisation)
    checks_results = create_invoice(config, data)
    return HttpResponse(f"Initiated actions: {checks_results}")