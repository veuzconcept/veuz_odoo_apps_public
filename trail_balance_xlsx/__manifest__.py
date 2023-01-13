# -*- coding: utf-8 -*-
{
    'name': 'Trail Balance XLSX',
    'description': '''Trail Balance XLSX ''',
    'author': "Veuz Concepts",
    "version": "0.1",
    'website': "www.veuzconcepts.com",
    'depends': ['base', 'web',],
    'data': [
        'views/trail_balance.xml'
    ],
    "assets": {
        "web.assets_backend": [
            # "trail_balance_xlsx/static/src/js/xlsx_controller.js",
        ],
    },
    "category": "Accounting",
    'installable': True,
    "images": ['static/description/banner.gif'],
}
