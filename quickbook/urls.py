from django.urls import path
from . import views

urlpatterns = [
    # Auth routes
    path('add-connector/', views.add_connector, name='add-quickbooks-connector'),
    path('set-connector/', views.set_connector, name='set-quickbooks-connector'),
    path('validate/', views.validate, name='validate'),
    path('fiscalise', views.fiscalise, name='quickbooks-fiscalise'),
]