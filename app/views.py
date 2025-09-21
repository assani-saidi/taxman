from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required

from payments.models import PaymentPlan
from zimra.models import ZimraConfig
from .forms import UserRegisterForm, UserLoginForm, UserProfileForm, InvoiceForm
from payments.models import PaymentPlan
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
# from verify_email.email_handler import send_verification_email
from .models import TaxConnector, ConnectedTax, Connector, ConnectedApp, Invoice, ConnectedTax
from allauth.account.utils import complete_signup
from allauth.account.models import EmailAddress
from allauth.account import app_settings as allauth_settings
import requests
from payments.decorators import payment_required


def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'app/home.html', {})

def pricing(request):
    # if request.user.is_authenticated:
    #     return redirect('dashboard')
    payments = PaymentPlan.objects.all()
    return render(request, 'app/pricing.html', {"payments": payments})

def contact(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'app/contactus.html', {})

def register(request):
    if request.method == 'POST':
        user_form = UserRegisterForm(request.POST)
        if user_form.is_valid():
            user = user_form.save(commit=True)
            user.username = user_form.cleaned_data['email']
            # user.is_active = False
            user.organisation.name = user_form.cleaned_data['organisation_name'] or "My Company"
            user.save()
            complete_signup(request, user, allauth_settings.EMAIL_VERIFICATION, success_url='/dashboard')
            return redirect('account_email_verification_sent')
        else:
            print(user_form.errors)
    else:
        user_form = UserRegisterForm()
    return render(request, 'app/register.html', {'user_form': user_form})


def signin(request):
    if request.method == 'POST':
        login_form = UserLoginForm(request.POST)
        if login_form.is_valid():
            email = login_form.cleaned_data.get('email')
            password = login_form.cleaned_data.get('password')
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
                return redirect('dashboard')
            else:
                messages.error(request, "User with the given credentials cannot be found")
                print("User with the given credentials cannot be found")
                return redirect('login')
        else:
            messages.error(request, "Invalid Email or Password")
            print("Invalid Email or Password")
            return redirect('login')
    else:
        login_form = UserLoginForm()
    return render(request, 'app/login.html', {'login_form': login_form})


@login_required
def signout(request):
    logout(request)
    return redirect('login')


@login_required
def edit_profile(request):
    if request.method == 'POST':
        profile_form = UserProfileForm(request.POST, instance=request.user)
        if profile_form.is_valid():
            user = profile_form.save()
            user.organisation.name = profile_form.cleaned_data['organisation_name']
            user.save()
            return redirect('profile')
        else:
            print(profile_form.errors)
    else:
        profile_form = UserProfileForm(instance=request.user)
    return render(request, 'app/edit_profile.html', {'profile_form': profile_form})


@login_required
def profile(request):
    return render(request, 'app/profile.html', {'user': request.user})


@login_required
@payment_required
def dashboard(request):
    data = {}
    data['tax_providers'] = TaxConnector.objects.filter()
    data['connected_apps'] = ConnectedApp.objects.filter(organisation=request.user.organisation)
    connected_apps = [connected_app.connector.id for connected_app in data['connected_apps']]
    data['connectors'] = Connector.objects.annotate(user_connected_apps_count=Count('connected_apps', filter=Q(
        connected_apps__organisation=request.user.organisation.id)))
    transactions = Invoice.objects.all()
    data['transactions'] = []
    data['organisation'] = request.user.organisation
    for transaction in transactions:
        if transaction.connected_app in data['connected_apps']:
            data['transactions'].append(transaction)
    return render(request, 'app/dashboard.html', data)


@login_required
@payment_required
def add_user_tax_provider(request):
    if request.method == 'POST':
        tax_provider = TaxConnector.objects.get(pk=request.POST.get('tax_provider'))
        redirect_url = f"/{tax_provider.tax.name}/connect?connector={tax_provider.id}"
        return redirect(redirect_url)
    return redirect('dashboard')


@login_required
@payment_required
def remove_user_tax_provider(request):
    connected_tax_id = int(request.GET.get('connected_tax', None))
    ConnectedTax.objects.get(pk=connected_tax_id).delete()
    return redirect('dashboard')

@login_required
@payment_required
def tax_provider_config_view(request, config_id):
    connected_tax = ConnectedTax.objects.get(pk=config_id)
    redirect_url = f"/{connected_tax.connector.tax.name}/details?connector={connected_tax.connector.id}"
    return redirect(redirect_url)

@login_required
@payment_required
def disconnect_app(request, app):
    connected_app = get_object_or_404(ConnectedApp, pk=app)
    connected_app.delete()
    return redirect('dashboard')

@login_required
@payment_required
def reconnect_app(request, app):
    connected_app = get_object_or_404(ConnectedApp, pk=app)
    connector = connected_app.connector
    reconnect_url = f"/{connector.app.name}/set-connector?connector={connector.id}"
    return redirect(reconnect_url)

@login_required
@payment_required
def complete_user_tax_provider(request):
    connected_tax_id = int(request.GET.get('connected_tax', None))
    connected_tax = ConnectedTax.objects.get(pk=connected_tax_id)
    redirect_url = f"/{connected_tax.connector.tax.name}/complete-registration?connected_tax={connected_tax.id}"
    return redirect(redirect_url)

@login_required
@payment_required
def view_invoice_details(request):
    invoice_id = int(request.GET.get('invoice', None))
    zimra_tax_config = ZimraConfig.objects.get(organisation=request.user.organisation)
    invoice_errors = zimra_tax_config.zimra_invoice_validation_errors
    invoice = Invoice.objects.get(pk=invoice_id)
    invoice_form = InvoiceForm(instance=invoice)
    return render(request, 'app/invoice_details.html', {'invoice_form': invoice_form, 'invoice': invoice, 'invoice_errors': invoice_errors})

@login_required
@payment_required
def sync_invoices(request):
    invoice_id = request.GET.get('invoice')
    connected_tax = ConnectedTax.objects.filter(organisation=request.user.organisation).first()
    if connected_tax:
        fiscal_url = request.build_absolute_uri(f"/{connected_tax.connector.tax.name}/fiscalise?invoice_id={invoice_id}")
        result = requests.get(fiscal_url)
        # result = result.json()
        print(f"IN sync_invoices (view): {result}")
    return redirect('dashboard')
