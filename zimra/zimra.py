import httpx
from django.conf import settings
from datetime import datetime, timedelta
from app.models import Invoice, InvoiceProduct
from .models import ZimraConfig
from .helpers import generate_csr_certificate_and_private_key, sign
from enum import Enum
from datetime import datetime, time
from django.core.files.base import ContentFile
import hashlib
from decimal import Decimal, ROUND_HALF_UP
import json
import base64


# ------------------- utility type

class ReceiptType(Enum):
    INVOICE = "FiscalInvoice"
    DEBIT_NOTE = "DebitNote"
    CREDIT_NOTE = "CreditNote"


class ReceiptLineType(Enum):
    SALE = "Sale"
    DISCOUNT = "Discount"


# ------------------- utility functions

get_invoice_type = lambda \
        invoice: ReceiptType.CREDIT_NOTE if invoice.type == "credit_note" else ReceiptType.DEBIT_NOTE if invoice.type == "debit_note" else ReceiptType.INVOICE

from decimal import Decimal, ROUND_HALF_UP


def fix_decimal(val):
    return float(Decimal(val).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def get_device_url_config(config, operation):
    device_payload = {"DeviceModelName": config.model_name, "DeviceModelVersion": config.model_version_no or 'v1'}
    url = f"{settings.ZIMRA_BASE_URL}/Device/{settings.ZIMRA_API_VERSION}/{config.device_id}/{operation}"
    certificates = (config.certificate.path, config.certificate_key.path)
    return url, certificates, device_payload


def prepare_hash_signature(invoices: list[Invoice], config: ZimraConfig, fiscal_day: int, fiscal_date: str):
    day_counters = prepare_fiscal_device_counters(invoices, config)
    raw_string = f"{config.device_id}{fiscal_day}{fiscal_date[:10]}"
    for day_counter in day_counters:
        raw_string += f"{day_counter['fiscalCounterType']}{day_counter['fiscalCounterCurrency']}{day_counter['fiscalCounterTaxPercent']}{day_counter['fiscalCounterValue']}"
    device_hash, device_signature = sign(raw_string, config)
    result = {"hash": device_hash, "signature": device_signature}
    return result


def prepare_device_sha(config: ZimraConfig, data: dict, update_hash=True):
    raw_string = ""
    # add deviceId
    raw_string += str(data['deviceID'])
    # add receiptType as uppercase
    raw_string += str(data['receiptType']).upper()
    # add receiptCurrency (ISO 4217 currency code
    raw_string += str(data['receiptCurrency'])
    # add receiptGlobalNo
    raw_string += str(data['receiptGlobalNo'])
    # add receiptDate ISO 8601 format <date>T<time>, YYYY-MM-DDTHH:mm:ss
    raw_string += str(data['receiptDate'])
    # add receiptTotal as cents
    receipt_total_cents = float(data['receiptTotal']) * 100
    raw_string += str(int(receipt_total_cents))
    # add receiptTaxes
    for tax in data['receiptTaxes']:
        # in order: taxPercent || taxAmount || salesAmountWithTax
        # add taxPercent it should have two trailing zeroes
        if tax['taxPercent']:
            formatted_tax_percent = f"{float(tax['taxPercent']):.2f}"
            raw_string += str(formatted_tax_percent)
        # add taxAmount in cents
        tax_amount_cents = float(tax['taxAmount']) * 100
        raw_string += str(int(tax_amount_cents))
        # add salesAmountWithTax in cents
        sales_amount_with_tax_cents = float(tax['salesAmountWithTax']) * 100
        raw_string += str(int(sales_amount_with_tax_cents))
    # add previousReceiptHash
    raw_string += str(data['previousReceiptHash']) if data['previousReceiptHash'] else ""
    print(f"\n\nRaw string for device hash: {raw_string}\n\n")
    device_hash, device_signature = sign(raw_string, config)
    if update_hash:
        config.receipt_previous_hash = device_hash
        config.save()
    result = {"hash": device_hash, "signature": device_signature}
    print(result)
    return result


def _prepare_device_sha(config: ZimraConfig, data: dict):
    raw_string = ''.join(
        str(value) for key, value in data.items() if key != "receiptTaxes" or key != "previousReceiptHash")
    for tax in data["receiptTaxes"]:
        raw_string += ''.join(str(value) for key, value in tax.items())
    raw_string += data['previousReceiptHash']
    device_hash, device_signature = sign(raw_string, config)
    config.receipt_previous_hash = device_hash
    config.save()
    result = {"hash": device_hash, "signature": device_signature}
    return result


def get_applicable_tax_id(taxes: list, percent: int | str) -> int:
    tax_id = 1
    for tax in taxes:
        try:
            if percent == tax["taxPercent"]:
                return tax["taxID"]
        except KeyError:
            continue
    return tax_id


def set_invoice_status(config: ZimraConfig, invoice: Invoice, zimra_response: dict, taxman_payload: dict, status_code: int, update_counters: bool = True):
    """
    Set the status of the invoice based on the Zimra response.
    and increase counters
    """

    if update_counters:
        config.receipt_global_counter += 1
        config.receipt_counter += 1
        config.save()

    zimra_response['httpStatusCode'] = status_code
    invoice.sent_data = taxman_payload
    if status_code == 200:
        invoice.tax_success_data = zimra_response
        if zimra_response.get("validationErrors"):
            invoice.failure_reason = "Validation errors occurred"
            invoice.status = "submitted"
        else:
            invoice.status = "fiscalised"
    else:
        invoice.tax_failure_data = zimra_response
        invoice.failure_reason = zimra_response.get("title", "Critical server error")
        invoice.status = "failed"
        invoice.retry = True  # Allow resubmission
        invoice.save()
    invoice.save()

def generate_qr_code(invoice: Invoice, config: ZimraConfig):
    """
    This method generates a Qr Code URL
    """
    qrUrl = config.zimra_api_device_information.get("qrUrl", "https://")
    qrUrl = qrUrl.rstrip('/')

    # Device ID represented in 10 digits number with leading zeros.
    deviceId = str(config.device_id).zfill(10)

    # Invoice date (receiptDate field value) represented in 8 digits (format: ddMMyyyy).
    receiptDate = invoice.created.strftime("%d%m%Y")

    # Receipt global number (receiptGlobalNo field value) issued by device represented in 10 digits with leading zeros
    receiptGlobalNo = str(invoice.sent_data.get("receipt", {}).get("receiptGlobalNo", 0)).zfill(10)

    # Receipt QR data field (first 16 hexadecimal characters of MD5 hash from ReceiptDeviceSignature value).
    device_signature_hash = invoice.sent_data.get("receipt", {}).get("receiptDeviceSignature", {}).get("signature", "")

    # Generate MD5 hash of the device signature hash and get first 16 hex characters
    if device_signature_hash:
        signature_bytes = base64.b64decode(device_signature_hash)
        signature_hex = signature_bytes.hex()
        device_signature_md5_hash = hashlib.md5(signature_hex.encode('utf-8')).hexdigest()
        receipt_qr_data = device_signature_md5_hash[:16].upper()
    else:
        receipt_qr_data = "0000000000000000"  # Fallback if hash is missing

    qr_url = f"{qrUrl}/{deviceId}{receiptDate}{receiptGlobalNo}{receipt_qr_data}"
    invoice.qr_code_url = qr_url
    invoice.save()


# ------------------- operational functions


def register_device(config):
    url = f"{settings.ZIMRA_BASE_URL}/Public/{settings.ZIMRA_API_VERSION}/{config.device_id}/RegisterDevice"
    device_payload = {"DeviceModelName": config.model_name or 'Server',
                      "DeviceModelVersion": config.model_version_no or 'v1'}
    certificate_private_key, csr_certificate = generate_csr_certificate_and_private_key(config.device_id,
                                                                                        config.serial_number, 'RSA')
    data = {
        "certificateRequest": csr_certificate.decode(),
        "activationKey": config.activation_key
    }
    with httpx.Client() as client:
        response = client.post(url, headers=device_payload, json=data)
        if response.status_code != 200:
            raise Exception(response.json())
        else:
            r = response.json()
            config.certificate.save(f"{config.organisation.name}_certificate_{config.id}",
                                    ContentFile(r['certificate']), save=True)
            config.certificate_key.save(f"{config.organisation.name}_certificate_key_{config.id}",
                                        ContentFile(certificate_private_key), save=True)
            config.save()

            # save device information
            get_device(config)

        print("\n\n")
        print("IN ZIMRA: register_device")
        print("\n")
        print(response.json())
        print("\n\n")
        return True


def get_device(config):
    if config.zimra_api_device_information:
        return config.zimra_api_device_information
    url, certificates, device_payload = get_device_url_config(config, 'GetConfig')
    with httpx.Client(cert=certificates) as client:
        response = client.get(url, headers=device_payload)
        if response.status_code != 200:
            raise Exception(response.json())

        config.zimra_api_device_information = response.json()
        config.save()
        print("\n\n")
        print("IN ZIMRA: get_device")
        print("\n")
        print(response.json())
        print("\n\n")
        return response.json()


def get_status(config):
    url, certificates, device_payload = get_device_url_config(config, 'GetStatus')
    # make sure to refresh the device info
    get_device(config)
    with httpx.Client(cert=certificates) as client:
        response = client.get(url, headers=device_payload)
        if response.status_code != 200:
            raise Exception(response.json())
        else:
            config.zimra_fiscal_day_information = response.json()
            config.save()
        print("\n\n")
        print("IN ZIMRA: get_status")
        print("\n")
        print(response.json())
        print("\n\n")
        r = response.json()
        return r


def check_day_status(config):
    status = get_status(config)
    if status['fiscalDayStatus'] == "FiscalDayClosed":
        return open_day(config)
    return True


def prepare_open_day(config):
    day_status = get_status(config)
    if day_status['fiscalDayStatus'] != "FiscalDayClosed":
        close_day(config, invoices=[])


def get_fiscal_day_no(config):
    day_status = get_status(config)
    return day_status['lastFiscalDayNo']


def open_day(config):
    day_open = datetime.combine(datetime.now().date(), time.min).strftime("%Y-%m-%dT%H:%M:%S")
    prepare_open_day(config)
    url, certificates, device_payload = get_device_url_config(config, 'OpenDay')
    data = {
        "fiscalDayOpened": day_open,
    }
    with httpx.Client(cert=certificates) as client:
        response = client.post(url, headers=device_payload, json=data)
        if response.status_code != 200:
            raise Exception(response.json())
        print("\n\n")
        print("IN ZIMRA: open_day")
        print("\n")
        print(response.json())
        print("\n\n")
        return True


def close_day(config, invoices: list[Invoice]):
    fiscal_day = get_fiscal_day_no(config)
    day_close = datetime.combine(datetime.now().date(), time.max).strftime("%Y-%m-%dT%H:%M:%S")
    url, certificates, device_payload = get_device_url_config(config, 'CloseDay')
    data = {
        "fiscalDayNo": fiscal_day,
        "fiscalDayCounters": prepare_fiscal_device_counters(invoices, config),
        "fiscalDayDeviceSignature": prepare_hash_signature(invoices, config, fiscal_day, day_close),
        "receiptCounter": config.receipt_counter
    }
    with httpx.Client(cert=certificates) as client:
        response = client.post(url, headers=device_payload, json=data)
        if response.status_code != 200:
            raise Exception(response.json())
        else:
            get_status(config) # get new device state
            config.receipt_previous_hash = None
            config.receipt_counter = 0
            config.save()
        print("\n\n")
        print("IN ZIMRA: close_day")
        print("\n")
        print(response.json())
        print("\n\n")
        return True


# ------------------- receipt submission functions
def prepare_submit_receipt(invoice: Invoice, config: ZimraConfig, update_hash=True) -> dict:
    # strangely ZIMRA needs 00 decimal places after the comma so we send it as a string formatted to 2 decimal places
    # to_decima_str = lambda x: f"{x:.2f}"
    to_decima_str = lambda x: float(x)

    # We prepare the receipt (see the param above)
    # notice pay_load is data will otherwise duplicate so we create it once and reuse it
    receipt_payload = {
        "deviceID": config.device_id,
        "receiptType": get_invoice_type(invoice).value,
        "receiptCurrency": invoice.currency.symbol,
        "receiptGlobalNo": config.receipt_global_counter + 1,
        "receiptDate": invoice.date.strftime("%Y-%m-%dT%H:%M:%S"),
        "receiptTotal": to_decima_str(float(invoice.total)),
        "receiptTaxes": [{
            "taxID": get_applicable_tax_id(config.zimra_api_device_information.get("applicableTaxes", []),
                                           line.invoice.tax.tax_percent),
            "taxPercent": line.invoice.tax.tax_percent,
            "taxAmount": to_decima_str(float(line.tax_amount)),
            "salesAmountWithTax": to_decima_str(float(line.total))
        } for line in invoice.invoiceproducts.all()],
        "previousReceiptHash": config.receipt_previous_hash,
    }
    receipt = {
        "receiptType": receipt_payload['receiptType'],
        "receiptCurrency": receipt_payload['receiptCurrency'],
        "receiptCounter": config.receipt_counter + 1,
        "receiptGlobalNo": receipt_payload['receiptGlobalNo'],
        "invoiceNo": str(invoice.id),
        # we give it the taxman invoice number instead of invoice.invoice_number, we know for certain this is unique
        # notice we skip buyerData because its not required by zimra
        "ReceiptNotes": invoice.notes or "",
        "receiptDate": receipt_payload['receiptDate'],
        "creditDebitNote": {
            "receiptID": invoice.reversed_invoice.origin_id,
            "deviceID": config.device_id,
            "receiptGlobalNo": invoice.reversed_invoice.sent_data.get("receiptGlobalNo", 0),
            "fiscalDayNo": invoice.reversed_invoice.sent_data.get("fiscalDayNo", 0),
        } if invoice.type in ["credit", "debit"] and invoice.reversed_invoice else None,
        "receiptLinesTaxInclusive": not all(product.tax == 'exclusive' for product in invoice.invoiceproducts.all()),
        "receiptLines": [{
            "receiptLineType": line.type.capitalize(),
            "receiptLineNo": index + 1,
            "receiptLineHSCode": line.hs_code,
            "receiptLineName": line.name,
            "receiptLinePrice": to_decima_str(float(line.price)),
            "receiptLineQuantity": to_decima_str(line.quantity),
            "receiptLineTotal": to_decima_str(float(line.total)) if line.tax != 'exclusive' else to_decima_str(
                float(line.amount)),
            "taxPercent": line.invoice.tax.tax_percent,
            "taxID": get_applicable_tax_id(config.zimra_api_device_information.get("applicableTaxes", []),
                                           line.invoice.tax.tax_percent)
        } for index, line in enumerate(invoice.invoiceproducts.all())],
        "receiptTaxes": receipt_payload['receiptTaxes'],
        "receiptPayments": [{
            "moneyTypeCode": line.invoice.payment_type.capitalize(),
            # Assuming cash payment, can be extended to support other payment types
            "paymentAmount": to_decima_str(float(line.total))
        } for line in invoice.invoiceproducts.all()],
        "receiptTotal": receipt_payload['receiptTotal'],
        "receiptPrintForm": "Receipt48",  # Assuming a default print form, can be extended to support other print forms
        "receiptDeviceSignature": prepare_device_sha(config=config, data=receipt_payload, update_hash=update_hash)
    }

    # add credit note fields if applicable
    if invoice.reversed_invoice:
        receipt['receiptNotes'] = invoice.notes or "Refund"
        receipt['creditDebitNote'] = {
            "receiptID": invoice.reversed_invoice.tax_success_data.get('receiptID', 0),
            "deviceID": config.device_id,
            "receiptGlobalNo": invoice.reversed_invoice.sent_data.get('receipt', 0).get("receiptGlobalNo", 0),
            "fiscalDayNo": get_fiscal_day_no(config),
        }


    # we wrap it in a data dict to match the zimra api requirements
    data = {
        "receipt": receipt
    }

    return data


def submit_receipt(invoice: Invoice, config: ZimraConfig) -> bool:
    # We get the request header data and url
    url, certificates, device_payload = get_device_url_config(config, 'submitReceipt')

    # We check the fiscal day status
    check_day_status(config)

    # we prepare the receipt
    data = prepare_submit_receipt(invoice, config)

    print(f"Formatted data to zimra: {data} \n")

    # we send the request to zimra api
    with httpx.Client(cert=certificates) as client:
        response = client.post(url, headers=device_payload, json=data)
        print("\n\n")
        print("IN ZIMRA: submit_receipt")
        print("\n")
        print(response.json())
        print("\n\n")
        set_invoice_status(config, invoice, response.json(), data, response.status_code)
        generate_qr_code(invoice, config)
        if response.status_code != 200:
            response.raise_for_status()
            raise Exception(response.json())
        return True


def resubmit_receipt(invoice: Invoice, config: ZimraConfig) -> bool:
    """
    Resubmit a receipt to ZIMRA.
    This function is similar to submit_receipt but is used for resubmitting receipts that have already been submitted.
    It checks the fiscal day status and prepares the receipt data before sending it to ZIMRA.
    """
    # We get the request header data and url
    url, certificates, device_payload = get_device_url_config(config, 'submitReceipt')

    # We check the fiscal day status
    check_day_status(config)

    # we prepare the receipt
    data = prepare_submit_receipt(invoice, config, update_hash=False)
    data['receipt']['receiptGlobalNo'] = invoice.sent_data['receipt'][
        'receiptGlobalNo']  # Use the original receipt global number
    data['receipt']['receiptCounter'] = invoice.sent_data['receipt'][
        'receiptCounter']  # Use the original receipt counter
    data['receipt']['receiptDeviceSignature'] = invoice.sent_data['receipt'][
        'receiptDeviceSignature']  # Use the original device signature

    print(f"Formatted data to zimra (resubmitted): {data} \n")

    # we send the request to zimra api
    with httpx.Client(cert=certificates) as client:
        response = client.post(url, headers=device_payload, json=data)
        print("\n\n")
        print("IN ZIMRA: re_submit_receipt")
        print("\n")
        print(response.json())
        print("\n\n")
        # Set the invoice status based on the response
        set_invoice_status(config, invoice, response.json(), data, response.status_code, update_counters=False)
        generate_qr_code(invoice, config)
        if response.status_code != 200:
            response.raise_for_status()
            raise Exception(response.json())
        return True


# ------------------ end receipt submission functions

# exactly what it sounds like, just a test function to see if we can submit a receipt works
def test_submit_receipt(config: ZimraConfig) -> dict:
    # We get the request header data and url
    url, certificates, device_payload = get_device_url_config(config, 'submitReceipt')
    data1 = {
        "receipt": {
            "receiptType": "FiscalInvoice",
            "receiptCurrency": "USD",
            "receiptCounter": 1,
            "receiptGlobalNo": 1,
            "invoiceNo": "343424",
            "ReceiptNotes": "",
            "receiptDate": "2025-09-08T10:00:00",
            "receiptLinesTaxInclusive": False,

            "receiptLines": [
                {
                    "receiptLineType": "Sale",
                    "receiptLineNo": 1,
                    "receiptLineHSCode": "200",
                    "receiptLineName": "Pedal Bin",
                    "receiptLinePrice": 100.00,
                    "receiptLineQuantity": 1.00,
                    "receiptLineTotal": 100.00,
                    "taxPercent": 15.0,
                    "taxID": 3
                }
            ],

            "receiptTaxes": [
                {
                    "taxID": 3,
                    "taxPercent": 15.0,
                    "taxAmount": 15.00,
                    "salesAmountWithTax": 115.00
                }
            ],

            "receiptPayments": [
                {
                    "moneyTypeCode": "Cash",
                    "paymentAmount": 115.00
                }
            ],

            "receiptTotal": "115.00",
            "receiptPrintForm": "Receipt48",

            "receiptDeviceSignature": {
                "hash": "e3b0c44298fc1c149afbf4c8996fb924",
                "signature": "YjhmZDM2ODg0NGE5ZDQ5MzZkY2U5N2QwY2Q5OGNkN2FlOGEzZGVmMjA2MWQ0NWM1"
            }
        }
    }

    data = {
        "receipt": {
            "receiptType": "FiscalInvoice",
            "receiptCurrency": "USD",
            "receiptCounter": 14,
            "receiptGlobalNo": 14,
            "invoiceNo": "88",
            "ReceiptNotes": "",
            "receiptDate": "2025-09-08T09:43:59",
            "receiptLinesTaxInclusive": False,
            "receiptLines": [
                {
                    "receiptLineType": "Sale",
                    "receiptLineNo": 1,
                    "receiptLineHSCode": "200",
                    "receiptLineName": "[E-COM10] Pedal Bin",
                    "receiptLinePrice": 100.00,
                    "receiptLineQuantity": 1.00,
                    "receiptLineTotal": 100.00,
                    "taxPercent": 15.0,
                    "taxID": 3
                }
            ],
            "receiptTaxes": [
                {
                    "taxID": 3,
                    "taxPercent": 15.0,
                    "taxAmount": 15.00,
                    "salesAmountWithTax": 115.00
                }
            ],
            "receiptPayments": [
                {
                    "moneyTypeCode": "Cash",
                    "paymentAmount": 115.00
                }
            ],
            "receiptTotal": "115.00",
            "receiptPrintForm": "Receipt48",
            "receiptDeviceSignature": {
                "hash": "SdJx1puCVNGYwTXv7ddE7fy/DqVGI3zsJ0i4o//xUOk=",
                "signature": "JRNWKeX8raHzR20Y1emEyhUF6fBKNAYM5CtEAVBuplX+gDni512xWW6QkOPUrHGlLhg+gY//wbL+RQTdEcfaNY9c5qw8KbJeyEbTaaDMpkZbRqPZgkKj7WfRMGa1ocdKc6IXdPKS81VMhohnaa1JKQsMcXDvGJY2HheEDcz337wlwYywv5gIlONrpf0XndUp1jYq9HhstO/EVchVwnzvu5oQ7XGw9KKI9x7o/+1nv5v4e4wVl6E34I8EW5HaR/KJ5NK4d26bycXeEqwrk204bTstw+dSGGRWyoCzEZBckpJc228kGEEPqsyjvseTBpZvlsgHLilOiVyInrwIwMuBXw=="
            }
        }
    }

    # we send the request to zimra api
    with httpx.Client(cert=certificates) as client:
        response = client.post(url, headers=device_payload, json=data1)
        print("\n\n")
        print("IN ZIMRA: submit_receipt(test)")
        print("\n")
        print(response.json())
        print("\n\n")
        return response.json()


def _submit_receipt(invoice: Invoice, config: ZimraConfig):
    url, certificates, device_payload = get_device_url_config(config, 'submitReceipt')
    check_day_status(config)
    data = prepare_receipts([invoice], config)
    data = {
        "receipt": data[0]
    }

    # with httpx.Client(cert=certificates) as client:
    #     response = client.post(url, headers=device_payload, json=data)
    #     response.raise_for_status()
    #     return response.json()

    with httpx.Client(cert=certificates) as client:
        response = client.post(url, headers=device_payload, json=data)
        print("\n\n")
        print("IN ZIMRA: _submit_receipt")
        print("\n")
        print(response.json())
        print("\n\n")
        set_invoice_status(invoice, response.json(), data, response.status_code)
        if response.status_code != 200:
            response.raise_for_status()
            raise Exception(response.json())
        return True


def prepare_receipt_line(invoice: Invoice, line: InvoiceProduct, config: ZimraConfig, index: int):
    tax_id = 0
    applicable_taxes = get_device(config)["applicableTaxes"]
    tax_id = get_applicable_tax_id(applicable_taxes, invoice.tax.tax_percent)
    return {
        "receiptLineType": ReceiptLineType.SALE.value,
        "receiptLineNo": index,
        "receiptLineName": line.name,
        "receiptLinePrice": float(line.price),
        "receiptLineQuantity": line.quantity,
        "receiptLineTotal": float(line.total),
        "taxID": tax_id
    }


def prepare_receipts(invoices: list[Invoice], config: ZimraConfig):
    invoices_data = []
    for invoice_index, invoice in enumerate(invoices):
        if not invoice: continue
        lines = []
        line_index = 0
        receipt_type = get_invoice_type(invoice).value
        for line_index, invoice_product in enumerate(invoice.invoiceproducts.all()):
            lines.append(prepare_receipt_line(invoice, invoice_product, config, line_index + 1))
        if not config.receipt_counter:
            config.receipt_counter = 1
        invoice_payload = {
            "deviceID": config.device_id,
            "receiptType": ReceiptType.INVOICE.value.upper(),
            "receiptCurrency": invoices[0].currency.symbol,
            "receiptGlobalNo": config.receipt_counter + 1,
            "receiptDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "receiptTotal": float(sum(invoice.total for invoice in invoices)),
            "receiptTaxes": prepare_tax_lines(invoice, config),
            "previousReceiptHash": config.receipt_previous_hash,
        }
        invoice_data = {
            "receiptType": ReceiptType.INVOICE.value,
            "receiptCurrency": invoice_payload['receiptCurrency'],
            "receiptCounter": invoice_index + 1,
            "receiptGlobalNo": invoice_payload['receiptGlobalNo'],
            "invoiceNo": invoice.invoice_number,
            "receiptDate": invoice_payload['receiptDate'],
            "receiptLinesTaxInclusive": False if invoice.tax.tax_type == "exclusive" else True,
            "receiptLines": lines,
            "receiptTaxes": invoice_payload['receiptTaxes'],
            "receiptPayments": prepare_receipt_payments(invoice, config),
            "receiptTotal": float(invoice_payload['receiptTotal']),
            "receiptDeviceSignature": prepare_device_sha(config=config, data=invoice_payload),
        }
        invoices_data.append(invoice_data)
        config.receipt_counter += 1
        config.save()
    return invoices_data


def prepare_tax_lines(invoice: Invoice, config: ZimraConfig):
    receipt_taxes = []
    applicable_taxes = get_device(config)['applicableTaxes']
    for line in invoice.invoiceproducts.all():
        t_percentage = line.invoice.tax.tax_percent if line.tax_amount > 0 else 0
        tax_id = tax_id = get_applicable_tax_id(applicable_taxes, t_percentage)
        receipt_taxes.append({
            "taxPercent": line.invoice.tax.tax_percent,
            "taxID": tax_id,
            "taxAmount": float(line.tax_amount),
            "salesAmountWithTax": float(line.total)
        })
    return receipt_taxes


def prepare_receipt_payments(invoice: Invoice, config: ZimraConfig):
    receipt_payments = []
    for line in invoice.invoiceproducts.all():
        receipt_payments.append({
            "moneyTypeCode": "Cash",
            "paymentAmount": float(line.total)
        })
    return receipt_payments


def prepare_fiscal_device_counters(invoices: list[Invoice], config: ZimraConfig):
    counters = []
    applicable_taxes = get_device(config)["applicableTaxes"]
    for invoice in invoices:
        tax_id = get_applicable_tax_id(applicable_taxes, invoice.tax.tax_percent)
        counters.append({
            "fiscalCounterType": "saleByTax",
            "fiscalCounterCurrency": invoice.currency.symbol,
            "fiscalCounterTaxPercent": invoice.tax.tax_percent,
            "fiscalCounterTaxID": tax_id,
            "fiscalCounterValue": float(invoice.total)
        })
    return counters


def submit_receipts_offline(invoices: list[Invoice], config: ZimraConfig):
    url, certificates, device_payload = get_device_url_config(config, 'SubmitFile')
    fiscal_day = get_fiscal_day_no(config) + 1
    fiscal_date = datetime.combine(datetime.now().date(), time.min).strftime("%Y-%m-%dT%H:%M:%S")
    day_close = datetime.combine(datetime.now().date(), time.max).strftime("%Y-%m-%dT%H:%M:%S")
    data = {
        "header": {
            "deviceID": int(config.device_id),
            "fiscalDayOpened": fiscal_date,
            "fiscalDayNo": fiscal_day,
            "fileSequence": config.file_counter + 1
        },
        "content": {
            "receipts": prepare_receipts(invoices, config),
        },
        "footer": {
            "fiscalDayCounters": prepare_fiscal_device_counters(invoices, config),
            "fiscalDayDeviceSignature": prepare_hash_signature(invoices, config, fiscal_day, fiscal_date),
            "receiptCounter": config.file_counter + 1,
            "fiscalDayClosed": day_close
        }
    }
    config.file_counter += 1
    config.save()

    # convert json data to base64 encoded string
    # data_json_str = json.dumps(data)
    # data_json_bytes = data_json_str.encode('utf-8')
    # data_base64_bytes = base64.b64encode(data_json_bytes)
    # data = data_base64_bytes.decode('utf-8')

    with httpx.Client(cert=certificates) as client:
        response = client.post(url, headers=device_payload, json=data)
        if response.status_code != 200:
            pass
        print("\n\n")
        print("IN ZIMRA: submit_receipts_offline")
        print("\n")
        print(response.json())
        print("\n\n")
        return response.json()


def check_submitted_receipts_offline(config: ZimraConfig):
    url, certificates, device_payload = get_device_url_config(config, 'SubmittedFileList')
    url = f"{url}?Offset=0&Limit=100"
    with httpx.Client(cert=certificates) as client:
        response = client.get(url, headers=device_payload)
        if response.status_code != 200:
            raise Exception(response.json())
        print("\n\n")
        print("IN ZIMRA: check_submitted_receipts_offline")
        print("\n")
        print(response.json())
        print("\n\n")
        return response.json()
