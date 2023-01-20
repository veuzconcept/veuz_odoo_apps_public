import time
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseDownPayment(models.TransientModel):
    _name = "purchase.advance.payment"

    @api.model
    def _count(self):
        return len(self._context.get('active_ids', []))

    @api.model
    def _default_product_id(self):
        product_id = self.env['ir.config_parameter'].sudo().get_param('purchase.default_down_payment_product_id')
        return self.env['product.product'].browse(int(product_id)).exists()

    @api.model
    def _default_deposit_account_id(self):
        return self._default_product_id()._get_product_accounts()['income']

    @api.model
    def _default_deposit_taxes_id(self):
        return self._default_product_id().taxes_id

    @api.model
    def _default_has_down_payment(self):
        if self._context.get('active_model') == 'purchase.order' and self._context.get('active_id', False):
            purchase_order = self.env['purchase.order'].browse(self._context.get('active_id'))
            return purchase_order.order_line.filtered(
                lambda purchase_order_line: purchase_order_line.is_downpayment
            )
        return False

    @api.model
    def _default_currency_id(self):
        if self._context.get('active_model') == 'purchase.order' and self._context.get('active_id', False):
            purchase_order = self.env['purchase.order'].browse(self._context.get('active_id'))
            return purchase_order.currency_id

    purchase_active_id = fields.Many2one('purchase.order', string='current purchase')

    advance_payment_method = fields.Selection([
        ('delivered', 'Regular bill'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
    ], string='Create Bill', default='delivered', required=True,
        help="A standard bill is issued with all the order lines ready for billing, \
        according to their billing policy (based on ordered or delivered quantity).",
    )

    deduct_down_payments = fields.Boolean('Deduct down payments', default=True)
    has_down_payments = fields.Boolean('Has down payments', default=_default_has_down_payment, readonly=True)
    product_id = fields.Many2one('product.product', string='Down Payment Product',
                                 domain=[('type', '=', 'service')],
                                 default=_default_product_id)
    count = fields.Integer(default=_count, string='Order Count')
    amount = fields.Float('Down Payment Amount', digits='Account',
                          help="The percentage of amount to be billed in advance, taxes excluded.")
    currency_id = fields.Many2one('res.currency', string='Currency', default=_default_currency_id)
    fixed_amount = fields.Monetary('Down Payment Amount (Fixed)',
                                   help="The fixed amount to be billed in advance, taxes excluded.")
    deposit_account_id = fields.Many2one("account.account", string="Income Account",
                                         domain=[('deprecated', '=', False)],
                                         help="Account used for deposits", default=_default_deposit_account_id)
    deposit_taxes_id = fields.Many2many("account.tax", string="Customer Taxes", help="Taxes used for deposits",
                                        default=_default_deposit_taxes_id)

    @api.onchange('advance_payment_method')
    def onchange_advance_payment_method(self):
        if self.advance_payment_method == 'percentage':
            amount = self.default_get(['amount']).get('amount')
            return {'value': {'amount': amount}}
        return {}

    def _get_advance_details(self, purchase_orders):
        context = {'lang': purchase_orders.partner_id.lang}
        if self.advance_payment_method == 'percentage':
            amount = purchase_orders.amount_untaxed * self.amount / 100
            name = _("Down payment of %s%%") % (self.amount)
        else:
            amount = self.fixed_amount
            name = _('Down Payment')
        del context
        return amount, name

    def _prepare_po_line(self, order=None, analytic_tag_ids=None, tax_ids=None, amount=None):
        context = {'lang': order.partner_id.lang}
        so_values = {
            'name': _('Down Payment: %s') % (time.strftime('%m %Y'),),
            'price_unit': amount,
            'product_qty': 0.0,
            'qty_to_invoice': 1,
            'order_id': order.id,
            'product_uom': self.product_id.uom_id.id,
            'product_id': self.product_id.id,
            'analytic_tag_ids': analytic_tag_ids,
            'taxes_id': [(6, 0, tax_ids)],
            'is_downpayment': True,
            'sequence': order.order_line and order.order_line[-1].sequence + 1 or 10,
        }
        del context
        return so_values

    def downpayment_line(self, purchase_orders):
        purchase_line_obj = self.env['purchase.order.line']
        # Create Down Payment product if not
        if (self.advance_payment_method == 'percentage' and self.amount <= 0.00) or (
                self.advance_payment_method == 'fixed' and self.fixed_amount <= 0.00):
            raise UserError(_('The value of the down payment amount must be positive.'))

        payment_product_id = self.env['ir.config_parameter'].sudo().get_param(
            'purchase.default_down_payment_product_id')


        if not self.product_id or payment_product_id == 0:
            raise UserError(
                _('The product used to bill a down payment ". Please update your down payment product to be able to create a deposit bill.'))

        self.product_id = self.env['product.product'].sudo().browse(int(payment_product_id))
        for order in self:
            amount, name = self._get_advance_details(purchase_orders)
            if self.product_id.type != 'service':
                raise UserError(
                    _("The product used to bill a down payment should be of type 'Service'. Please use another product or update this product."))

            # supplier_taxes_id
            taxes = self.product_id.supplier_taxes_id.filtered(
                lambda r: not purchase_orders.company_id or r.company_id == purchase_orders.company_id)
            tax_ids = purchase_orders.fiscal_position_id.map_tax(taxes).ids
            analytic_tag_ids = []
            for line in purchase_orders.order_line:
                analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
            so_line_values = self._prepare_po_line(purchase_orders, analytic_tag_ids, tax_ids, amount)
            down_payments_section_line = {
                'display_type': 'line_section',
                'name': _('Down Payments'),
                'product_id': False,
                'product_qty': 0.0,
                'order_id': purchase_orders.id,
                'product_uom': False,
                'analytic_tag_ids': False,
                'taxes_id': False,
                'is_downpayment': True,
                'sequence': (purchase_orders.order_line and purchase_orders.order_line[-1].sequence + 1 or 10) - 1,
            }
            so_line = purchase_line_obj.create(down_payments_section_line)
            so_line = purchase_line_obj.create(so_line_values)
            so_line_values['label'] = name
            return so_line_values

    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<     create_invoices     >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
    def create_invoices(self):
        self.purchase_active_id = self._context.get('active_id')
        purchase_orders = self.env['purchase.order'].browse(self._context.get('active_ids', []))
        if self.advance_payment_method == 'delivered':
            # ('is_shipped', '=', True), ('state','not in', ('purchase','done')), ('incoming_picking_count', '=', 0)
            if not purchase_orders.is_shipped:
                raise UserError(_('There is no invoiceable line. If a product has a control policy based on received '
                                  'quantity, please make sure that a quantity has been received.'))
            return purchase_orders.with_context(purchase_orders=purchase_orders,
                                                po_line_values={}).action_create_invoice()
        else:
            downpayment_line = self.downpayment_line(purchase_orders)
            return purchase_orders.with_context(purchase_orders=purchase_orders,
                                                po_line_values=downpayment_line).action_create_invoice()


class ProductTemplate(models.Model):
    _inherit = 'product.product'

    invoice_policy = fields.Selection([
        ('order', 'Ordered quantities'),
        ('delivery', 'Delivered quantities')], string='Invoicing Policy',
        help='Ordered Quantity: Invoice quantities ordered by the customer.\n'
             'Delivered Quantity: Invoice quantities delivered to the customer.',
        default='order')

    down_payment_product_id = fields.Integer(string='Invoicing Policy',
                                             help='Ordered Quantity: Invoice quantities ordered by the customer.\n'
                                                  'Delivered Quantity: Invoice quantities delivered to the customer.',
                                             )
