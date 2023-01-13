# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from num2words import num2words
import math
from datetime import datetime
from odoo.http import request


class AccountMoveExtended(models.Model):
    _inherit = 'account.move'

    customer_po = fields.Char(string="Customer PO#")
    customer_po_date = fields.Date(string="PO Date")
    our_ref = fields.Char(string="Our Reference")
    place_of_supply = fields.Char(string="Place of Supply")
    currency = fields.Char(string="Currency")
    print_to_report = fields.Boolean("Show in Report", default=True)
    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',
                                              check_company=True, readonly=True,
                                              states={'draft': [('readonly', False)]},
                                              default=1)
    terms_and_conditions = fields.One2many('invoice_data_details', 'pro_terms')
    contact_id = fields.Many2one('res.partner', string='Contact Person')
    child_ids = fields.Many2one('res.partner', string='Contact Person')
    child_ids_partner = fields.Boolean(string='child_ids_partner')
    total_discount = fields.Float('Discount Total', compute="_compute_total_discount_amount")
    total_without_discount = fields.Float('Total Excl Discount', compute="_compute_without_discount_amount")
    amount_total_words = fields.Char("Amount (In Words)", compute="_compute_amount_total_words")
    amount_total_arabic = fields.Char("Amount (In Words)", compute="_compute_amount_total_arabic")
    amount_in_words = fields.Char(string='Amount', readonly=True)
    bank_in_report = fields.Boolean('Print BANK Details',
                                    default=lambda self: self.env.company.bank_in_report_default_or_not)


    def _compute_total_discount_amount(self):
        for invoice in self:
            total = 0.0
            for line in invoice.invoice_line_ids:
                total += (line.discount / 100) * (line.price_unit * line.quantity)
            invoice.total_discount = total

    def _compute_without_discount_amount(self):
        for invoice in self:
            total = 0.0
            for line in invoice.invoice_line_ids:
                total += line.price_unit * line.quantity
            invoice.total_without_discount = total

    @api.onchange('partner_id')
    def get_contacts(self):
        vendor = self.env['res.partner'].search([('customer_rank', '=', 0)])
        ids = []
        if self.contact_id:
            self.contact_id = False
        for rec in self:
            if rec.partner_id.child_ids:
                for i in rec.partner_id.child_ids:
                    ids.append(i.id)
        if len(ids) == 0:
            self.child_ids_partner = True
        else:
            self.child_ids_partner = False
        return {'domain': {'contact_id': [('id', 'in', ids)]}}

    @api.depends('amount_total_arabic')
    def _compute_amount_total_arabic(self):
        for i in self:
            i.amount_total_arabic = False
            unit = i.env['ir.translation'].sudo().search(
                [('name', '=', 'res.currency,currency_unit_label'), ('lang', '=', 'ar_001'),
                 ('state', '=', 'translated')], limit=1)
            sub_unit = i.env['ir.translation'].sudo().search(
                [('name', '=', 'res.currency,currency_subunit_label'), ('lang', '=', 'ar_001'),
                 ('state', '=', 'translated')], limit=1)
            amount = '{:.2f}'.format(i.amount_total)
            if unit and amount:
                b = num2words(float(str(amount).split('.')[0]), lang='ar') + " " + unit.value
                if float(str(amount).split('.')[1]) > 0.00:
                    if sub_unit:
                        c = "و " + num2words(float(str(amount).split('.')[1]), lang='ar') + " " + sub_unit.value
                        i.amount_total_arabic = b + " " + c
                else:
                    i.amount_total_arabic = b

    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        """Compute Function To Translate Total Amount Purchase To English"""
        for order in self:
            sub_unit = self.env['ir.translation'].sudo().search(
                [('name', '=', 'res.currency,currency_subunit_label'), ('lang', '=', 'ar_001'),
                 ('res_id', '=', self.currency_id.id), ('state', '=', 'translated')], limit=1)
            if order.currency_id.name == "SAR":
                before = order.currency_id.amount_to_text(float(str('{:.2f}'.format(order.amount_total)).split('.')[0]))
                after = \
                    order.currency_id.amount_to_text(
                        float(str('{:.2f}'.format(order.amount_total)).split('.')[1])).split(" ")[
                        0]
                amount = before
                if after != 'Zero':
                    amount += " And " + after + " " + str(sub_unit.src)
                order.amount_total_words = amount
                order.amount_in_words = order.currency_id.amount_to_text(order.amount_total)
            else:
                before = order.currency_id.amount_to_text(float(str('{:.2f}'.format(order.amount_total)).split('.')[0]))
                after = \
                    order.currency_id.amount_to_text(
                        float(str('{:.2f}'.format(order.amount_total)).split('.')[1])).split(" ")[
                        0]
                amount = before
                if after != 'Zero':
                    amount += " And " + after + " " + str(sub_unit.src)
                order.amount_total_words = amount
                order.amount_in_words = order.currency_id.amount_to_text(order.amount_total)


class InvoiceReportVeuz(models.Model):
    _name = 'invoice_data_details'
    _description = 'To add one2many for terms and condition'

    pro_terms = fields.Char('Terms & Conditions')
    name = fields.Char('Terms & Conditions')
    account_id = fields.Many2one('account.move')
    notes = fields.Char('Notes')


class BankDetails(models.Model):
    _inherit = 'res.bank'

    ifsc_code = fields.Char('IBAN')
    bank_branch = fields.Char('Branch Name')
