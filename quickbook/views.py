from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from .qb import get_auth_client, get_quickbooks, save_invoice, _save_invoice, API_SCOPES
from django.http import HttpResponse, JsonResponse
from .models import QuickbookUserConfig, QuickbookUserConfig 
from app.models import ConnectedApp, Connector
from django.conf import settings
import json

realm_id_cookie = settings.QUICKBOOKS_REALM_ID_COOKIE_NAME
refresh_token_cookie = settings.QUICKBOOKS_REFRESH_TOKEN_COOKIE_NAME

@login_required
def set_connector(request):
    connector_id = request.GET.get('connector', None)
    response = redirect('add-quickbooks-connector')
    response.set_cookie("connector", connector_id, path="/quickbooks/validate")
    return response

@login_required
def add_connector(request):
    auth_client = get_auth_client()
    url = auth_client.get_authorization_url(API_SCOPES)
    return redirect(url)

@login_required
def validate(request):
    connector_id = int(request.COOKIES.get('connector'))
    code = str(request.GET.get('code', None))
    realm_id = str(request.GET.get('realmId', None))
    # check if there is a connector with the same realm_id
    if QuickbookUserConfig.objects.filter(realm_id=realm_id):
        raise Exception("Another quickbooks configuration is linked to the same database!")
    auth_client = get_auth_client()
    auth_client.get_bearer_token(code, realm_id=realm_id)
    response = redirect('dashboard')
    response.set_cookie(realm_id_cookie, auth_client.realm_id, path="/")
    response.set_cookie(refresh_token_cookie, auth_client.refresh_token, path="/")
    user_connector = Connector.objects.get(pk=connector_id) 
    # create configuration file
    user_quickbooks_configuration = QuickbookUserConfig(
        connector = user_connector.app,
        organisation = request.user.organisation,
        realm_id = auth_client.realm_id,
        refresh_token = auth_client.refresh_token  
    )
    user_quickbooks_configuration.save()
    # create new connected app
    user_connected_app = ConnectedApp(
        connector = user_connector,
        organisation = request.user.organisation
    )
    user_connected_app.save()
    return response

@login_required
def configure(request):
    return render(request, 'quickbooks/configure.html')

@csrf_exempt
def fiscalise(request):
    if request.method == 'POST':
        data = json.loads(request.body) 
        for event in data['eventNotifications']:
            realm_id = event['realmId']
            quickbooks_user_configuration = QuickbookUserConfig.objects.get(realm_id=realm_id)
            auth_client = get_auth_client()
            auth_client.refresh(quickbooks_user_configuration.refresh_token)
            auth_client.realm_id = quickbooks_user_configuration.realm_id
            quickbooks_user_configuration.refresh_token = auth_client.refresh_token
            quickbooks_user_configuration.save()
            client = get_quickbooks(auth_client)
            save_invoice_ids = [] 
            for entity in event['dataChangeEvent']['entities']:
                if entity['operation'] == "Create":
                    save_invoice_ids.append(int(entity['id']))
            save_invoice(config=quickbooks_user_configuration ,client=client, invoice_ids=save_invoice_ids)
        return JsonResponse({'message': 'Data processed successfully'}, status=200)
    else:
        realm_id = "9341452726955454"
        quickbooks_user_configuration = QuickbookUserConfig.objects.get(realm_id=realm_id)
        auth_client = get_auth_client()
        auth_client.refresh(quickbooks_user_configuration.refresh_token)
        auth_client.realm_id = quickbooks_user_configuration.realm_id
        quickbooks_user_configuration.refresh_token = auth_client.refresh_token
        quickbooks_user_configuration.save()
        client = get_quickbooks(auth_client)
        result = _save_invoice(client)
        return JsonResponse(result, safe=False)