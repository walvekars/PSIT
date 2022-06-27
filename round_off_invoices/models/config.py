# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Treesa Maria Jude(<https://www.cybrosys.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <https://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.tools import float_is_zero
from openerp.exceptions import ValidationError
#from openerp.exceptions import UserError
from openerp import fields, models, api, _
#from openerp import api, models,fields, _
from openerp.exceptions import except_orm,Warning,RedirectWarning
import pdb

class AccountRoundOff(models.Model):
    _inherit = 'account.invoice'

    round_off_value = fields.Float(string='Round Off Amount')
    rounded_total = fields.Float(compute='_compute_amount_value', string='Gross Total')

    @api.one
    @api.depends( 'amount_total','rounded_total','round_off_value')        
    def _compute_amount_value(self):
	round_off_value = 0.00
        self.rounded_total = self.amount_total + self.round_off_value


    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line.invoice_amount',
        'move_id.line_id.amount_residual',
        'move_id.line_id.currency_id')
    def _compute_residual(self):
        residual = 0.0
        residual_company_signed = 0.0
        sign = self.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in self.sudo().move_id.line_id:
            if line.account_id.type in ('receivable', 'payable'):
                residual_company_signed += line.amount_residual
                if line.currency_id == self.currency_id:
                    residual += line.amount_residual_currency if line.currency_id else line.amount_residual
                else:
                    from_currency = (line.currency_id and line.currency_id.with_context(
                        date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
                    residual += from_currency.compute(line.amount_residual, self.currency_id)
        self.residual_company_signed = abs(residual_company_signed) * sign
        self.residual_signed = abs(residual) * sign
	self.residual = residual
        digits_rounding_precision = self.currency_id.rounding
        if float_is_zero(self.residual, precision_rounding=digits_rounding_precision):
            self.reconciled = True
        else:
            self.reconciled = False
    


    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines """
        account_move = self.env['account.move']

        for inv in self:

            if not inv.journal_id.sequence_id:
                raise ValidationError(_('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise UserError(_('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice
            company_currency = inv.company_id.currency_id
            iml = inv._get_analytic_lines()

            # I disabled the check_total feature
            if self.env['res.users'].has_group('account.group_supplier_inv_check_total'):
                if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.rounded_total) >= (inv.currency_id.rounding / 2.0):
                    raise except_orm(_('Bad Total!'), _('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            # create move lines (one per invoice line + eventual taxes and analytic lines)
            #iml+= self.env['account.invoice.line'].move_line_get(self.id)
            #iml += inv.tax_line_move_line_get()
            iml += self.env['account.invoice.tax'].move_line_get(inv.id)

            diff_currency = inv.currency_id != company_currency
            

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = inv.number
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency,ref, iml)


	    #create round off account if not created
 	    account_obj = self.env['account.account']
	    acc_id = account_obj.search([('name','=','Round Off')],limit=1)	
	    if not acc_id :
		asset_type = self.env.ref('account.data_account_type_asset')  
		acc_id = account_obj.create({
					'name':  'Round Off',
					'code':  '100720',
					'user_type':asset_type.id,
					'company_id': inv.company_id.id,
					})

            name = inv.name or '/'
            if inv.payment_term:
                totlines = inv.with_context(ctx).payment_term.with_context(currency_id=company_currency.id).compute(
                    total, date_invoice)[0]
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency
                        
                    if self.type == 'out_invoice':
                        iml.append({
                            'type': 'dest',
                            'name': name,
                            'price': t[1] + self.round_off_value,
                            'account_id': inv.account_id.id,
                            'date_maturity': t[0],
                            'amount_currency': diff_currency and amount_currency,
                            'currency_id': diff_currency and inv.currency_id.id,
                            'invoice_id': inv.id
                        })
                        #ir_values = self.env['ir.values']
                        #acc_id = ir_values.get_default('account.config.settings', 'round_off_account')
                        
                        iml.append({
                            'type': 'dest',
                            'name': "Round off",
                            'price': -self.round_off_value,
                            'account_id': acc_id.id,
                            'date_maturity': t[0],
                            'amount_currency': diff_currency and amount_currency,
                            'currency_id': diff_currency and inv.currency_id.id,
                            'invoice_id': inv.id
                        })
		    if self.type == 'in_invoice':
		        
                        if self.round_off_value >= 0 :	
                            rounded_total = -(abs(t[1]) + abs(self.round_off_value))
                            round_off_value = self.round_off_value
                        else :		
                            rounded_total = t[1] + abs(self.round_off_value)
                            round_off_value = self.round_off_value
                        iml.append({
                            'type': 'dest',
                            'name': name,
                            'price': rounded_total,
                            'account_id': inv.account_id.id,
                            'date_maturity': t[0],
                            'amount_currency': diff_currency and amount_currency,
                            'currency_id': diff_currency and inv.currency_id.id,
                            'invoice_id': inv.id
                        })
                        #ir_values = self.env['ir.values']
                        #acc_id = ir_values.get_default('account.config.settings', 'round_off_account')
                        iml.append({
                            'type': 'dest',
                            'name': "Round off",
                            'price': round_off_value,
                            'account_id': acc_id.id,
                            'date_maturity': t[0],
                            'amount_currency': diff_currency and amount_currency,
                            'currency_id': diff_currency and inv.currency_id.id,
                            'invoice_id': inv.id
                        })
                    #else:

                        #iml.append({
                            #'type': 'dest',
                            #'name': name,
                            #'price': t[1],
                            #'account_id': inv.account_id.id,
                            #'date_maturity': t[0],
                            #'amount_currency': diff_currency and amount_currency,
                            #'currency_id': diff_currency and inv.currency_id.id,
                            #'invoice_id': inv.id
                        #})

            else:
                if self.type == 'out_invoice':
		  
                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': total + self.round_off_value,
                        'account_id': inv.account_id.id,
                        'date_maturity': inv.date_due,
                        'amount_currency': diff_currency and total_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
                    #ir_values = self.env['ir.values']
                    #acc_id = ir_values.get_default('account.config.settings', 'round_off_account')
                    
                    iml.append({
                        'type': 'dest',
                        'name': "Round off",
                        'price': -self.round_off_value,
                        'account_id': acc_id.id,
                        'date_maturity': inv.date_due,
                        'amount_currency': diff_currency and total_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
		if self.type == 'in_invoice':
		  
                    if self.round_off_value >= 0 :	
                        rounded_total = -(abs(total) + abs(self.round_off_value))
                        round_off_value = self.round_off_value
                    else :		
                        rounded_total = total + abs(self.round_off_value)
                        round_off_value = self.round_off_value
                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': rounded_total,
                        'account_id': inv.account_id.id,
                        'date_maturity': inv.date_due,
                        'amount_currency': diff_currency and total_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
                    #ir_values = self.env['ir.values']
                    #acc_id = ir_values.get_default('account.config.settings', 'round_off_account')
                    
                    iml.append({
                        'type': 'dest',
                        'name': "Round off",
                        'price': round_off_value,
                        'account_id': acc_id.id,
                        'date_maturity': inv.date_due,
                        'amount_currency': diff_currency and total_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'invoice_id': inv.id
                    })
                #else:
                    #iml.append({
                        #'type': 'dest',
                        #'name': name,
                        #'price': total,
                        #'account_id': inv.account_id.id,
                        #'date_maturity': inv.date_due,
                        #'amount_currency': diff_currency and total_currency,
                        #'currency_id': diff_currency and inv.currency_id.id,
                        #'invoice_id': inv.id
                    #})
            
            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)

            date = inv.date_invoice
            
            line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            line = inv.finalize_invoice_move_lines(line)

            date = date_invoice
            move_vals = {
                'ref': inv.reference,
                'line_id': line,
                'journal_id': journal.id,
                'date': inv.date_invoice,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
            }
            ctx['company_id'] = inv.company_id.id
            period = inv.period_id
            if not period:
                period = period.with_context(ctx).find(date_invoice)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id
            ctx['invoice'] = inv
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'period_id': period.id,
                #'date': date,
                'move_name': move.name,
            }
            inv.with_context(ctx).write(vals)
        return True
