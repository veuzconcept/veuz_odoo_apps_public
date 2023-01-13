from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _default_report_logo(self):
        return self.env.company.logo

    invoice_without_header_footer = fields.Boolean('Invoice Without Header And Footer')
    approved_by = fields.Boolean('Approved By')
    received_by = fields.Boolean('Received By')
    prepared_by = fields.Boolean('Prepared BY')
    prepared_person = fields.Boolean('Prepared By Person Name')
    remove_product_image = fields.Boolean('Product Image')
    show_table_border = fields.Boolean('Table Border')
    display_logo = fields.Boolean('Company Logo')
    salesman = fields.Boolean('Salesperson')
    salesman_name = fields.Boolean('Salesperson Name')
    total_on_header = fields.Boolean('Header Total')
    date_of_supply = fields.Boolean('Date Of Supply')
    header_img = fields.Binary('Header Image ')
    footer_img = fields.Binary('Footer Image ')
    compny_fax_id = fields.Char(string="Fax")
    bank_in_report_default_or_not = fields.Boolean('Bank Account')
    header_color = fields.Char('Background', default='#000000')
    header_text_color = fields.Char('Text', default='#FFFFFF')
    line1_color = fields.Char('Table Line 1', default='#eaeaea')
    line2_color = fields.Char('Table Line 2', default='#FFFFFF')
    invoice_report_layout_id = fields.Selection([
        ('invoice report ', 'Invoice Report'),
        ('tax invoice', 'Tax Invoice Report')], string='Report Layout')
    preview_invoice_report_layout_id = fields.Selection([
        ('invoice report ', 'Invoice Report'),
        ('tax invoice', 'Tax Invoice Report')], string='Report Layout')
    report_status = fields.Char(string='Report Status')

    preview_invoice_without_header_footer = fields.Boolean('Invoice Without Header And Footer')
    preview_approved_by = fields.Boolean('Approved By')
    preview_received_by = fields.Boolean('Received By')
    preview_prepared_by = fields.Boolean('Prepared BY')
    preview_prepared_person = fields.Boolean('Prepared By Person Name')
    preview_remove_product_image = fields.Boolean('Product Image')
    preview_show_table_border = fields.Boolean('Table Border')
    preview_display_logo = fields.Boolean('Company Logo')
    preview_salesman = fields.Boolean('Salesperson')
    preview_salesman_name = fields.Boolean('Salesperson Name')
    preview_total_on_header = fields.Boolean('Header Total')
    preview_date_of_supply = fields.Boolean('Date Of Supply')
    preview_header_img = fields.Binary('Header Image ')
    preview_footer_img = fields.Binary('Footer Image ')
    preview_compny_fax_id = fields.Char(string="Fax")
    preview_logo = fields.Binary(string="Logo", default=_default_report_logo)
    preview_bank_in_report_default_or_not = fields.Boolean('Bank Account')
    preview_header_color = fields.Char('Background', default='#000000')
    preview_header_text_color = fields.Char('Text', default='#FFFFFF')
    preview_line1_color = fields.Char('Table Line 1', default='#eaeaea')
    preview_line2_color = fields.Char('Table Line 2', default='#FFFFFF')
    invoice_report_layout = fields.Boolean('Is any invoice_report_layout', compute='compute_invoice_report_layout')

    @api.model
    def compute_invoice_report_layout(self):
        for rec in self:
            rec.invoice_report_layout = rec.report_status()


    def report_status(self):
        invoice_report = self.env['ir.module.module'].search(
            [('name', '=', 'veuz_ksa_tax_invoice_report_custom_default')])
        tax_invoice = self.env['ir.module.module'].search([('name', '=', 'tax_invoice')])
        if invoice_report.state == 'installed' and tax_invoice.state == 'uninstalled':
            visible_invoice_layout_id = 'invoice report'
        elif invoice_report.state == 'uninstalled' and tax_invoice.state == 'installed':
            visible_invoice_layout_id = 'tax invoice'
        elif invoice_report.state == 'installed' and tax_invoice.state == 'installed':
            visible_invoice_layout_id = 'both'
        else:
            visible_invoice_layout_id = False
        return visible_invoice_layout_id


class ResPartnerExtended(models.Model):
    _inherit = 'res.partner'

    fax_id = fields.Char(string="Fax")
