from openerp.osv import fields,osv
from openerp.tools.translate import _
from lxml import etree
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import tools, exceptions
import openerp.addons.decimal_precision as dp
from num2words import num2words
from openerp.tools import amount_to_text
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

from openerp.tools import amount_to_text_en
import pdb


    
    
class psit_account_invoice(models.Model): 
    
    _inherit = 'account.invoice'

    def get_num2words(self,amount,currency):
	if currency == 'INR' :	
		words = num2words(amount, lang='en_IN')
	else :
		words = num2words(amount)
	return words.title()

    
    def amount_to_text(self, amount_total, currency='INR'): 
        return amount_to_text(amount_total, currency)
    
    @api.multi
    def button_compute(self, set_total=False):
        self.button_reset_taxes()
        for invoice in self:
            #pdb.set_trace()
            if set_total:
                invoice.check_total = 0.00
        return True
    
    

    @api.one
    @api.depends('invoice_line.cgst', 'invoice_line.sgst','invoice_line.igst','invoice_line.other_tax')
    def _compute_total_gst(self):
	for line in self.invoice_line:
            self.amount_tax = self.amount_gst = self.amount_gst + line.cgst + line.sgst + line.igst+line.other_tax
            self.amount_cgst = self.amount_cgst + line.cgst 
            self.amount_sgst = self.amount_sgst + line.sgst
            self.amount_igst = self.amount_igst + line.igst
            self.amount_other_tax = self.amount_other_tax + line.other_tax
    

    

    
    @api.multi
    def button_reset_taxes(self):
        
      # code to update main taxes to invoice_lines ------------start          
        invoice_line_obj = self.env["account.invoice.line"]
        taxes_ids = []
        if self.taxes_id:
            taxes_ids = self.taxes_id.ids
            if self.invoice_line:
                invoice_lines = self.invoice_line
                for i in invoice_lines:
                    invoice_line_brow = invoice_line_obj.browse(i.id)
                    invoice_line_brow.write({'invoice_line_tax_id':[(6,0,taxes_ids)]})
                    
                    
      # code to update main taxes to invoice_lines ------------end          


        
        account_invoice_tax = self.env['account.invoice.tax']
        ctx = dict(self._context)
        for invoice in self:
            self._cr.execute("DELETE FROM account_invoice_tax WHERE invoice_id=%s AND manual is False", (invoice.id,))
            self.invalidate_cache()
            partner = invoice.partner_id
            if partner.lang:
                ctx['lang'] = partner.lang
            for taxe in account_invoice_tax.compute(invoice.with_context(ctx)).values():
                account_invoice_tax.create(taxe)
                
                
        # dummy write on self to trigger recomputations
        return self.with_context(ctx).write({'invoice_line': []})

    
    @api.one
    @api.depends('invoice_line.price_subtotal', 'tax_line.amount','tot_duty_percent','amount_gst','invoice_line.invoice_amount')
    def _compute_amount(self):
#         self.amount_sub_total = sum(line.price_subtotal for line in self.invoice_line)
            
        val1 = 0
        invoice_line_account = None
        taxes = []
        for line in self.invoice_line: 
           if line.product_id.name != 'Packing and Forwarding':
               val1 = val1 + line.invoice_amount
               
               if line.invoice_line_tax_id:
                   taxes = line.invoice_line_tax_id.ids

        
	self.invoice_total = val1
        #packing =  (self.amount_sub_total * self.packing_percent) / 100

        #yy = self._get_packing_line(packing)

        
        self.amount_untaxed = self.invoice_total
	#self.amount_untaxed = self.amount_sub_total + packing
        
        tot_duty_payable = (self.amount_untaxed * self.tot_duty_percent) / 100
        
        
        self.amount_tax = self.amount_gst
        self.amount_total = round(self.amount_untaxed + self.amount_tax)
        
        self.roundoff =  (self.amount_total - (self.amount_untaxed + self.amount_tax ))

        self.amount_tot_duty_payable = tot_duty_payable
        
        #self.packing_percent_amt = packing
        
        
        #self.packing_percent = self.packing_percent
        self.tot_duty_percent = self.tot_duty_percent
        
        
        self.amount_tax = sum(line.amount for line in self.tax_line)
        self.amount_total = self.amount_untaxed + self.amount_tax
        #self.button_reset_taxes()
        
        
        
        for tax in self.tax_line:
            name_str=tax.name
            if 'CGST' in name_str :
                self.round_off_cgst=tax.amount
                print self.round_off_cgst
            elif 'SGST' in name_str :
                self.round_off_sgst=tax.amount   
                print self.round_off_sgst
            elif 'IGST' in name_str :
                self.round_off_igst=tax.amount
                print self.round_off_igst
            else:
                self.round_off_other_tax=tax.amount
                print self.round_off_other_tax
                
    
    packing_percent = fields.Float(string = 'Packing and Forwarding' , store=True)
    
    packing_percent_amt = fields.Float(string='Packing and Forwarding', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')



    tot_duty_percent = fields.Float(string = 'Duty Payable %' , store=True)

    amount_tot_duty_payable = fields.Float(string='Total Duty Payable', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')

    
    amount_sub_total = fields.Float(string='Subtotal', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')


    amount_untaxed = fields.Float(string='Untaxed Amount', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Float(string='Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')

                
    roundoff = fields.Float(string='Round Off', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')

                
    #number = fields.Char(related='seq_num', store=True, readonly=True, copy=False)

#GST Columns Mandotary for Report
    amount_gst = fields.Float(string='GST Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_total_gst', track_visibility='always')
    amount_cgst = fields.Float(string='CGST Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_total_gst', track_visibility='always')
    amount_sgst = fields.Float(string='SGST Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_total_gst', track_visibility='always')
    amount_igst = fields.Float(string='IGST Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_total_gst', track_visibility='always')
    amount_other_tax = fields.Float(string='Other Tax Total', digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_total_gst', track_visibility='always')
    round_off_cgst=fields.Float(string="Round Off CGST", digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    round_off_sgst=fields.Float(string="Round Off SGST", digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    round_off_igst=fields.Float(string="Round Off IGST", digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')
    round_off_other_tax=fields.Float(string="Round Off Other TAX", digits=dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_amount')

    delivery_terms = fields.Char("Delivery Terms",size=256)
    


    
    def create(self, cr, uid, vals, context=None):
        if not context:
            context={}

        if 'origin' in vals and 'type' in vals:
            # code to generate invoice, validate and paid it before generating DO ----start 
            if not context:
                so_obj = self.pool.get("sale.order")
                so_id = so_obj.search(cr,1,[('name','=',vals['origin'])])
                if so_id:
                    so_brow = so_obj.browse(cr,1,so_id[0])
                    #packing_percent = so_brow.packing_percent
                    #packing_amount = so_brow.packing_amount
                    partner_invoice_id = None or False
                    partner_shipping_id = None or False
                    
                    if so_brow.partner_invoice_id:
                        partner_invoice_id = so_brow.partner_invoice_id.id
                    if so_brow.partner_shipping_id:
                        partner_shipping_id = so_brow.partner_shipping_id.id
                        
                    if so_brow.taxes_id:
                        tax_ids = so_brow.taxes_id.ids
                        taxes_id = [(6,0,tax_ids)]
                        vals.update({'taxes_id':taxes_id})
                    
                    vals.update({'so_ref_id':so_id[0],
                                 'partner_shipping_id':partner_shipping_id, 'partner_invoice_id':partner_invoice_id
                                 })
                    
#                    vals.update({'packing_percent':packing_percent,'packing_percent_amt':packing_amount,'so_ref_id':so_id[0],'partner_shipping_id':partner_shipping_id, 'partner_invoice_id':partner_invoice_id})

            # code to generate invoice, validate and paid it before generating DO ----start 
            if context:
                if 'active_model' in context:
                    if context['active_model'] == 'stock.picking':
                        
                        if vals['type'] == 'in_invoice':
                            po_obj = self.pool.get("purchase.order")
                            stock_picking_obj = self.pool.get("stock.picking")
                            stock_picking_id = stock_picking_obj.search(cr,1,[('name','=',vals['origin'])])
                            if stock_picking_id:
                                stock_picking_brow = stock_picking_obj.browse(cr,1,stock_picking_id[0])
                                po_ref = stock_picking_brow.origin
                                po_id = po_obj.search(cr,1,[('name','=',po_ref)])
                                if po_id:
                                    po_brow = po_obj.browse(cr,1,po_id[0])
                                    #packing_percent = po_brow.packing_percent
                                    #packing_amount = po_brow.packing_amount
                                    
                                    if po_brow.taxes_id:
                                        tax_ids = po_brow.taxes_id.ids
                                        taxes_id = [(6,0,tax_ids)]
                                        vals.update({'taxes_id':taxes_id})

                                    
                                    vals.update({'po_ref_id':po_id[0],'sp_ref_id':stock_picking_id[0]})
                                

                                    
#                                    vals.update({'packing_percent':packing_percent,'packing_percent_amt':packing_amount,'po_ref_id':po_id[0],'sp_ref_id':stock_picking_id[0]})
                                
                                

                        if vals['type'] == 'out_invoice':
                            so_obj = self.pool.get("sale.order")
                            stock_picking_obj = self.pool.get("stock.picking")
                            stock_picking_id = stock_picking_obj.search(cr,1,[('name','=',vals['origin'])])
                            if stock_picking_id:
                                stock_picking_brow = stock_picking_obj.browse(cr,1,stock_picking_id[0])
                                so_ref = stock_picking_brow.origin
                                so_id = so_obj.search(cr,1,[('name','=',so_ref)])
                                if so_id:
                                    so_brow = so_obj.browse(cr,1,so_id[0])
                                    #packing_percent = so_brow.packing_percent
                                    #packing_amount = so_brow.packing_amount
                                    
                                    if so_brow.partner_invoice_id:
                                        partner_invoice_id = so_brow.partner_invoice_id.id
                                    if so_brow.partner_shipping_id:
                                        partner_shipping_id = so_brow.partner_shipping_id.id
                                    
                                    if so_brow.taxes_id:
                                        tax_ids = so_brow.taxes_id.ids
                                        taxes_id = [(6,0,tax_ids)]
                                        vals.update({'taxes_id':taxes_id})
                                    
                                    
                                    vals.update({'so_ref_id':so_id[0],'sp_ref_id':stock_picking_id[0],
                                                 'partner_shipping_id':partner_shipping_id, 'partner_invoice_id':partner_invoice_id})
                                    
                                    
 #                                   vals.update({'packing_percent':packing_percent,'packing_percent_amt':packing_amount,'so_ref_id':so_id[0],'sp_ref_id':stock_picking_id[0],'partner_shipping_id':partner_shipping_id, 'partner_invoice_id':partner_invoice_id})
                            
        res = super(psit_account_invoice,self).create(cr, uid, vals, context)  
        return res



    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False,
        payment_term=False, partner_bank_id=False, company_id=False):
        account_id = False
        payment_term_id = False
        fiscal_position = False
        bank_id = False
        
        partner_invoice_id = False
        partner_shipping_id = False
        

        if partner_id:
            p = self.env['res.partner'].browse(partner_id)
            addr = p.address_get(['delivery', 'invoice', 'contact'])
            
            partner_invoice_id = addr['invoice']
            partner_shipping_id = addr['delivery']
            
            rec_account = p.property_account_receivable
            pay_account = p.property_account_payable
            if company_id:
                if p.property_account_receivable.company_id and \
                        p.property_account_receivable.company_id.id != company_id and \
                        p.property_account_payable.company_id and \
                        p.property_account_payable.company_id.id != company_id:
                    prop = self.env['ir.property']
                    rec_dom = [('name', '=', 'property_account_receivable'), ('company_id', '=', company_id)]
                    pay_dom = [('name', '=', 'property_account_payable'), ('company_id', '=', company_id)]
                    res_dom = [('res_id', '=', 'res.partner,%s' % partner_id)]
                    rec_prop = prop.search(rec_dom + res_dom) or prop.search(rec_dom)
                    pay_prop = prop.search(pay_dom + res_dom) or prop.search(pay_dom)
                    rec_account = rec_prop.get_by_record(rec_prop)
                    pay_account = pay_prop.get_by_record(pay_prop)
                    if not rec_account and not pay_account:
                        action = self.env.ref('account.action_account_config')
                        msg = _('Cannot find a chart of accounts for this company, You should configure it. \nPlease go to Account Configuration.')
                        raise RedirectWarning(msg, action.id, _('Go to the configuration panel'))

            if type in ('out_invoice', 'out_refund'):
                account_id = rec_account.id
                payment_term_id = p.property_payment_term.id
            else:
                account_id = pay_account.id
                payment_term_id = p.property_supplier_payment_term.id
            fiscal_position = p.property_account_position.id
            bank_id = p.bank_ids and p.bank_ids[0].id or False

        result = {'value': {
            'account_id': account_id,
            'payment_term': payment_term_id,
            'fiscal_position': fiscal_position,
            
            'partner_invoice_id' : partner_invoice_id,
            'partner_shipping_id' : partner_shipping_id,
        
            
        }}

        if type in ('in_invoice', 'in_refund'):
            result['value']['partner_bank_id'] = bank_id

        if payment_term != payment_term_id:
            if payment_term_id:
                to_update = self.onchange_payment_term_date_invoice(payment_term_id, date_invoice)
                result['value'].update(to_update.get('value', {}))
            else:
                result['value']['date_due'] = False

        if partner_bank_id != bank_id:
            to_update = self.onchange_partner_bank(bank_id)
            result['value'].update(to_update.get('value', {}))

        return result



psit_account_invoice()
    


class psit_account_invoice_lines(models.Model): 
    
    _inherit = 'account.invoice.line'

    @api.one
    @api.depends('price_unit','invoice_line_tax_id', 'quantity','product_id')
    def _compute_gst(self):
	
	for tax in self.invoice_line_tax_id:
		name_str = tax.name
		if 'CGST' in name_str:
			self.cgst = (self.price_unit * self.quantity) * tax.amount
			self.cgst_rate = int(tax.amount * 100)
		elif 'SGST' in name_str:
			self.sgst = (self.price_unit * self.quantity) * tax.amount
			self.sgst_rate = int(tax.amount * 100)
		elif 'IGST' in name_str:
			self.igst = (self.price_unit * self.quantity) * tax.amount
			self.igst_rate = int(tax.amount * 100)
                else:
                    self.other_tax = (self.price_unit*self.quantity)*tax.amount
                    self.other_tax_rate=int(tax.amount *100)



    
#    def _get_packing_line(self,packing,po_line):
#        self.env.cr.execute('''UPDATE account_invoice_line  SET   price_unit= %s where id = %s''', (packing, self.id,))
        
        


    @api.multi
    def product_id_change_1(self, product, uom_id, parent_taxes,  qty=0, name='', type='out_invoice',
            partner_id=False, fposition_id=False, price_unit=False, currency_id=False,
            company_id=None):
        context = self._context
        company_id = company_id if company_id is not None else context.get('company_id', False)
        self = self.with_context(company_id=company_id, force_company=company_id)

        if not partner_id:
            raise except_orm(_('No Partner Defined!'), _("You must first select a partner!"))
        if not product:
            if type in ('in_invoice', 'in_refund'):
                return {'value': {}, 'domain': {'uos_id': []}}
            else:
                return {'value': {'price_unit': 0.0}, 'domain': {'uos_id': []}}

        values = {}

        part = self.env['res.partner'].browse(partner_id)
        fpos = self.env['account.fiscal.position'].browse(fposition_id)

        if part.lang:
            self = self.with_context(lang=part.lang)
        product = self.env['product.product'].browse(product)

        values['name'] = product.partner_ref
        if type in ('out_invoice', 'out_refund'):
            account = product.property_account_income or product.categ_id.property_account_income_categ
        else:
            account = product.property_account_expense or product.categ_id.property_account_expense_categ
        account = fpos.map_account(account)
        if account:
            values['account_id'] = account.id

        if type in ('out_invoice', 'out_refund'):
            taxes = product.taxes_id or account.tax_ids
            if product.description_sale:
                values['name'] += '\n' + product.description_sale
        else:
            taxes = product.supplier_taxes_id or account.tax_ids
            if product.description_purchase:
                values['name'] += '\n' + product.description_purchase

	values['product_hsn_code'] = product.product_tmpl_id.product_hsn_code
	'''
        account_tax = self.env['account.tax']
        if parent_taxes:
            taxes = account_tax.browse(parent_taxes[0][2])
#             so_taxes = account_tax.browse(cr,1,parent_taxes)

# 
#             if uid == SUPERUSER_ID and partner.company_id:
#                 taxes = so_taxes.filtered(lambda r: r.company_id == partner.company_id)
#             else:
#                 taxes = so_taxes

            taxes = fpos.map_tax(taxes)
            values['invoice_line_tax_id'] = taxes.ids
	
        if type in ('in_invoice', 'in_refund'):
            values['price_unit'] = price_unit or product.standard_price
        else:
            values['price_unit'] = product.lst_price
	'''
	
        fp_taxes = fpos.map_tax(taxes)
        values['invoice_line_tax_id'] = fp_taxes.ids

        if type in ('in_invoice', 'in_refund'):
            if price_unit and price_unit != product.standard_price:
                values['price_unit'] = price_unit
            else:
                values['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.standard_price, taxes, fp_taxes.ids)
        else:
            values['price_unit'] = self.env['account.tax']._fix_tax_included_price(product.lst_price, taxes, fp_taxes.ids)


        values['uos_id'] = product.uom_id.id
        if uom_id:
            uom = self.env['product.uom'].browse(uom_id)
            if product.uom_id.category_id.id == uom.category_id.id:
                values['uos_id'] = uom_id

        domain = {'uos_id': [('category_id', '=', product.uom_id.category_id.id)]}

        company = self.env['res.company'].browse(company_id)
        currency = self.env['res.currency'].browse(currency_id)

        if company and currency:
            if company.currency_id != currency:
                if type in ('in_invoice', 'in_refund'):
                    values['price_unit'] = product.standard_price
                values['price_unit'] = values['price_unit'] * currency.rate

            if values['uos_id'] and values['uos_id'] != product.uom_id.id:
                values['price_unit'] = self.env['product.uom']._compute_price(
                    product.uom_id.id, values['price_unit'], values['uos_id'])

        return {'value': values, 'domain': domain}

    @api.multi
    def uos_id_change(self, product, uom, qty=0, name='', type='out_invoice', partner_id=False,
            fposition_id=False, price_unit=False, currency_id=False, company_id=None):
        context = self._context
        company_id = company_id if company_id != None else context.get('company_id', False)
        self = self.with_context(company_id=company_id)

        result = self.product_id_change_1(
            product, uom, False , qty, name, type, partner_id, fposition_id, price_unit,
            currency_id, company_id=company_id,
        )
        warning = {}
        if not uom:
            result['value']['price_unit'] = 0.0
        if product and uom:
            prod = self.env['product.product'].browse(product)
            prod_uom = self.env['product.uom'].browse(uom)
            if prod.uom_id.category_id != prod_uom.category_id:
                warning = {
                    'title': _('Warning!'),
                    'message': _('The selected unit of measure is not compatible with the unit of measure of the product.'),
                }
                result['value']['uos_id'] = prod.uom_id.id
        if warning:
            result['warning'] = warning
        return result
    
    

    @api.multi
    def onchange_account_id(self, product_id, partner_id, inv_type, fposition_id, account_id):
        if not account_id:
            return {}
        unique_tax_ids = []
        account = self.env['account.account'].browse(account_id)
        if not product_id:
            fpos = self.env['account.fiscal.position'].browse(fposition_id)
            unique_tax_ids = fpos.map_tax(account.tax_ids).ids
        else:
            product_change_result = self.product_id_change_1(product_id, False, False, type=inv_type,
                partner_id=partner_id, fposition_id=fposition_id, company_id=account.company_id.id)
            if 'invoice_line_tax_id' in product_change_result.get('value', {}):
                unique_tax_ids = product_change_result['value']['invoice_line_tax_id']
        return {'value': {'invoice_line_tax_id': unique_tax_ids}}


    product_hsn_code = fields.Char('HSN/SAC Code')
    cgst_rate = fields.Float(string='cGST rate', digits= dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_gst')
    sgst_rate = fields.Float(string='sGST rate', digits= dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_gst')
    igst_rate = fields.Float(string='iGST rate', digits= dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_gst')
    cgst = fields.Float(string='CGST', digits= dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_gst')
    sgst = fields.Float(string='SGST', digits= dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_gst')
    igst = fields.Float(string='IGST', digits= dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_gst')
    other_tax=fields.Float(string='Other Tax', digits= dp.get_precision('Account'),
        store=True, readonly=True, compute='_compute_gst')
    
class account_tax(osv.osv):
    _inherit = 'account.tax'
    
    def _fix_tax_included_price(self, cr, uid, price, prod_taxes, line_taxes):
        """Subtract tax amount from price when corresponding "price included" taxes do not apply"""
        incl_tax = [tax for tax in prod_taxes if tax.id not in line_taxes and tax.price_include]
        if incl_tax:
            return self._unit_compute_inv(cr, uid, incl_tax, price)[0]['price_unit']
        return price
