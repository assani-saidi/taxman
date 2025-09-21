from django.urls import path
from . import views

urlpatterns = [
    path('connect', views.set_connector, name='set-zimra-connector'),
    path('add-tax', views.add_connector, name='add-zimra-connector'),
    path('details', views.view_details, name='view-zimra-details'),
    path('complete-registration', views.complete_registration, name='complete-zimra-connector'),
    path('fiscalise', views.fiscalise_invoice, name='zimra-fiscalise'),
    path('fiscalise-all', views.fiscalise_invoices, name='zimra-fiscalise-all'),
    path('test', views.close_day_test, name='zimra-test'),
    # path('set-connector/', views.set_connector, name='set-quickbooks-connector'),
    # path('validate/', views.validate, name='validate'),
    # path('fiscalise', views.fiscalise, name='quickbooks-fiscalise'),
]