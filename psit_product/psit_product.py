# -*- encoding: utf-8 -*-

##############################################################################
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import pdb
#----------------------------------------------------

class psit_product_product(osv.osv): 
    _inherit = 'product.product'
    
    _columns={
        'product_hsn_code': fields.char('HSN/SAC Code'),
        
        }
psit_product_product()

class psit_product_template(osv.osv): 
    _inherit = 'product.template'
    
    _columns={
        'product_hsn_code' : fields.char('HSN/SAC Code'),
              }

class psit_account_invoice_1(osv.osv): 
    _inherit = 'account.invoice'
    
    _columns={
        'vehicle_num':fields.char("Vehicle No."), 
        'electronic_reference_num':fields.char("Electronic Reference Number"),
        'transportation_mode' : fields.char("Transportation Mode"),                       
        'date_of_supply' : fields.date("Date of Supply"),
        'seq_num':fields.char("Seq Num"),
        'partner_shipping_id': fields.many2one('res.partner', 'Delivery Address', readonly=False, required=False, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Delivery address for current Invoice order."),
        'taxes_id': fields.many2many('account.tax', 'invoice_order_tax_rel', 'ord_id', 'tax_id', 'Taxes'),
        }
    
    def invoice_validate(self, cr, uid, ids, context=None):
	
        if not context:
            context={}
	invoice = self.browse(cr, uid, ids, context=None)
        if invoice:
		for line in invoice.invoice_line:
			product_hsn_code = line.product_id.product_tmpl_id.product_hsn_code
			if product_hsn_code == False:
				warn_msg = _(' %s does not have any HSN/SAC Code.') %(line.product_id.product_tmpl_id.name)

				#update of warning messages
				if warn_msg:
				    warning = {
					       'title': _('Configuration Error!'),
					       'message' : warn_msg
					    }
        res = super(psit_account_invoice_1,self).invoice_validate(cr, uid, ids, context = context) 
        return res
    
    def create(self,cr,uid,vals,context=None):
	res = super(psit_account_invoice_1,self).create(cr, uid, vals, context)
	return res

psit_account_invoice_1()


class psit_company(osv.osv): 
    _inherit = 'res.company'
    _columns={
               #'cin_no' :  fields.char('CIN',size=256),
               'cin_no' :  fields.char('CIN',size=256),
               
              }
    
    
psit_company()

class sale_order_line(osv.osv): 
    
    _inherit = 'sale.order.line'
    _columns={
        'product_hsn_code' :fields.char('HSN/SAC Code'),       
        }
    
sale_order_line()


class sale_order(osv.osv): 
    
    _inherit = 'sale.order'
    _columns={
        'taxes_id': fields.many2many('account.tax', 'invoice_order_tax_rel', 'ord_id', 'tax_id', 'Taxes'),     
        }
    
sale_order()


        