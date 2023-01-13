# -*- coding: utf-8 -*-

from odoo import  fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    invoice_report_layout = fields.Boolean(related='company_id.invoice_report_layout')

    def action_view_report_layout(self):
        attachment_action = self.env.ref('veuz_report_fields.action_document_layout_configurator')
        action = attachment_action.read()[0]
        report_status = self.company_id.report_status()
        invoice_report_layout = False
        if report_status == 'both':
            invoice_report_layout = self.company_id.invoice_report_layout_id
        elif report_status == 'invoice report':
            invoice_report_layout = False
        elif report_status == 'tax invoice':
            invoice_report_layout = 'tax invoice'
        action['context'] = {
            'default_invoice_report_layout': invoice_report_layout,
            'default_logo': self.company_id.logo,
            'default_total_on_header': self.company_id.total_on_header,
            'default_header_color': self.company_id.header_color,
            'default_header_text_color': self.company_id.header_text_color,
            'default_line1_color': self.company_id.line1_color,
            'default_line2_color': self.company_id.line2_color,
            'default_invoice_without_header_footer': self.company_id.invoice_without_header_footer,
            'default_show_table_border': self.company_id.show_table_border,
            'default_approved_by': self.company_id.approved_by,
            'default_received_by': self.company_id.received_by,
            'default_prepared_by': self.company_id.prepared_by,
            'default_prepared_person': self.company_id.prepared_person,
            'default_display_logo': self.company_id.display_logo,
            'default_salesman': self.company_id.salesman,
            'default_date_of_supply': self.company_id.date_of_supply,
            'default_salesman_name': self.company_id.salesman_name,
            'default_bank_in_report_default_or_not': self.company_id.bank_in_report_default_or_not,
        }
        return action
