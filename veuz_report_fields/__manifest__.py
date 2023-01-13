{
    'name': "Veuz Invoice Report Fields",
    'summary': """Custom Invoice Report Fields""",
    'description': """ Custom Invoice Report Fields for 2 reports """,
    'author': "Veuz Concepts",
    'website': "http://www.veuzconcepts.com",
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/report_paper_formate.xml',
        'views/report_template.xml',
        'views/tax_report_template.xml',
        'views/report_layout.xml',
        'views/invoice.xml',
        'views/company.xml',
        'views/partner.xml',
        'views/res_config_settings.xml',
    ],
    'application': True,
    'sequence': -1,
}
# -*- coding: utf-8 -*-
