{
    'name': 'Trail Balance XLSX',
    'description': '''Trail Balance XLSX ''',
    'author': "Veuz Concepts",
    "version": "1.0",
    'website': "www.veuzconcepts.com",
    'depends': ['base', 'web', 'report_xlsx', 'base_accounting_kit'],
    'data': [
        'views/trail_balance.xml'

    ],
"assets": {
        "web.assets_backend": [
            # "trail_balance_xlsx/static/src/js/xlsx_controller.js",
        ],
    },

    'license': 'LGPL-3',

    'installable': True,
}
