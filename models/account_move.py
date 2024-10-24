from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    discount_method = fields.Selection([("fixed", "Fixed"), ("percentage", "Percentage")], string="Discount Method")
    discount_amount = fields.Float(string="Discount Amount")
    total_discount = fields.Float(string="- Discount", compute="_compute_total_discount")
    sale_order = fields.Boolean(string='Sale Order', compute='compute_sale_order', default=False)

    def compute_sale_order(self):
        for move in self:
            move.sale_order = bool(move.invoice_line_ids.mapped('sale_line_ids.order_id'))

    @api.onchange("discount_method", "discount_amount", "amount_untaxed")
    def onchange_on_total_discount(self):
        for move in self:
            if move.state == "draft":
                if move.discount_amount and move.discount_method:
                    if move.amount_untaxed:
                        move.total_discount = move.count_total_discount()
                        move.amount_total = (move.amount_untaxed + move.amount_tax) - move.total_discount
                    else:
                        move.total_discount = 0.0
                else:
                    move.total_discount = 0.0

    @api.depends('line_ids.debit',
                 'line_ids.credit',
                 'line_ids.currency_id',
                 'line_ids.amount_currency',
                 'line_ids.amount_residual',
                 'line_ids.amount_residual_currency',
                 'line_ids.payment_id.state',
                 'total_discount')
    def _compute_amount(self):
        res = super(AccountMove, self)._compute_amount()
        for move in self:
            if move.total_discount:
                move.amount_total -= move.total_discount
                move.amount_residual = move.amount_total
            elif move.discount_amount and move.discount_method:
                total_discount = move.count_total_discount()
                move.amount_total -= total_discount
                move.amount_residual = move.amount_total
        return res

    def count_total_discount(self):
        for move in self:
            amount = 0
            if move.discount_amount and move.discount_method:
                if move.discount_method == "fixed":
                    amount = move.discount_amount
                else:
                    amount = round((move.discount_amount * move.amount_untaxed) / 100, 2)
            move.total_discount = amount  # Store the result in total_discount
        return amount

    @api.depends("discount_method", "discount_amount", "amount_untaxed")
    def _compute_total_discount(self):
        for move in self:
            if move.discount_amount and move.discount_method:
                move.total_discount = move.count_total_discount()
            else:
                move.total_discount = 0.0

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        for move in self:
            if move.discount_method == 'fixed':
                if move.discount_amount > move.amount_total:
                    raise UserError(_('You can not add more than the amount in fixed rate'))
            if move.discount_method == 'percentage':
                if move.discount_amount > 100 or move.discount_amount < 0:
                    raise UserError(_('You can not add value less than 0 and greater than 100'))
        return res
