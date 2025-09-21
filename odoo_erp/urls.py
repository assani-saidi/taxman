from django.urls import path
from . import views

urlpatterns = [ 
    # Auth routes
    path('add-connector/', views.add_connector, name='add-odoo-connector'),
    path('set-connector/', views.set_connector, name='set-odoo-connector'),
    path('fiscalise', views.fiscalise, name='odoo-fiscalise'),
    path('test', views.test, name='test'),
]