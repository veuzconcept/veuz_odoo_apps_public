from odoo import api, fields, models

DEFAULT_HEADER_COLOR = '#000000'
DEFAULT_HEADER_TEXT_COLOR = '#FFFFFF'
DEFAULT_LINE1_COLOR = '#eaeaea'
DEFAULT_LINE2_COLOR = '#FFFFFF'


class BaseDocumentLayout(models.TransientModel):
    """
    Customise the custom invoice report layout and display a live preview
    """

    _name = 'vz.report.layout'
    _description = 'Veuz Report Layout'

    invoice_report_layout = fields.Selection([
        ('invoice report ', 'Invoice Report'),
        ('tax invoice', 'Tax Invoice Report')], string='Report Layout')
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True)
    preview = fields.Html(compute='_compute_preview', sanitize=False)
    logo = fields.Binary(readonly=False)
    invoice_without_header_footer = fields.Boolean(string='Without Header And Footer', readonly=False)
    show_table_border = fields.Boolean('Show Borders', readonly=False,
                                       help="show table borders in invoice report")
    approved_by = fields.Boolean('Approved By', readonly=False)
    received_by = fields.Boolean('Received By', readonly=False)
    prepared_by = fields.Boolean('Prepared By', readonly=False)
    prepared_person = fields.Boolean('Prepared By Person Name')
    remove_product_image = fields.Boolean('Remove Product Image',
                                          readonly=False, help="Remove product images from the invoice report")
    display_logo = fields.Boolean('Remove Logo', readonly=False,
                                  help="Remove company logo from the invoice report")
    salesman = fields.Boolean('Salesperson', readonly=False)
    date_of_supply = fields.Boolean('Remove Date Of Supply', readonly=False,
                                    help="Remove date of supply from the invoice report")
    salesman_name = fields.Boolean('Salesperson Name', readonly=False)
    total_on_header = fields.Boolean('Remove Header Total',
                                     readonly=False, help="Remove total price from the invoice header")
    bank_in_report_default_or_not = fields.Boolean('Bank Account', readonly=False)
    header_color = fields.Char(string='Background', readonly=False)
    header_text_color = fields.Char(string='Text', readonly=False)
    custom_colors = fields.Boolean(compute="_compute_custom_colors", readonly=False)
    default_line_colors = fields.Boolean(compute="_compute_default_line_colors", readonly=False)
    line1_color = fields.Char(string='Line 1', readonly=False)
    line2_color = fields.Char(string='Line 2', readonly=False)
    report_status = fields.Char(string='Report Status', readonly=False)

    @api.depends('header_color', 'header_text_color')
    def _compute_custom_colors(self):
        for wizard in self:
            header_color = wizard.header_color or ''
            header_text_color = wizard.header_text_color or ''
            if header_color != DEFAULT_HEADER_COLOR or header_text_color != DEFAULT_HEADER_TEXT_COLOR:
                wizard.custom_colors = True

    @api.depends('line1_color', 'line2_color')
    def _compute_default_line_colors(self):
        for wizard in self:
            line1_color = wizard.line1_color
            line2_color = wizard.line2_color
            if line1_color != DEFAULT_LINE1_COLOR or line2_color != DEFAULT_LINE2_COLOR:
                wizard.default_line_colors = True

    @api.onchange('custom_colors')
    def _onchange_custom_colors(self):
        for wizard in self:
            if not wizard.custom_colors:
                wizard.header_color = DEFAULT_HEADER_COLOR
                wizard.header_text_color = DEFAULT_HEADER_TEXT_COLOR

    @api.onchange('default_line_colors')
    def _onchange_default_line_colors(self):
        for wizard in self:
            if not wizard.default_line_colors:
                wizard.line1_color = DEFAULT_LINE1_COLOR
                wizard.line2_color = DEFAULT_LINE2_COLOR

    # @api.onchange('invoice_report_layout')
    # def onchange_invoice_report_layout(self):
    #     for rec in self:
    #         if not rec.invoice_report_layout:
    #             rec.company_id.preview_invoice_report_layout_id = 'sec'

    def document_layout_save(self):
        for wizard in self:
            if wizard.invoice_report_layout == 'invoice report':
                invoice_report_layout = False
            else:
                invoice_report_layout = wizard.invoice_report_layout
            wizard.company_id.invoice_report_layout_id = invoice_report_layout
            wizard.company_id.total_on_header = wizard.total_on_header
            wizard.company_id.logo = wizard.logo
            wizard.company_id.header_color = wizard.header_color
            wizard.company_id.header_text_color = wizard.header_text_color
            wizard.company_id.line1_color = wizard.line1_color
            wizard.company_id.line2_color = wizard.line2_color
            wizard.company_id.invoice_without_header_footer = wizard.invoice_without_header_footer
            wizard.company_id.show_table_border = wizard.show_table_border
            wizard.company_id.approved_by = wizard.approved_by
            wizard.company_id.received_by = wizard.received_by
            wizard.company_id.prepared_by = wizard.prepared_by
            wizard.company_id.prepared_person = wizard.prepared_person
            wizard.company_id.display_logo = wizard.display_logo
            wizard.company_id.salesman = wizard.salesman
            wizard.company_id.date_of_supply = wizard.date_of_supply
            wizard.company_id.salesman_name = wizard.salesman_name
            wizard.company_id.bank_in_report_default_or_not = wizard.bank_in_report_default_or_not
            report_status = wizard.company_id.report_status()
            model = self.env.ref('account.model_account_move')
            if report_status == 'both':
                sec_report = self.env.ref('tax_invoice.tax_invoice_report_pulse_infotech')
                sec_report_without_payment = self.env.ref('tax_invoice.tax_without_paymnt_report_pulse_infotech')
                first_report = self.env.ref(
                    'veuz_ksa_tax_invoice_report_custom_default.report_custom_invoices_with_payment')
                first_report_without_payment = self.env.ref(
                    'veuz_ksa_tax_invoice_report_custom_default.report_custom_invoices')
                if wizard.company_id.invoice_report_layout_id == 'tax invoice':
                    first_report.binding_model_id = False
                    sec_report.binding_model_id = model.id
                    first_report_without_payment.binding_model_id = False
                    sec_report_without_payment.binding_model_id = model.id
                else:
                    first_report.binding_model_id = model.id
                    sec_report.binding_model_id = False
                    first_report_without_payment.binding_model_id = model.id
                    sec_report_without_payment.binding_model_id = False
            elif report_status == 'invoice report':
                first_report = self.env.ref(
                    'veuz_ksa_tax_invoice_report_custom_default.report_custom_invoices_with_payment')
                first_report_without_payment = self.env.ref(
                    'veuz_ksa_tax_invoice_report_custom_default.report_custom_invoices')
                first_report.binding_model_id = model.id
                first_report_without_payment.binding_model_id = model.id
            elif report_status == 'tax invoice':
                sec_report = self.env.ref('tax_invoice.tax_invoice_report_pulse_infotech')
                sec_report_without_payment = self.env.ref('tax_invoice.tax_without_paymnt_report_pulse_infotech')
                sec_report.binding_model_id = model.id
                sec_report_without_payment.binding_model_id = model.id

    @api.depends('invoice_report_layout', 'logo', 'header_color', 'header_text_color', 'line1_color', 'line2_color',
                 'invoice_without_header_footer', 'show_table_border', 'approved_by', 'received_by', 'prepared_by',
                 'prepared_person', 'display_logo', 'salesman', 'date_of_supply', 'total_on_header', 'salesman_name',
                 'bank_in_report_default_or_not')
    def _compute_preview(self):
        """ compute a qweb based preview to display on the wizard """
        for wizard in self:
            wizard.report_status = wizard.company_id.report_status()
            if wizard.invoice_report_layout == 'invoice report':
                invoice_report_layout = False
            else:
                invoice_report_layout = wizard.invoice_report_layout
            wizard.company_id.preview_invoice_report_layout_id = invoice_report_layout
            wizard.company_id.preview_total_on_header = wizard.total_on_header
            wizard.company_id.preview_logo = wizard.logo
            wizard.company_id.preview_header_color = wizard.header_color
            wizard.company_id.preview_header_text_color = wizard.header_text_color
            wizard.company_id.preview_line1_color = wizard.line1_color
            wizard.company_id.preview_line2_color = wizard.line2_color
            wizard.company_id.preview_invoice_without_header_footer = wizard.invoice_without_header_footer
            wizard.company_id.preview_show_table_border = wizard.show_table_border
            wizard.company_id.preview_approved_by = wizard.approved_by
            wizard.company_id.preview_received_by = wizard.received_by
            wizard.company_id.preview_prepared_by = wizard.prepared_by
            wizard.company_id.preview_prepared_person = wizard.prepared_person
            wizard.company_id.preview_display_logo = wizard.display_logo
            wizard.company_id.preview_salesman = wizard.salesman
            wizard.company_id.preview_date_of_supply = wizard.date_of_supply
            wizard.company_id.preview_salesman_name = wizard.salesman_name
            wizard.company_id.preview_bank_in_report_default_or_not = wizard.bank_in_report_default_or_not
            if wizard.report_status == 'both':
                if wizard.invoice_report_layout == 'tax invoice':
                    ir_ui_view = wizard.env['ir.ui.view']._render_template(
                        'veuz_report_fields.preview_tax_report_layout_template')
                else:
                    ir_ui_view = wizard.env['ir.ui.view']._render_template(
                        'veuz_report_fields.custom_report_invoice_wizard_preview')
            elif wizard.report_status == 'invoice report':
                ir_ui_view = wizard.env['ir.ui.view']._render_template(
                    'veuz_report_fields.custom_report_invoice_wizard_preview')
            elif wizard.report_status == 'tax invoice':
                ir_ui_view = wizard.env['ir.ui.view']._render_template(
                    'veuz_report_fields.preview_tax_report_layout_template')
            wizard.preview = ir_ui_view
