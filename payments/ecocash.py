import httpx
import uuid
from django.conf import settings
from .models import Payment, PaymentPlan
from django.contrib.auth.models import User

def ecocash_pay(user: User, plan: PaymentPlan, ecocash_phone_number: str) -> (str, bool):

    source_reference = str(uuid.uuid4())

    url = settings.ECOCASH_API_URL

    payload = {
      "customerMsisdn": str(ecocash_phone_number),
      "amount": float(plan.amount),
      "reason": "Payment",
      "currency": str(plan.currency),
      "sourceReference": source_reference
    }
    headers = {
      'X-API-KEY': str(settings.ECOCASH_API_KEY),
      'Content-Type': 'application/json'
    }
    with httpx.Client() as client:
        response = client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
            return False, "Error processing payment!!!"

        # successful? create a pending payment object
        payment = Payment(
            user=user,
            amount=plan.amount,
            identity=ecocash_phone_number,
            internal_reference=source_reference,
            payment_plan=plan
        )
        payment.save()
        return True, "Processing payment..."