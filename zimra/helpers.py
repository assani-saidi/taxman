import openpyxl
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.conf import settings

from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.x509 import NameOID, CertificateSigningRequestBuilder
from cryptography.x509.oid import NameOID
import cryptography.x509 as x509
import base64

from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA

def sign(data: str, config):
    private_key_file = config.certificate_key.read()
    config.certificate_key.seek(0)
    priv_key = RSA.importKey(private_key_file)
    h = SHA256.new(data.encode('utf-8'))
    signature = PKCS1_v1_5.new(priv_key).sign(h)
    signature_base64 = base64.b64encode(signature).decode()
    hash_base64 = base64.b64encode(h.digest()).decode()
    return hash_base64, signature_base64


def generate_csr_certificate_and_private_key(device_id, serial_no, method='RSA'):
    # Create subject CN
    subject_cn = f"ZIMRA-{serial_no}-{'0' * (10 - len(str(device_id)))}{device_id}"
    
    # Create subject details
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, subject_cn)
    ])
    
    # Generate private key
    if method == 'RSA':
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
    elif method == 'ECC':
        private_key = ec.generate_private_key(
            ec.SECP256R1()
        )
    else:
        raise ValueError("Invalid method. Use 'RSA' or 'ECC'.")
    
    # Generate CSR
    csr = CertificateSigningRequestBuilder().subject_name(subject).sign(private_key, hashes.SHA256())
    
    # Serialize private key to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Serialize CSR to PEM format
    csr_pem = csr.public_bytes(serialization.Encoding.PEM)
    
    return private_key_pem, csr_pem

def create_excel_registration_form(data):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    
    # cosmetics
    # sheet['A1'] = 'Data to be filled in:'
    # sheet['A2'] = 'Taxpayer details'
    # sheet['E2'] = 'Taxpayer location details'
    # sheet['N2'] = 'Fiscal device information'
    
    # headers
    sheet['A1'] = 'Taxpayer TIN'
    sheet['B1'] = 'Taxpayer name'
    sheet['C1'] = 'VAT number'
    sheet['D1'] = 'Email'
    sheet['E1'] = 'Trade name'
    sheet['F1'] = 'Contact phone No.'
    sheet['G1'] = 'E-mail'
    sheet['H1'] = 'Province'
    sheet['I1'] = 'Street'
    sheet['J1'] = 'House No.'
    sheet['K1'] = 'City'
    sheet['L1'] = 'Region'
    sheet['M1'] = 'Station'
    sheet['N1'] = 'Serial No.'
    sheet['O1'] = 'Model name'
    sheet['P1'] = 'Supplier'
    
    # detail row
    sheet['A2'] = data['taxpayer_tin_number']
    sheet['B2'] = data['taxpayer_name']
    sheet['C2'] = data['taxpayer_vat_number']
    sheet['D2'] = data['taxpayer_email']
    sheet['E2'] = data['trade_name']
    sheet['F2'] = data['phone_number']
    sheet['G2'] = data['email']
    sheet['H2'] = data['province']
    sheet['I2'] = data['street']
    sheet['J2'] = data['house_number']
    sheet['K2'] = data['city']
    sheet['L2'] = data['region'].name
    sheet['M2'] = data['station'].name
    sheet['N2'] = data['serial_number']
    sheet['O2'] = data['model_name']
    sheet['P2'] = data['supplier']
    
    excel_file = BytesIO()
    workbook.save(excel_file)
    excel_file.seek(0)

    excel_content = ContentFile(excel_file.read(), name=f"{data['taxpayer_name']} - {data['taxpayer_tin_number']} - Registration Form.xlsx")
    return excel_content

def send_registration_form(excel_registration_form, zimra_email, client_email):
    subject = f'Registration Form'
    body = f'Please find the attached registration form.'
    from_email = settings.EMAIL_HOST_USER # Replace with your email address
    recipient_list = [zimra_email]
    cc_list = [client_email]
    
    email_message = EmailMessage(
        subject,
        body,
        from_email,
        recipient_list,
        cc=cc_list
    )
    
    # Attach the Excel file
    email_message.attach(excel_registration_form.name, excel_registration_form.read(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    
    # Send the email
    email_message.send(fail_silently=False)
    
    return True