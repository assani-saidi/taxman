from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Payment


def payment_required_ajax(view_func):
    """
    Decorator for AJAX views that require payment.
    Returns JSON response instead of redirect.
    """
    from django.http import JsonResponse

    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        active_payments = Payment.objects.filter(
            user=request.user,
            status='success'
        )

        today = timezone.now().date()
        has_active_payment = active_payments.filter(
            valid_from__lte=today,
            valid_to__gte=today
        ).exists()

        if not has_active_payment:
            return JsonResponse({
                'error': 'Active subscription required',
                'redirect_url': '/payments/'
            }, status=403)

        return view_func(request, *args, **kwargs)

    return _wrapped_view

def payment_required(view_func):
    """
    Decorator that requires user to have an active payment.
    Must be used after @login_required.
    """

    @wraps(view_func)
    @login_required  # Ensure user is logged in first
    def _wrapped_view(request, *args, **kwargs):
        # Check if user has any active payments
        active_payments = Payment.objects.filter(
            user=request.user,
            status='success'
        )

        # Check if any payment is currently active
        today = timezone.now().date()
        has_active_payment = active_payments.filter(
            valid_from__lte=today,
            valid_to__gte=today
        ).exists()

        if not has_active_payment:
            messages.error(request, 'You need an active subscription to access this feature. Please purchase a plan.')
            return redirect('pricing')  # Redirect to pricing page

        return view_func(request, *args, **kwargs)

    return _wrapped_view