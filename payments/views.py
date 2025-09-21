from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .ecocash import ecocash_pay as pay
from django.contrib import messages
import json

from .models import Payment, PaymentPlan


@login_required
def process_payment(request, payment_plan_id):
    if not payment_plan_id:
        return redirect('pricing')

    payment_plan = PaymentPlan.objects.get(id=payment_plan_id)
    if request.method == "POST":
        messages.error(request, "Payments currently unavailable. Please contact support for direct payments.")
        return redirect('pricing')
        phone_number = request.POST.get('phone_number')

        # Validate phone number (9 digits)
        if not phone_number or len(phone_number) != 9 or not phone_number.isdigit():
            messages.error(request, 'Please enter a valid 9-digit phone number')
            return render(request, 'payments/payment.html', {'payment_plan_id': payment_plan_id})

        # Add 263 prefix for EcoCash
        full_phone = '263' + phone_number

        result, message = pay(user=request.user, ecocash_phone_number=full_phone, plan=payment_plan)
        if result:
            messages.success(request, 'Payment initiated successfully! Check your phone for EcoCash prompt.')
            return redirect(f"/payments/pay/{payment_plan_id}/")
        else:
            messages.error(request, 'Payment failed!!! Please try again later.')
            return redirect('pricing')
    return render(request, 'payments/payment.html', {'payment_plan': payment_plan})

def complete_payment(request):
    if request.method == 'POST':
        json_data = json.loads(request.body.decode('utf-8'))
        print("IN COMPLETE PAYMENT METHOD:")
        print(json.dumps(json_data, indent=2))
        # save payment information
        # get payment object by internal_reference
        payment = Payment.objects.filter(internal_reference=json_data.get('clientReference', '')).first()
        if json_data.get('transactionOperationStatus', 'UNKNOWN') == 'SUCCESS':
            payment.mark_as_completed(payment_reference=json_data.get('ecocashReference', ''))
            return HttpResponse("Payment received and logged", status=200)
        else:
            payment.mark_as_failed()
            return HttpResponse("Payment failed", status=402)

    return HttpResponse("Webhook endpoint - POST only", status=405)

