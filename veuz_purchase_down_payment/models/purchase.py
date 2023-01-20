from odoo import models, fields, api, _
from odoo.tools.float_utils import float_is_zero
from itertools import groupby
from odoo.tools.misc import format_date
from odoo.exceptions import UserError, ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_down_payment_product_id = fields.Many2one(
        'product.product',
        'Deposit Product',
        domain="[('type', '=', 'service')]",
        default_model='product.product',
        help='Default product used for payment advances')

    @api.onchange('default_down_payment_product_id')
    def onchange_default_down_payment_product_id(self):
        if self.default_down_payment_product_id:
            self.env['ir.config_parameter'].sudo().set_param('purchase.default_down_payment_product_id',
                                                             self.default_down_payment_product_id.id)
        else:
            self.default_down_payment_product_id = False
            self.env['ir.config_parameter'].sudo().set_param('purchase.default_down_payment_product_id',0)

class account(models.Model):
    _inherit = 'account.move'

    purchase_active_id = fields.Many2one('purchase.advance.payment', compute='_get_active_id', )

    @api.depends('purchase_id')
    def _get_active_id(self):
        self.purchase_active_id = self.env['purchase.advance.payment'].browse(self.purchase_active_id)
        return self.purchase_active_id

    @api.constrains('ref', 'move_type', 'partner_id', 'journal_id', 'invoice_date')
    def _check_duplicate_supplier_reference(self):
        moves = self.filtered(lambda move: move.is_purchase_document() and move.ref)
        if not moves:
            return
        self.env["account.move"].flush([
            "ref", "move_type", "invoice_date", "journal_id",
            "company_id", "partner_id", "commercial_partner_id",
        ])
        self.env["account.journal"].flush(["company_id"])
        self.env["res.partner"].flush(["commercial_partner_id"])

        # /!\ Computed stored fields are not yet inside the database.
        self._cr.execute('''
            SELECT move2.id
            FROM account_move move
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_partner partner ON partner.id = move.partner_id
            INNER JOIN account_move move2 ON
                move2.ref = move.ref
                AND move2.company_id = journal.company_id
                AND move2.commercial_partner_id = partner.commercial_partner_id
                AND move2.move_type = move.move_type
                AND (move.invoice_date is NULL OR move2.invoice_date = move.invoice_date)
                AND move2.id != move.id
            WHERE move.id IN %s
        ''', [tuple(moves.ids)])
        duplicated_moves = self.browse([r[0] for r in self._cr.fetchall()])

        if not self.env['ir.module.module'].sudo().search(
                [('name', '=', 'veuz_purchase_down_payment'), ('state', '=', 'installed')]):
            if duplicated_moves:
                raise ValidationError(
                    _('Duplicated vendor reference detected. You probably encoded twice the same vendor bill/credit note:\n%s') % "\n".join(
                        duplicated_moves.mapped(lambda m: "%(partner)s - %(ref)s - %(date)s" % {
                            'ref': m.ref,
                            'partner': m.partner_id.display_name,
                            'date': format_date(self.env, m.invoice_date),
                        })
                    ))

    advance_payment_method = fields.Selection([
        ('delivered', 'Regular bill'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
    ], string='Create Bill', default='delivered',
        help="A standard bill is issued with all the order lines ready for billing, \
        according to their billing policy (based on ordered or delivered quantity).",
        related='purchase_active_id.advance_payment_method')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_active_id = fields.Many2one('purchase.advance.payment', compute='_get_active_id', )
    ref_count = fields.Integer(string='dp_count', default=1)

    def _get_active_id(self):
        self.purchase_active_id = False
        if len(self.env['purchase.advance.payment'].search([])) > 1 and self.env['purchase.advance.payment'].search([])[
            -1].purchase_active_id.id == self.id:
            self.purchase_active_id = self.env['purchase.advance.payment'].search([])[-1].id

    advance_payment_method = fields.Selection([
        ('delivered', 'Regular bill'),
        ('percentage', 'Down payment (percentage)'),
        ('fixed', 'Down payment (fixed amount)')
    ], string='Create Bill', default='delivered',
        help="A standard bill is issued with all the order lines ready for billing, \
        according to their billing policy (based on ordered or delivered quantity).",
        related='purchase_active_id.advance_payment_method')

    is_downpayment = fields.Boolean(
        string="Is a down payment", help="Down payments are made when creating bill from a purchase order."
                                         " They are not copied when duplicating a purchase order.")


    def copy_data(self, default=None):
        if default is None:
            default = {}
        if 'order_line' not in default:
            default['order_line'] = [(0, 0, line.copy_data()[0]) for line in
                                     self.order_line.filtered(lambda l: not l.is_downpayment)]
        return super(PurchaseOrder, self).copy_data(default)

    def action_create_invoice(self):
        """Create the invoice associated to the PO.
        """
        if (self.purchase_active_id.advance_payment_method != 'delivered') and ('purchase_orders' in self.env.context):
            po_line_values = self.env.context.get('po_line_values')
        else:
            if 'po_line_values' not in self.env.context:
                raise UserError(_('Down payment context is missing...'))

        purchase_line_id = {}
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        # 1) Prepare invoice vals and clean-up the section lines
        seq = ''
        invoice_vals_list = []
        for order in self:
            if order.invoice_status != 'to invoice':
                continue
            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.

            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).

            for line in order.order_line:
                if order.purchase_active_id.advance_payment_method != 'delivered':
                    if line.display_type == 'line_section':
                        pending_section = line
                        continue
                else:
                    if not line.is_downpayment and line.display_type == 'line_section':
                        pending_section = line
                        continue

                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if order.purchase_active_id.advance_payment_method == 'delivered':
                        if line.is_downpayment and (
                                self.purchase_active_id.advance_payment_method == 'delivered' and not self.purchase_active_id.deduct_down_payments):
                            continue
                        if pending_section:
                            invoice_vals['invoice_line_ids'].append(
                                (0, 0, pending_section._prepare_account_move_line()))
                            pending_section = None
                        invoice_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))
                    else:
                        if pending_section:
                            get_invoice_line = pending_section.prepare_downpayment_account_move_line(po_line_values)
                            invoice_vals['invoice_line_ids'].append((0, 0, get_invoice_line))
                            pending_section = None
                        get_invoice_line = line.prepare_downpayment_account_move_line(po_line_values)
                        invoice_vals['invoice_line_ids'].append((0, 0, get_invoice_line))
                        purchase_line_id = get_invoice_line['purchase_line_id']
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_('There is no invoiceable line. If a product has a control policy based on received '
                              'quantity, please make sure that a quantity has been received.'))

        # 2) group by (company_id, partner_id, currency_id) for batch creation

        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (
                x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })

            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        if self.purchase_active_id.advance_payment_method != 'delivered':
            if po_line_values:
                invoice_line_ids = [(0, 0, {'display_type': False,
                                            'sequence': int(po_line_values['sequence']),
                                            'name': po_line_values['label'],
                                            'product_id': int(po_line_values['product_id']),
                                            'product_uom_id': 1,
                                            'quantity': 1.0,
                                            'price_unit': float(po_line_values['price_unit']),
                                            'tax_ids': po_line_values['taxes_id'],
                                            'purchase_line_id': purchase_line_id  # Bill count
                                            })]
                invoice_vals_list[0].update(invoice_line_ids=invoice_line_ids)
                if self.partner_ref:
                    reference = _("Downpayment: %s [%s]" % (self.ref_count, invoice_vals_list[0]['ref']))
                    invoice_vals_list[0]['ref'] = reference
                    invoice_vals_list[0]['payment_reference'] = reference
                    self.ref_count = self.ref_count + 1

        # 3) Create bill.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            moves |= AccountMove.with_company(vals['company_id']).create(vals)

        moves.filtered(
            lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

        # return self.action_view_invoice(moves)
        if self._context.get('open_invoices', False):
            return self.action_view_invoice(moves)
        return {'type': 'ir.actions.act_window_close'}


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_downpayment = fields.Boolean(
        string="Is a down payment", help="Down payments are made when creating bill from a purchase order."
                                         " They are not copied when duplicating a purchase order.")

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move)
        res.update({'quantity': -1 if self.is_downpayment else self.qty_to_invoice, })
        return res

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty',
                 'order_id.state')
    def _compute_qty_invoiced(self):
        for line in self:
            # compute qty_invoiced
            qty = 0.0
            for inv_line in line._get_invoice_lines():
                if inv_line.move_id.state not in ['cancel']:
                    if line.order_id.purchase_active_id.advance_payment_method == 'delivered':
                        if inv_line.move_id.move_type == 'in_invoice':
                            qty += inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                        elif inv_line.move_id.move_type == 'in_refund':
                            qty -= inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom)
                        if line.is_downpayment and not line.display_type:
                            qty = 0
                else:
                    if line.is_downpayment and not line.display_type:
                        qty = 0
                line.qty_invoiced = qty

            # compute qty_to_invoice
            if line.order_id.state in ['purchase', 'done']:
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
                if line.is_downpayment and not line.display_type:
                    line.qty_to_invoice = -1
                if line.order_id.purchase_active_id.advance_payment_method == 'delivered':
                    line.qty_to_invoice = 0
            else:
                line.qty_to_invoice = 0

    @api.onchange('is_downpayment')
    def _onchange_is_downpayment(self):
        for rec in self:
            if rec.is_downpayment == True:
                rec.order_id.is_downpayment = True

    def prepare_downpayment_account_move_line(self, po_line_values=None, move=False):
        res = {
            'display_type': self.display_type,
            'sequence': self.sequence,
            'name': '%s: %s' % (self.order_id.name, self.name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'price_unit': '',
            'tax_ids': [(6, 0, self.taxes_id.ids)],
            'analytic_account_id': self.account_analytic_id.id,
            'analytic_tag_ids': [(6, 0, self.analytic_tag_ids.ids)],
            'purchase_line_id': self.id,
        }

        if not move:
            return res

        if self.currency_id == move.company_id.currency_id:
            currency = False
        else:
            currency = move.currency_id

        res.update({
            'move_id': move.id,
            'currency_id': currency and currency.id or False,
            'date_maturity': move.invoice_date_due,
            'partner_id': move.partner_id.id,
        })
        return res
