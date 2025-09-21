# -*- coding: utf-8 -*-
{
    'name': "TaxMan Receipt Customisation",

    'summary': "This modifies odoo's default receipt to include TaxMan details",

    'description': """This modifies odoo's default receipt to include TaxMan details
    """,

    'author': "Assani Saidi",
    'website': "https://github.com/assani-saidi",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Productivity',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'point_of_sale'],

    'assets': {
        'point_of_sale._assets_pos': [
            'taxman_receipt/static/src/xml/receipt.xml',
            'taxman_receipt/static/src/js/receipt.js'
        ],
    }
}

