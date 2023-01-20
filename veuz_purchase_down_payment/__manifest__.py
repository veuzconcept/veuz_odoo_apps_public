{
    'name': 'Advance Payment For Purchase Order',
    'description': '''Advance Payment in Purchase Order''',
    'summary': 'Advance Payment in purchase',
    'author': 'Veuz Concepts',
    "version": "15.0",
    "category": "Accounting",
    'website': "www.veuzconcepts.com",
    'depends': ['base', 'web', 'account', 'stock', 'purchase'],
    "images": ['static/description/banner.gif'],
    'data': [
        'security/ir.model.access.csv',
        'views/settings.xml',
        'wizard/purchase_make_invoice_advance_views.xml',
        'views/purchase.xml',
    ],
    'installable': True,
}
