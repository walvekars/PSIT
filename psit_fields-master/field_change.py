# -*- encoding: utf-8 -*-

##############################################################################
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import pdb
#----------------------------------------------------

class account_invoice_class(osv.osv):

    _inherit = "account.invoice"
#To add new field on account invoice page
    _columns = {
        'x_esugam_no': fields.char('e - Way Bill No.', size=100,copy=False),
        'x_customer_po_no': fields.char('Customer PO No' ,required=True,copy=False),
        'x_customer_po_date': fields.date('Customer PO Date', required=True,copy=False),
        'partner_gst_number' : fields.many2one('res.partner', string='GST Number',required=True, readonly=True,
        track_visibility='always',copy=False),
        'rounded_total': fields.float(string='Total', readonly=True),
        'round_off': fields.float(string='Round Off', digits=dp.get_precision('Account'), store=True, readonly=False)
           }

    _defaults = {
           }

#Function to calculate and update amount value for old invoice records
    def compute_button_old_data(self, cr, uid, ids, *args):
        tax_obj = self.pool.get('account.tax')
        invoice_obj = self.pool.get('account.invoice')
        cur_obj = self.pool.get('res.currency')
	all_invoice_lines = self.pool.get('account.invoice.line').search(cr,uid,[])
        for line in self.pool.get('account.invoice.line').browse(cr, uid, all_invoice_lines):
		discount = line.discount 
		quantity = line.quantity
		unit_price = line.price_unit
		price = unit_price  * (1-(discount or 0.0)/100.0)
		taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
		total_price = taxes['total']
		self.pool.get('account.invoice.line').write(cr,uid,[line.id],{'invoice_amount':total_price})
	
        return True


account_invoice_class()

class account_invoice_line_class(osv.osv):

    _inherit = "account.invoice.line"

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        """
        -Process-added to get value from invoice_amount field
        """
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
	    #directly putting the value from new field
	    
	    line_amount = line.invoice_amount
            #price = line.price_unit  * (1-(line.discount or 0.0)/100.0)
            #taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
            #res[line.id] = taxes['total']
	    res[line.id] = line_amount
           # if line.invoice_id:
            #    cur = line.invoice_id.currency_id
             #   res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res


#-----------------------------------------------------
#While creating, the value should from  take the default amount field 
    def create(self, cr, uid, vals, context=None):
        product_obj = self.pool.get('product.product')
        tax_obj = self.pool.get('account.tax')
        invoice_obj = self.pool.get('account.invoice')
        cur_obj = self.pool.get('res.currency')
	#pdb.set_trace()
	if 'quantity' in vals:
		quantity = vals['quantity']
	else:
		quantity = 0.0
	if 'price_unit' in vals:
		unit_price = vals['price_unit']
	else:
		unit_price = 0.0
	product_id = vals['product_id']

	if 'discount' in vals:
		discount = vals['discount']
	else:
		discount = 0.0
	if 'invoice_line_tax_id' in vals:
		tax_id = vals['invoice_line_tax_id']
		if tax_id:
			invoice_line_tax_id = tax_obj.browse(cr,uid,tax_id[0][2])
		else:
			invoice_line_tax_id = []
	else:
		invoice_line_tax_id = []
	if 'invoice_id' in vals:
		invoice_id = vals['invoice_id']
		partner = invoice_obj.browse(cr,uid,invoice_id).partner_id
	else:
		partner = []

	product = product_obj.browse(cr,uid,[product_id])
        price = unit_price  * (1-(discount or 0.0)/100.0)
        taxes = tax_obj.compute_all(cr, 1, invoice_line_tax_id, price, quantity, product=product, partner=[partner])
       	total_price = taxes['total']
	#total_price = quantity * unit_price
	vals.update({'invoice_amount':total_price})
        return super(account_invoice_line_class, self).create(cr, uid, vals, context=context)

# Function to take Priority for Amount field
    def write(self, cr, uid, ids, vals, context=None): 
    
	if 'invoice_amount' not in vals:
	    	if 'price_unit' in vals:
		    unit_price = vals['price_unit']
		    if 'quantity' in vals:
			quantity = vals['quantity']
		    else:
			quantity = self.browse(cr,uid,ids)[0].quantity

		    inv_amount = unit_price * 	quantity
		   
                    vals.update({'invoice_amount':inv_amount})
	if 'invoice_amount' in vals:
		inv_amount = vals['invoice_amount']
		if 'quantity' in vals:
			quantity = vals['quantity']
		else:
			quantity = self.browse(cr,uid,ids)[0].quantity
		unit_price = float(inv_amount)/float(quantity)
		    
                vals.update({'price_unit':unit_price})	
			
	return super(account_invoice_line_class,self).write(cr, uid, ids, vals, context)


#Function to change values whenever user changes the quantity, unit price or Amount
    def onchange_invoice_amount(self, cr, uid, ids, inv_amt, qty):
        result = {}
	unit_price = float(inv_amt)/float(qty)
        result['value'] = {
                'price_unit': unit_price,
		
            }

	#self.write(cr,uid,ids,{'price_unit':unit_price})
        return result


    def onchange_prdt_quantity(self, cr, uid, ids, qty,price_unit):
        result = {}
	invoice_amount = qty * price_unit
        result['value'] = {
                'invoice_amount': invoice_amount,
		
            }

	#self.write(cr,uid,ids,{'invoice_amount': invoice_amount})
        return result


    def onchange_prdt_unit_quantity(self, cr, uid, ids, price_unit,qty):
        result = {}
	invoice_amount = qty * price_unit
        result['value'] = {
                'invoice_amount': invoice_amount,
		
            }

	#self.write(cr,uid,ids,{'invoice_amount': invoice_amount})
        return result


    _columns = {

	'invoice_amount': fields.float('Amount(New)',digits_compute= dp.get_precision('Account')),
        'price_subtotal': fields.function(_amount_line, string='Amount', type="float",
            digits_compute= dp.get_precision('Account'), store=True),
	'price_unit': fields.float('Unit Price',digits_compute= dp.get_precision('Unit Price'), digits="(14, 2)")

    }


account_invoice_line_class()

# To add new fields in product page

class product_product_class(osv.osv):

    _inherit = "product.product"
    _columns = {
        'x_regular_discount': fields.float('Regular Discount'),
        'x_special_discount': fields.float('Special Discount'),
        'x_dealer_discount': fields.float('Dealer Discount'),
        'x_oem_discount': fields.float('OEM Discount'),
	'type_dump': fields.selection([('product', 'Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Product Type Dump'),
           }

    _defaults = {
           }

product_product_class()

class product_template_class(osv.osv):

    _inherit = "product.template"
    _columns = {
        'x_regular_discount': fields.float('Regular Discount'),
        'x_special_discount': fields.float('Special Discount'),
        'x_dealer_discount': fields.float('Dealer Discount'),
        'x_oem_discount': fields.float('OEM Discount'),
        'type_dump': fields.selection([('product', 'Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Product Type Dump'),
        'manufacturer_pname':fields.char('Manufacturer Product Name'),
        'manufacturer_purl':fields.char('Manufacturer Product URL'),
        'manufacturer_pref':fields.char('Manufacturer Product Code'),
        'manufacturer':fields.many2one('res.partner', 'Manufacturer'),
        'reference_number':fields.char("Reference Number",size=256),
           }
product_template_class()

class account_voucher_class(osv.osv):

    _inherit = "account.voucher"

    _columns = {
        'x_instrument': fields.selection([('cheque','Cheque/DD'),('rtgs','RTGS/NEFT'),('others','Others')], required=True),
	
           }
account_voucher_class()

class stock_move(osv.osv):

    _inherit = "stock.move"

    _columns = {
        'job_id': fields.many2one('job.work.order', 'Job Work Order'),
	
           }
    
    def create(self,cr,uid,vals,context=None):
	res = super(stock_move,self).create(cr, uid, vals, context)
	stock_move_id = self.pool.get('stock.move').browse(cr, uid, res)
	if stock_move_id:
	    mrp_name = stock_move_id.name
	    job_id = self.pool.get('job.work.order').search(cr, uid, [('order.name','ilike',mrp_name),('state','=','new')],context=context)
	    if job_id:
	        stock_move_id.update({'job_id':job_id[0]})
	    
	    
	    
	return res



