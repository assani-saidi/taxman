from datetime import datetime
import odoorpc
from zimra.zimra import resubmit_receipt
from .models import OdooUserConfig
from django.conf import settings
import xmlrpc.client
from app import models
import os
import base64
from io import BytesIO

odoo_webhook_url = settings.ODOO_WEBHOOK_URL

supported_odoo_versions = [
    15, 16, 17, 18
]


# Functions

def connect(config):
    clean_url = config.url.replace("http://", "").replace("https://", "").replace("/", "")
    odoo = odoorpc.ODOO(clean_url, port=config.port)
    odoo.login(config.database, config.email, config.password)
    return odoo


def create_fiscalise_field(config):
    odoo = connect(config)
    IrModelFields = odoo.env['ir.model.fields']
    IrModel = odoo.env['ir.model']
    account_move_model_id = IrModel.search([('model', '=', 'account.move')])
    pos_config_model_id = IrModel.search([('model', '=', 'pos.config')])

    invoice_count = IrModelFields.search_count(
        [('name', '=', 'x_taxman_fiscalise'), ('model_id', '=', account_move_model_id[0])])
    if invoice_count < 1:
        IrModelFields.create({
            "name": "x_taxman_fiscalise",
            "field_description": "TaxMan Fiscalise Invoice",
            "help": "Choose to send this invoice to be fiscalised on taxman",
            "model_id": account_move_model_id[0],
            "ttype": "boolean",
            "store": True,
        })

    # create point of sale config x_fiscalise field
    receipt_count = IrModelFields.search_count(
        [('name', '=', 'x_taxman_fiscalise'), ('model_id', '=', pos_config_model_id[0])])
    if receipt_count < 1:
        IrModelFields.create({
            "name": "x_taxman_fiscalise",
            "field_description": "TaxMan Fiscalise Receipts",
            "help": "Choose whether to fiscalise receipts from this point of sale on taxman",
            "model_id": pos_config_model_id[0],
            "ttype": "boolean",
            "store": True,
        })

    return True

def install_taxman_receipt_module(config):
    odoo = connect(config)
    Module = odoo.env['ir.module.module']
    BaseImportModule = odoo.env['base.import.module']

    # remove existing module
    taxman_module_count = Module.search_count([('name', '=', 'taxman_receipt')])
    if taxman_module_count > 0:
        taxman_module = Module.search([('name', '=', 'taxman_receipt')])
        for module in Module.browse(taxman_module):
            if module.state == 'installed':
                module.button_immediate_uninstall()

    # install module

    # get the zip folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    taxman_receipt_zip_path = os.path.join(current_dir, "taxman_receipt.zip")
    if not os.path.exists(taxman_receipt_zip_path):
        return False

    # create the record
    with open(taxman_receipt_zip_path, "rb") as f:
        zip_bytes = f.read()

    base64_taxman_receipt_zip = base64.encodebytes(zip_bytes).decode("utf-8")
    import_module_id = BaseImportModule.create({
        "module_file": base64_taxman_receipt_zip,
        "force": True,
    })
    import_module = BaseImportModule.browse(import_module_id)
    import_module.import_module()
    return True

def create_hs_code_field(config):
    odoo = connect(config)
    IrModelFields = odoo.env['ir.model.fields']
    IrModel = odoo.env['ir.model']
    product_template_model_id = IrModel.search([('model', '=', 'product.template')])
    hs_code_count = IrModelFields.search_count(
        [('name', '=', 'x_taxman_hs_code'), ('model_id', '=', product_template_model_id[0])])
    if hs_code_count < 1:
        IrModelFields.create({
            "name": "x_taxman_hs_code",
            "field_description": "TaxMan HS Code",
            "help": "Harmonized System Code for this product",
            "model_id": product_template_model_id[0],
            "ttype": "char",
            "store": True,
        })
    invoice_line_model_id = IrModel.search([('model', '=', 'account.move.line')])
    hs_code_count = IrModelFields.search_count(
        [('name', '=', 'x_taxman_hs_code'), ('model_id', '=', invoice_line_model_id[0])])
    if hs_code_count < 1:
        IrModelFields.create({
            "name": "x_taxman_hs_code",
            "field_description": "TaxMan HS Code",
            "model_id": invoice_line_model_id[0],
            "related": "product_id.x_taxman_hs_code",
            "ttype": "char",
            "store": True,
        })

    return True

def create_qr_code_url_field(config):
    odoo = connect(config)
    IrModelFields = odoo.env['ir.model.fields']
    IrModel = odoo.env['ir.model']
    account_move_model_id = IrModel.search([('model', '=', 'account.move')])
    pos_order_model_id = IrModel.search([('model', '=', 'pos.order')])

    invoice_count = IrModelFields.search_count(
        [('name', '=', 'x_taxman_qr_code_url'), ('model_id', '=', account_move_model_id[0])])
    if invoice_count < 1:
        IrModelFields.create({
            "name": "x_taxman_qr_code_url",
            "field_description": "TaxMan QR Code URL",
            "model_id": account_move_model_id[0],
            "ttype": "char",
            "store": True,
        })

    receipt_count = IrModelFields.search_count(
        [('name', '=', 'x_taxman_qr_code_url'), ('model_id', '=', pos_order_model_id[0])])
    if receipt_count < 1:
        IrModelFields.create({
            "name": "x_taxman_qr_code_url",
            "field_description": "TaxMan QR Code URL",
            "model_id": pos_order_model_id[0],
            "ttype": "char",
            "store": True,
        })

    return True

def create_qr_code_field(config):
    odoo = connect(config)
    IrModelFields = odoo.env['ir.model.fields']
    IrModel = odoo.env['ir.model']
    account_move_model_id = IrModel.search([('model', '=', 'account.move')])
    pos_order_model_id = IrModel.search([('model', '=', 'pos.order')])

    invoice_count = IrModelFields.search_count(
        [('name', '=', 'x_taxman_qr_code'), ('model_id', '=', account_move_model_id[0])])
    if invoice_count < 1:
        IrModelFields.create({
            "name": "x_taxman_qr_code",
            "field_description": "TaxMan QR Code image URL",
            "model_id": account_move_model_id[0],
            "ttype": "char",
            "store": True,
        })

    receipt_count = IrModelFields.search_count(
        [('name', '=', 'x_taxman_qr_code'), ('model_id', '=', pos_order_model_id[0])])
    if receipt_count < 1:
        IrModelFields.create({
            "name": "x_taxman_qr_code",
            "field_description": "TaxMan QR Code image URL",
            "model_id": pos_order_model_id[0],
            "ttype": "char",
            "store": True,
        })

    return True

def create_pos_automation_rule(config):
    odoo = connect(config)
    Automation = odoo.env['base.automation']
    IrModel = odoo.env['ir.model']
    IrActionServer = odoo.env['ir.actions.server']
    IrModelFields = odoo.env['ir.model.fields']
    account_move_model_id = IrModel.search([('model', '=', 'pos.order')])

    automation_count = Automation.search_count([('name', '=', 'TaxMan POS Webhook Automation')])
    if automation_count > 0:
        return True

    webhook_automation = {
        'name': 'TaxMan POS Webhook Automation',
        'model_id': account_move_model_id[0],
        'trigger': 'on_create_or_write',
        'trigger_field_ids': [
            (6, 0, IrModelFields.search([('model_id', '=', account_move_model_id[0]), ('name', '=', 'state')]))],
        'filter_domain': '[("state", "=", "draft")]'
    }
    # we get all the fields of the account.move model we need
    required_field_names = ['id', 'name', 'pos_reference', 'amount_total', 'amount_paid', 'move_type', 'partner_id',
                            'config_id', 'amount_tax', 'company_id', 'date_order', 'state', 'currency_id', 'lines',
                            'refunded_order_ids', 'note']
    field_ids = IrModelFields.search([('model_id', 'in', account_move_model_id), ('name', 'in', required_field_names)])

    server_action = {
        'name': 'TaxMan POS Webhook Automation',
        'model_id': account_move_model_id[0],
        'state': 'webhook',
        'type': 'webhook',
        'usage': 'base_automation',
        'webhook_url': f"{odoo_webhook_url}?uuid={config.database_uuid}&organisation={config.organisation.id}&module=pos",
        'webhook_field_ids': [(6, 0, field_ids)],
    }

    webhook_automation['action_server_ids'] = [(0, 0, server_action)]

    Automation.create(webhook_automation)

    return True

def create_invoice_automation_rule(config):
    odoo = connect(config)
    Automation = odoo.env['base.automation']
    IrModel = odoo.env['ir.model']
    IrActionServer = odoo.env['ir.actions.server']
    IrModelFields = odoo.env['ir.model.fields']
    account_move_model_id = IrModel.search([('model', '=', 'account.move')])

    automation_count = Automation.search_count([('name', '=', 'TaxMan Invoice Webhook Automation')])
    if automation_count > 0:
        return True

    webhook_automation = {
        'name': 'TaxMan Invoice Webhook Automation',
        'model_id': account_move_model_id[0],
        'trigger': 'on_create_or_write',
        'trigger_field_ids': [(6, 0, IrModelFields.search(
            [('model_id', '=', account_move_model_id[0]), ('name', '=', 'x_taxman_fiscalise')]))],
        'filter_domain': '["&", ("move_type", "in", ["out_invoice", "out_refund"]), ("state", "=", "posted")]'
    }
    # we get all the fields of the account.move model we need
    required_field_names = ['id', 'name', 'amount_total', 'move_type', 'partner_id', 'invoice_date', 'payment_state',
                            'amount_tax', 'amount_untaxed', 'amount_total', 'currency_id', 'company_id',
                            'invoice_line_ids', 'reversed_entry_id', 'ref', 'x_taxman_fiscalise']
    field_ids = IrModelFields.search([('model_id', 'in', account_move_model_id), ('name', 'in', required_field_names)])

    server_action = {
        'name': 'TaxMan Invoice Webhook Automation',
        'model_id': account_move_model_id[0],
        'state': 'webhook',
        'type': 'webhook',
        'usage': 'base_automation',
        'webhook_url': f"{odoo_webhook_url}?uuid={config.database_uuid}&organisation={config.organisation.id}&module=sales",
        'webhook_field_ids': [(6, 0, field_ids)],
    }

    webhook_automation['action_server_ids'] = [(0, 0, server_action)]

    Automation.create(webhook_automation)

    return True

def create_invoice_view(config):
    odoo = connect(config)
    IrView = odoo.env['ir.ui.view']

    view_count = IrView.search_count([('name', '=', 'taxman_invoice_view')])
    if view_count < 1:
        IrView.create({
        'name': 'taxman_invoice_view',
        'type': 'form',
        'model': 'account.move',
        'inherit_id': odoo.env.ref('account.view_move_form').id,
        'arch': """
        <data>
            <xpath expr="//div[field[@name='partner_id']]" position="after">
                <field name="x_taxman_fiscalise" widget="boolean_toggle" readonly="x_taxman_qr_code_url and x_taxman_qr_code"/>
                <field name="x_taxman_qr_code_url" readonly="True"/>
                <field name="x_taxman_qr_code" readonly="True"/>
            </xpath>
            <xpath expr="//page[@name='invoice_tab']/field/tree/field[@name='product_id']" position="after">
                <field name="x_taxman_hs_code"/>
            </xpath>
        </data>
        """
    })

    view_count = IrView.search_count([('name', '=', 'taxman_product_view')])
    if view_count < 1:
        IrView.create({
        'name': 'taxman_product_view',
        'type': 'form',
        'model': 'product.template',
        'inherit_id': odoo.env.ref('product.product_template_form_view').id,
        'arch': """
            <xpath expr="//field[@name='categ_id']" position="after">
                <field name="x_taxman_hs_code"/>
            </xpath>
        """
    })

    return True

def create_pos_view(config):
    odoo = connect(config)
    IrView = odoo.env['ir.ui.view']

    view_count = IrView.search_count([('name', '=', 'taxman_pos_config_view')])
    if view_count < 1:
        IrView.create({
            'name': 'taxman_pos_config_view',
            'type': 'form',
            'model': 'pos.config',
            'inherit_id': odoo.env.ref('point_of_sale.pos_config_view_form').id,
            'arch': """
                 <xpath expr="//setting[@id='other_devices']" position="after">
                     <setting id="taxman_config" string="Taxman Fiscalise" help="Fiscalise all receipts from this point of sale">
                        <field name="x_taxman_fiscalise"/>
                     </setting>
                 </xpath>
            """
        })

    view_count = IrView.search_count([('name', '=', 'taxman_pos_view')])
    if view_count < 1:
        IrView.create({
            'name': 'taxman_pos_view',
            'type': 'form',
            'model': 'pos.order',
            'inherit_id': odoo.env.ref('point_of_sale.view_pos_pos_form').id,
            'arch': """
                     <xpath expr="//field[@name='partner_id']" position="after">
                         <field name="x_taxman_qr_code_url" readonly="True"/>
                         <field name="x_taxman_qr_code" readonly="True"/>
                     </xpath>
                """
        })

    return True

def create_invoice_report(config):
    odoo = connect(config)
    IrView = odoo.env['ir.ui.view']

    view_count = IrView.search_count([('name', '=', 'taxman_invoice_report_document_view')])
    if view_count < 1:
        IrView.create({
            'name': 'taxman_invoice_report_document_view',
            'type': 'qweb',
            'model': 'account.move',
            'inherit_id': odoo.env.ref('account.report_invoice_document').id,
            'arch': """
                    <data>
                        <xpath expr="//t[@t-call='web.external_layout']" position="inside">
                            <t t-if="o.x_taxman_qr_code_url and o.x_taxman_qr_code">
                                <div t-if="o.x_taxman_qr_code_url" style="position: fixed; top: 5px !important; right: 5px; z-index: 99999; background: white; border: 2px solid #000; padding: 5px; text-align: center;">
                                    <img t-att-src="o.x_taxman_qr_code" alt="Tax Authority QR Code" style="width: 150px; height: 150px;"/>
                                    <div style="font-size: 8px; font-weight: bold; margin-top: 2px;">
                                        <b>Verification QR CODE</b>
                                    </div>
                                </div>
                            </t>
                        </xpath>
                    </data>
               """
        })

    return True

def test_required_apps_installed(config, app_list=False) -> bool:
    required_apps = ['point_of_sale', 'base_automation', 'account', 'sale_management'] if not app_list else app_list
    odoo = connect(config)
    Module = odoo.env['ir.module.module']
    for app_name in required_apps:
        count = Module.search_count([('name', '=', app_name), ('state', '!=', 'installed')])
        if count > 0:
            app_ids = Module.search([('name', '=', app_name)])
            for app in Module.browse(app_ids):
                app.button_immediate_install()
    odoo.close()
    return True

def test_automation_rules_app_installed(config):
    required_apps = ['base_automation']
    return test_required_apps_installed(config, required_apps)

def test_database_connection(config):
    odoo = connect(config)
    try:
        odoo.close()
        return True
    except Exception as e:
        print("IN ODOO TEST DATABASE CONNECTION: ", e)
        return False
    finally:
        odoo.close()

def test_database_version(config):
    version = False
    clean_url = config.url.replace("http://", "").replace("https://", "").replace("/", "")
    common = xmlrpc.client.ServerProxy(f'http://{clean_url}:{config.port}/xmlrpc/2/common')
    server_version = common.version()['server_version']
    for _version in supported_odoo_versions:
        if str(_version) in server_version:
            version = _version
            break
    return version

def create_scheduled_action(config):
    # if database is odoo 16 or less
    # create scheduled action in taxmna to
    # check invoice
    # however if possible do it in odoo
    pass

def create_invoice(config, data, zimra_config=None):

    if not data['x_taxman_fiscalise']:
        print(f"Invoice: {data['name']} is set to do not fiscalise")
        return False, f"Invoice  {data['name']} is marked as do not fiscalise"

    # globals
    odoo = connect(config)

    # fields needed by invoice
    connected_app = config.connected_app

    # additional data from odoo
    ResCurrency = odoo.env['res.currency']
    currency = ResCurrency.browse(data['currency_id'])

    try:
        currency = models.TaxCurrencies.objects.get(symbol=currency.symbol)
    except models.TaxCurrencies.DoesNotExist:
        currency = models.TaxCurrencies(
            name=currency.name,
            symbol=currency.symbol,
            country="ZW"
        )

        currency.save()

    ResPartner = odoo.env['res.partner']
    partner = ResPartner.browse(data['partner_id'])

    # credit note determination fields 'reversed_entry_id', 'ref'
    is_credit_note = True if data['reversed_entry_id'] or data['move_type'] == 'out_refund' else False

    # create app customer
    existing_customer = models.Customer.objects.filter(name=partner.name, tax_id=partner.vat).first()
    if existing_customer:
        customer = existing_customer
    else:
        customer = models.Customer(
            name=partner.name,
            tax_id=partner.vat,
            address=partner.street
        )
        customer.save()

    # create app tax
    ResCompany = odoo.env['res.company']
    company = ResCompany.browse(data['company_id'])
    AccountTax = odoo.env['account.tax']
    sales_tax = company.account_sale_tax_id[0]

    # create tax type
    t_name = sales_tax.name,
    t_tax_type = "inclusive" if sales_tax.price_include else "exclusive",
    t_computation_type = "fixed_amount" if sales_tax.amount_type == "group" or sales_tax.amount_type == "fixed" else "percentage",
    t_tax_percent = sales_tax.amount if sales_tax.amount_type == "percent" or sales_tax.amount_type == "division" else 0,
    t_fixed_amount = sales_tax.amount if sales_tax.amount_type == "fixed" or sales_tax.amount_type == "group" else 0
    existing_tax_type = models.TaxType.objects.filter(
        name=t_name[0],
        tax_type=t_tax_type,
        computation_type=t_computation_type,
        tax_percent=t_tax_percent[0],
        fixed_amount=t_fixed_amount
    ).first()

    if existing_tax_type:
        tax_type = existing_tax_type
    else:
        tax_type = models.TaxType(
            name=t_name[0],
            tax_type=t_tax_type,
            computation_type=t_computation_type,
            tax_percent=t_tax_percent[0],
            fixed_amount=t_fixed_amount
        )
        tax_type.save()

    # create app invoice to save in app
    # notice we do this in one transaction so that our signal triggers correctly
    from django.db import transaction
    with transaction.atomic():
        # check if invoice already exists
        ExistingInvoice = models.Invoice.objects.filter(origin_id=int(data['id']), connected_app=connected_app,
                                                        invoice_number=data['name'], type__in=["invoice", "credit_note"])
        if len(ExistingInvoice) > 0:
            ExistingInvoice = ExistingInvoice[0]
            if ExistingInvoice.status == "fiscalised":
                return False, f"Invoice {ExistingInvoice.invoice_number} already fiscalised"
            else:
                ExistingInvoice.type = 'invoice' if not is_credit_note else 'credit_note'
                ExistingInvoice.customer = customer
                ExistingInvoice.date = datetime.strptime(data['invoice_date'], "%Y-%m-%d").replace(hour=13, minute=0, second=0)
                ExistingInvoice.tax = tax_type
                ExistingInvoice.amount = float(data['amount_untaxed']) if not is_credit_note else float(data['amount_untaxed']) * -1
                ExistingInvoice.tax_amount = float(data['amount_tax']) if not is_credit_note else float(data['amount_tax']) * -1
                ExistingInvoice.total = float(data['amount_total']) if not is_credit_note else float(data['amount_total']) * -1
                ExistingInvoice.currency = currency
                if is_credit_note:
                    reversed_invoice = models.Invoice.objects.filter(connected_app=connected_app, origin_id=data['reversed_entry_id']).first()
                    ExistingInvoice.reversed_invoice = reversed_invoice
                    ExistingInvoice.notes = data['ref'] or "Reason unspecified"
                ExistingInvoice.save()
                print(f"Updating existing invoice {ExistingInvoice.invoice_number} with new data")

                # delete existing products
                ExistingInvoice.invoiceproducts.all().delete()
                # create product lines
                for line in odoo.execute('account.move.line', 'read', data['invoice_line_ids'],
                                         ['name', 'quantity', 'price_unit', 'price_subtotal', 'price_total', 'x_taxman_hs_code',
                                          'tax_ids']):
                    tax_type = "exclusive"
                    for tax_id in line['tax_ids']:
                        tax = AccountTax.browse(tax_id)
                        if tax.price_include:
                            tax_type = "inclusive"
                            break
                    product = models.InvoiceProduct(
                        invoice=ExistingInvoice,
                        name=line['name'],
                        hs_code=line['x_taxman_hs_code'],
                        quantity=line['quantity'],
                        price=line['price_unit'] if not is_credit_note else line['price_unit'] * -1,
                        amount=line['price_subtotal'] if not is_credit_note else line['price_subtotal'] * -1,
                        tax_amount=(line['price_total'] - line['price_subtotal']) if not is_credit_note else (line['price_total'] - line['price_subtotal']) * -1,
                        tax=tax_type,
                        total=line['price_total'] if not is_credit_note else line['price_total'] * -1
                    )
                    product.save()
                # trigger signal to fiscalise invoice
                resubmit_receipt(ExistingInvoice, zimra_config)
        else:
            app_invoice = models.Invoice(
                type ='invoice' if not is_credit_note else 'credit_note',
                connected_app=connected_app,
                origin_id=int(data['id']),
                customer=customer,
                date=datetime.strptime(data['invoice_date'], "%Y-%m-%d").replace(hour=13, minute=0, second=0),
                tax=tax_type,
                invoice_number=data['name'],
                status="pending",
                amount=float(data['amount_untaxed']) if not is_credit_note else float(data['amount_untaxed']) * -1,
                tax_amount=float(data['amount_tax']) if not is_credit_note else float(data['amount_tax']) * -1,
                total=float(data['amount_total']) if not is_credit_note else float(data['amount_total']) * -1,
                currency=currency,
                reversed_invoice=models.Invoice.objects.filter(connected_app=connected_app, origin_id=data['reversed_entry_id']).first() if is_credit_note else None,
                notes=data['ref'] or "Reason unspecified" if is_credit_note else None
            )
            app_invoice.save()

            # create product lines
            for line in odoo.execute('account.move.line', 'read', data['invoice_line_ids'],
                                     ['name', 'quantity', 'price_unit', 'price_subtotal', 'price_total', 'tax_ids', 'x_taxman_hs_code']):
                tax_type = "exclusive"
                for tax_id in line['tax_ids']:
                    tax = AccountTax.browse(tax_id)
                    if tax.price_include:
                        tax_type = "inclusive"
                        break
                product = models.InvoiceProduct(
                    invoice=app_invoice,
                    name=line['name'],
                    hs_code=line['x_taxman_hs_code'],
                    quantity=line['quantity'],
                    price=line['price_unit'] if not is_credit_note else line['price_unit'] * -1,
                    amount=line['price_subtotal'] if not is_credit_note else line['price_subtotal'] * -1,
                    tax_amount=(line['price_total'] - line['price_subtotal']) if not is_credit_note else (line['price_total'] - line['price_subtotal']) * -1,
                    tax=tax_type,
                    total=line['price_total'] if not is_credit_note else line['price_total'] * -1
                )
                product.save()

    return True

def create_receipt(config, data, zimra_config=None):

    odoo = connect(config)
    PosConfig = odoo.env['pos.config']

    point_of_sale = PosConfig.browse([int(data['config_id'])])
    if not point_of_sale.x_taxman_fiscalise:
        print(f"Receipt: {data['name']} is set to do not fiscalise")
        return False, f"Receipt  {data['name']} is marked as do not fiscalise"

    # fields needed by invoice
    connected_app = config.connected_app

    # additional data from odoo
    ResCurrency = odoo.env['res.currency']
    currency = ResCurrency.browse(data['currency_id'])

    try:
        currency = models.TaxCurrencies.objects.get(symbol=currency.symbol)
    except models.TaxCurrencies.DoesNotExist:
        currency = models.TaxCurrencies(
            name=currency.name,
            symbol=currency.symbol,
            country="ZW"
        )

        currency.save()

    ResPartner = odoo.env['res.partner']
    partner = ResPartner.browse(data['partner_id'])

    # credit note determination fields 'pos_reference': 'Order 00010-001-0003', 'refunded_order_ids': [8], 'note': False
    is_credit_note = True if data['refunded_order_ids'] else False

    # create app customer
    existing_customer = models.Customer.objects.filter(name=partner.name, tax_id=partner.vat).first()
    if existing_customer:
        customer = existing_customer
    else:
        customer = models.Customer(
            name=partner.name,
            tax_id=partner.vat,
            address=partner.street
        )
        customer.save()

    # create app tax
    ResCompany = odoo.env['res.company']
    company = ResCompany.browse(data['company_id'])
    AccountTax = odoo.env['account.tax']
    sales_tax = company.account_sale_tax_id[0]

    # create tax type
    t_name = sales_tax.name,
    t_tax_type = "inclusive" if sales_tax.price_include else "exclusive",
    t_computation_type = "fixed_amount" if sales_tax.amount_type == "group" or sales_tax.amount_type == "fixed" else "percentage",
    t_tax_percent = sales_tax.amount if sales_tax.amount_type == "percent" or sales_tax.amount_type == "division" else 0,
    t_fixed_amount = sales_tax.amount if sales_tax.amount_type == "fixed" or sales_tax.amount_type == "group" else 0
    existing_tax_type = models.TaxType.objects.filter(
        name=t_name[0],
        tax_type=t_tax_type,
        computation_type=t_computation_type,
        tax_percent=t_tax_percent[0],
        fixed_amount=t_fixed_amount
    ).first()

    if existing_tax_type:
        tax_type = existing_tax_type
    else:
        tax_type = models.TaxType(
            name=t_name[0],
            tax_type=t_tax_type,
            computation_type=t_computation_type,
            tax_percent=t_tax_percent[0],
            fixed_amount=t_fixed_amount
        )
        tax_type.save()

    # create app receipt to save in app
    # notice we do this in one transaction so that our signal triggers correctly
    from django.db import transaction
    with transaction.atomic():
        # check if receipt already exists
        ExistingReceipt = models.Invoice.objects.filter(origin_id=int(data['id']), connected_app=connected_app,
                                                        invoice_number=data['name'], type__in=["receipt", "credit_note"])
        if len(ExistingReceipt) > 0:
            ExistingReceipt = ExistingReceipt[0]
            if ExistingReceipt.status == "fiscalised":
                return False, f"Receipt {ExistingReceipt.invoice_number} already fiscalised"
            else:
                ExistingReceipt.type = 'receipt' if not is_credit_note else 'credit_note'
                ExistingReceipt.customer = customer
                ExistingReceipt.date = datetime.strptime(data['date_order'], "%Y-%m-%d %H:%M:%S")
                ExistingReceipt.tax = tax_type
                ExistingReceipt.amount = -abs(float(data['amount_untaxed'])) if is_credit_note else data['amount_untaxed']
                ExistingReceipt.tax_amount = -abs(float(data['amount_tax'])) if is_credit_note else data['amount_tax']
                ExistingReceipt.total = -abs(float(data['amount_total'])) if is_credit_note else data["amount_total"]
                ExistingReceipt.currency = currency
                if is_credit_note:
                    reversed_invoice = models.Invoice.objects.filter(connected_app=connected_app, origin_id__in=data['refunded_order_ids'] or []).first()
                    ExistingReceipt.reversed_invoice = reversed_invoice
                    ExistingReceipt.notes = data['note'] or "Refund point of sale receipt"
                ExistingReceipt.save()
                print(f"Updating existing invoice {ExistingReceipt.invoice_number} with new data")

                # delete existing products
                ExistingReceipt.invoiceproducts.all().delete()
                # create product lines
                for line in odoo.execute('pos.order.line', 'read', data['lines'],
                                         ['full_product_name', 'qty', 'price_unit', 'price_subtotal', 'price_subtotal_incl',
                                          'tax_ids', 'product_id']):
                    tax_type = "exclusive"
                    for tax_id in line['tax_ids']:
                        tax = AccountTax.browse(tax_id)
                        if tax.price_include:
                            tax_type = "inclusive"
                            break

                    product_template = odoo.env['product.product'].browse(line['product_id']).product_tmpl_id
                    product = models.InvoiceProduct(
                        invoice=ExistingReceipt,
                        name=line['full_product_name'],
                        hs_code=product_template.x_taxman_hs_code,
                        quantity=abs(line['qty']) if is_credit_note else line["qty"],
                        price=-abs(line['price_unit']) if is_credit_note else line["price_unit"],
                        amount=-abs(line['price_subtotal']) if is_credit_note else line["price_subtotal"],
                        tax_amount=-abs(line['price_total'] - line['price_subtotal_incl']) if is_credit_note else (line['price_total'] - line['price_subtotal_incl']),
                        tax=tax_type,
                        total=-abs(line['price_subtotal_incl']) if is_credit_note else line["price_subtotal_incl"]
                    )
                    product.save()
                    # trigger signal to fiscalise invoice
                    resubmit_receipt(ExistingReceipt, zimra_config)
        else:
            app_receipt = models.Invoice(
                type='receipt' if not is_credit_note else 'credit_note',
                connected_app=connected_app,
                origin_id=int(data['id']),
                customer=customer,
                date=datetime.strptime(data['date_order'], "%Y-%m-%d %H:%M:%S"),
                tax=tax_type,
                invoice_number=data['pos_reference'],
                status="pending",
                amount=-abs(float(data['amount_total']) - float(data['amount_tax'])) if is_credit_note else (float(data['amount_total']) - float(data['amount_tax'])),
                tax_amount=-abs(float(data['amount_tax'])) if is_credit_note else float(data['amount_tax']),
                total=-abs(float(data['amount_total'])) if is_credit_note else float(data['amount_total']),
                currency=currency,
                reversed_invoice=models.Invoice.objects.filter(connected_app=connected_app, origin_id__in=data['refunded_order_ids'] or []).first() if is_credit_note else None,
                notes=data['note'] or "Refund point of sale receipt" if is_credit_note else None
            )
            app_receipt.save()

            # create product lines
            for line in odoo.execute('pos.order.line', 'read', data['lines'],
                                     ['full_product_name', 'qty', 'price_unit', 'price_subtotal', 'price_subtotal_incl',
                                      'tax_ids', 'product_id']):
                tax_type = "exclusive"
                for tax_id in line['tax_ids']:
                    tax = AccountTax.browse(tax_id)
                    if tax.price_include:
                        tax_type = "inclusive"
                        break
                product_template = odoo.env['product.product'].browse(line['product_id'][0]).product_tmpl_id
                product = models.InvoiceProduct(
                    invoice=app_receipt,
                    name=line['full_product_name'],
                    hs_code=product_template.x_taxman_hs_code,
                    quantity=abs(line['qty']) if is_credit_note else line['qty'],
                    price=-abs(line['price_unit']) if is_credit_note else line['price_unit'],
                    amount=-abs(line['price_subtotal']) if is_credit_note else line['price_subtotal'],
                    tax_amount=-abs(line['price_subtotal_incl'] - line['price_subtotal']) if is_credit_note else (line['price_subtotal_incl'] - line['price_subtotal']),
                    tax=tax_type,
                    total=-abs(line['price_subtotal_incl']) if is_credit_note else line['price_subtotal_incl']
                )
                product.save()

    return True

def run_preliminary_checks(config):
    database_connection_test_result = test_database_connection(config)
    if not database_connection_test_result:
        return False, 'database_version', "Odoo refused to connect with the credentials"
    database_version = test_database_version(config)
    if not database_version:
        return False, database_version, "Your odoo database version is not yet supported"
    return True, database_version, "All preliminary checks succeeded"

def get_extra_database_information(config):
    odoo = connect(config)
    SystemParameter = odoo.env['ir.config_parameter']
    system_parameter_id = SystemParameter.search([('key', '=', 'database.uuid')])
    system_parameter = SystemParameter.browse(system_parameter_id)
    return {
        "uuid": system_parameter.value
    }

def run_post_check_actions(config, database_version):
    required_apps_installed = test_required_apps_installed(config)
    if not required_apps_installed:
        return False, "We encountered an error installing Automated Actions / Automations, Point of Sale and Sales in your odoo database. Please proceed to manually install this module!"
    create_fiscalise_field_action_result = create_fiscalise_field(config)
    if not create_fiscalise_field_action_result:
        return False, "Ahh, we cant create a field `x_taxman_fiscalise` on `account.move` model. Please use studio and manually create it yourself."
    create_hs_code_field_action_result = create_hs_code_field(config)
    if not create_hs_code_field_action_result:
        return False, "Ahh, we cant create a field `x_taxman_hs_code` on `account.move.line` model. Please use studio and manually create it yourself."
    create_qr_code_url_field_result = create_qr_code_url_field(config)
    if not create_qr_code_url_field_result:
        return False, "Ahh, we cant create a field `x_taxman_qr_code_url` on `account.move` model. Please use studio and manually create it yourself."
    create_qr_code_field_result = create_qr_code_field(config)
    if not create_qr_code_field_result:
        return False, "Ahh, we cant create a field `x_taxman_qr_code` on `account.move` model. Please use studio and manually create it yourself."
    if database_version >= 17:
        intialise_result = initialise_database(config)
        return intialise_result
    return True, "Database successfully linked with taxman"

def send_qr_code_to_odoo(invoice: models.Invoice):
    try:
        config = OdooUserConfig.objects.get(connected_app=invoice.connected_app)
    except OdooUserConfig.DoesNotExist:
        return False, "We could not find the odoo configuration for this connected app"

    if not invoice.qr_code_url:
        return False, "Invoice does not have a qr code to send to odoo"

    odoo = connect(config)
    AccountMove = odoo.env['account.move']
    PosOrder = odoo.env['pos.order']
    if invoice.type != 'credit_note':
        Model = AccountMove if invoice.type in ['invoice', 'debit_note'] else PosOrder
    else:
        Model = AccountMove if invoice.reversed_invoice.type in ['invoice', 'debit_note'] else PosOrder
    try:
        # record = Model.browse(104)
        record = Model.search([('id', '=', invoice.origin_id)])
        if not record:
            return False, f"We could not find the invoice/receipt/credit note with id {invoice.origin_id} in odoo"
        Model.write(record, {
            'x_taxman_qr_code_url': str(invoice.qr_code_url),
            'x_taxman_qr_code': str(invoice.qr_code)
        })
        odoo.close()
        return True, "Successfully sent qr code to odoo"
    except Exception as e:
        print("Error sending qr code to odoo: ", e)
        return False, str(e)
    finally:
        odoo.close()

# Callables for odoo 17 and up

def initialise_database(config):
    install_taxman_receipt_module_result = install_taxman_receipt_module(config)
    if not install_taxman_receipt_module_result:
        return False, "We encountered an error installing Taxman Receipt module in your odoo database. Please proceed to manually install this module!"
    invoice_automation_created = create_invoice_automation_rule(config)
    if not invoice_automation_created:
        return False, "Invoice automation could not be created: Check if you have Invoicing | Accounting installed"
    pos_automation_created = create_pos_automation_rule(config)
    if not pos_automation_created:
        return False, "POS automation could not be created: Check if you have POS installed"
    invoice_view_created = create_invoice_view(config)
    if not invoice_view_created:
        return False, "We could not create a view to show the fiscalise field on the invoice form view. Please use studio to add the field `x_taxman_fiscalise` to the invoice form view"
    pos_view_created = create_pos_view(config)
    if not pos_view_created:
        return False, "We could not create a view to show the fiscalise field on the point of sale config form view. Please use studio to add the field `x_taxman_fiscalise` to the point of sale config form view"
    invoice_report_created = create_invoice_report(config)
    if not invoice_report_created:
        return False, "We could not create a view to show the qr code on the invoice report. Please use studio to add the fields `x_taxman_qr_code_url` and `x_taxman_qr_code` to the invoice report"
    return True, "Database successfully linked with taxman"

    # STEPS WE NEED
    # 1. Check connection to odoo
    # 2. Check if odoo version
    # 3. Check if odoo has base_automation app installed
    # 4. Create fiscalise field on invoice model
    # 5. if odoo version 17:
    # a. Create webhook automation rule for invoice
    # b. Create webhook automation rule for pos
    # 6. if odoo version 16 or less:
    # a. Create scheduled action in taxman to check invoice
