from django.urls import path
from . import views

urlpatterns = [
    # Auth routes
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('pricing/', views.pricing, name='pricing'),
    path('contactus/', views.contact, name='contactus'),
    path('login/', views.signin, name='login'),
    path('logout/', views.signout, name='logout'),
    path('profile/', views.profile, name='profile'),
    # Profile routes
    path('edit-profile/', views.edit_profile, name='edit-profile'),
    # Dashboard routes
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-tax-provider', views.add_user_tax_provider, name="add-tax-provider"), # post routes no /
    path('remove-tax-provider/', views.remove_user_tax_provider, name="remove-tax-provider"),
    path('tax-provider-config/<int:config_id>/', views.tax_provider_config_view, name='tax-provider-config'),
    path('disconnect-app/<int:app>/', views.disconnect_app, name='disconnect-app'),
    path('reconnect-app/<int:app>/', views.reconnect_app, name='reconnect-app'),
    path('complete-tax-provider/', views.complete_user_tax_provider, name="complete-tax-provider"),
    path('view-invoice/', views.view_invoice_details, name="view-invoice"),
    path('sync-invoices/', views.sync_invoices, name="sync-invoices"),
]