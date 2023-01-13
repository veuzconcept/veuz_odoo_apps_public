import logging
from odoo import api, fields, models, _
# -*- coding: utf-8 -*-
import re
import time
from odoo.exceptions import UserError
from datetime import datetime
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)
import io
import json
from odoo.tools.misc import get_lang
from odoo.exceptions import UserError
import time
import json
import datetime
import io
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import date_utils

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter
try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter
import xlwt
from xlsxwriter.workbook import Workbook
import base64
from io import BytesIO
import xlwt
from xlsxwriter.workbook import Workbook
import base64


class AccountBalanceReports(models.TransientModel):
    _inherit = 'account.balance.report'

    # _inherit = "report.report_xlsx.abstract"
    # _inherit = ['report.report_xlsx.abstract', 'account.balance.report']

    def print_xlsx(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(['date_from', 'date_to', 'journal_ids', 'target_move', 'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context, lang=get_lang(self.env).code)
        data = self.pre_print_report(data)
        data['active_model'] = 'account.balance.report'
        data['currency'] = self.env.company.currency_id.symbol
        model = 'account.balance.report'
        if not data.get('form') or not self.env[model].browse(data['form']['id']):
            raise UserError(
                _("Form content is missing, this report cannot be printed."))
        docs = self.env[model].browse(data['form']['id'])
        docids = data['form']['id']
        display_account = data['form'].get('display_account')
        accounts = docs if model == 'account.account' else self.env['account.account'].search([])
        report_data = []

        report_data = self.env['report.base_accounting_kit.report_trial_balance'].with_context(used_context)._get_accounts(accounts,
                                                                                                display_account)

        data = {
            'domain': 'domain',
            'report_data': report_data,
            'info': data,
            'report_type': 'xlsx',
        }
        return self.env.ref('trail_balance_xlsx.report_trail_balance_xlsx').report_action(self, data=data)


class PartnerXlsx(models.AbstractModel):
    _name = "report.trail_balance_xlsx.report_trail_xlsx"
    _inherit = "report.report_xlsx.abstract"
    _description = "Sale Analysis Excel Report"

    def generate_xlsx_report(self, workbook, data, partners):
        invoice_ids = []
        pos_order_ids = []
        sheet = workbook.add_worksheet('Sale Analysis Report')
        company_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'bold': True,
            'size': '22',
            'border': 1,
            'color': '#000000',
        })

        header_format = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'bold': True,
            'size': '12',
            'border': 1,
            'color': '#000000',
        })
        amt_header_format = workbook.add_format({
            'align': 'right',
            'valign': 'vcenter',
            'bold': True,
            'size': '12',
            'border': 1,
            'color': '#000000',
        })

        data_format = workbook.add_format({
            'align': 'left',
            'valign': 'top',
            'size': '12',
        })
        amt_data_format = workbook.add_format({
            'align': 'right',
            'valign': 'top',
            'size': '12',
        })

        sheet.set_column(0, 0, 5)
        sheet.set_column(1, 6, 25)
        row = 0
        column = 0
        display_account = 'With movements'
        target_move = 'With movements'

        sheet.write(row, column, data['info']['form']['company_id'][1] + ' : ' + 'Trial Balance', company_format)
        bold = workbook.add_format({'bold': True, 'font_size': 14})
        normal = workbook.add_format({'font_size': 8})

        date_from = "Date from : " + str(data['info']['form']['date_from'])
        date_to = "Date to : " + str(data['info']['form']['date_to'])

        segments_from = [header_format, date_from[:11], data_format, date_from[11:]]
        segments_to = [header_format, date_to[:9], data_format, date_to[9:]]

        # sheet.write_rich_string('A1', *segments_to)

        sheet.write(row + 3, column, 'Display Account:', header_format)
        if data['info']['form']['date_from']:
            sheet.write_rich_string('C4', *segments_from)
        sheet.write(row + 3, column + 4, 'Target Moves:', header_format)

        if data['info']['form']['display_account'] == 'movement':
            display_account = 'With movements'
        elif data['info']['form']['display_account'] == 'all':
            display_account = 'All accounts'
        elif data['info']['form']['display_account'] == 'not_zero':
            display_account = 'With balance not equal to zero'

        if data['info']['form']['target_move'] == 'posted':
            target_move = 'All Posted Entries'
        elif data['info']['form']['target_move'] == 'all':
            target_move = 'All Entries'

        sheet.write(row + 4, column, display_account, data_format)
        if data['info']['form']['date_to']:
            sheet.write_rich_string('C5', *segments_to)

        sheet.write(row + 4, column + 4, target_move, data_format)
        row = 7
        sheet.write(row, column, 'Code.', header_format)
        sheet.write(row, column + 1, 'Account', header_format)
        sheet.write(row, column + 2, 'Debit', amt_header_format)
        sheet.write(row, column + 3, 'Credit', amt_header_format)
        sheet.write(row, column + 4, 'Balance', amt_header_format)
        for rec in data['report_data']:
            row += 1
            sheet.write(row, column, rec['code'], data_format)
            sheet.write(row, column + 1, rec['name'], data_format)
            sheet.write(row, column + 2, str(rec['debit']) + ' ' + str(data['info']['currency']), amt_data_format)
            sheet.write(row, column + 3, str(rec['credit']) + ' ' + str(data['info']['currency']), amt_data_format)
            sheet.write(row, column + 4, str(rec['balance']) + ' ' + str(data['info']['currency']), amt_data_format)
