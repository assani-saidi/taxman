from django.urls import path
from . import views

urlpatterns = [
    path("callback/", views.complete_payment, name='payment-callback'),
    path("pay/<int:payment_plan_id>/", views.process_payment, name='payment-pay'),
]