# app/signals.py
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from app.models import Invoice
from odoo_erp.odooerp import send_qr_code_to_odoo
from zimra.models import ZimraConfig
from zimra.zimra import submit_receipt

@receiver(post_save, sender=Invoice)
def on_invoice_save(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(lambda: auto_fiscalise_invoice(instance.id))
    # if not created and instance.status == "fiscalised":
    if not hasattr(instance, '_qr_code_processing'):
        instance._qr_code_processing = True
        transaction.on_commit(lambda: auto_notify_fiscalisation_status(instance.id))


def auto_notify_fiscalisation_status(invoice_id):
    invoice = Invoice.objects.get(id=invoice_id)
    if invoice.qr_code_url:
        try:
            result = send_qr_code_to_odoo(invoice)
            print(f"[SIGNAL] Send QR code result: {result}")
        except Exception as e:
            print(f"[SIGNAL] Send QR code error: {str(e)}")

def auto_fiscalise_invoice(invoice_id):
    instance = Invoice.objects.get(id=invoice_id)
    if instance.status != "fiscalised":
        try:
            tax_config = ZimraConfig.objects.get(organisation=instance.connected_app.organisation)
            result = submit_receipt(instance, tax_config)
            print(f"[SIGNAL] Fiscalisation result: {result}")
        except Exception as e:
            print(f"[SIGNAL] Fiscalisation error: {str(e)}")
