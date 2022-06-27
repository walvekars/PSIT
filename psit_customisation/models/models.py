# -*- encoding: utf-8 -*-

##############################################################################
import time
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
#----------------------------------------------------

class accountinvoice(osv.osv):
    _inherit='account.invoice'

    _columns = {
        'amount_cgst': fields.float('Total CGST'),
        'amount_sgst': fields.float('Total SGST'),
        'amount_igst': fields.float('Total IGST'),
        'rounded_total': fields.float('Total Amount'),
	'price_unit': fields.float('Unit Price',digits_compute= dp.get_precision('Unit Price'), digits="(14, 2)")
           }

class saleorder(osv.osv):
    _inherit='sale.order'

    _columns = {
    	'x_customer_po_no' : fields.char('Customer PO No'),
    	'x_customer_po_date': fields.date('Customer PO Date')
		}

class purchaseorder(osv.osv):
    _inherit='purchase.order'


class producttemplate(osv.osv):
    _inherit='product.template'


class productproduct(osv.osv):
    _inherit='product.product'


class productproduct(osv.osv):
    _inherit='product.category'


class saleorderLines(osv.osv):
    _inherit='sale.order.line'

    _columns = {
    	'name_order' : fields.char(related='order_id.name', string='SO No.', store=True),
    	'default_code' : fields.char(related='product_id.default_code', store=True, string='Item'),
    	'date_order' : fields.datetime(related='order_id.date_order', string='SO Date', store=True),
    	'x_customer_po_no' : fields.char(related='order_id.x_customer_po_no', string='PO No')
          }


class AccountInvoiceLine(osv.osv):
    _inherit = 'account.invoice.line'

    _columns = {
	'invoice_number': fields.char(related='invoice_id.number', string='Invoice No.',store=True),
        'invoice_date': fields.date(related='invoice_id.date_invoice', string='Invoice Date',store=True),
    	'partner_gst_number' : fields.char(string='GST Number', store=True),
	'state': fields.selection(selection=[
            ('draft', 'Draft'),('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled')], related='invoice_id.state', store=True)
	}


class purchaseOrderLines(osv.osv):
    _inherit='purchase.order.line'

    _columns = {
    	'name_order' : fields.char(related='order_id.name', string='PO No.', store=True),
    	'default_code' : fields.char(related='product_id.default_code', store=True, string='Product'),
    	'date_order' : fields.datetime(related='order_id.date_order', string='PO Date', store=True),
          }


class ResPartner(osv.osv):
    _inherit='res.partner'

    _columns = {
    	'name' : fields.char('Contact', store=True),
    	'mobile' : fields.char('Mobile', store=True),
          }

class StockMove(osv.osv):
    _inherit='stock.move'


class StockPicking(osv.osv):
    _inherit='stock.picking'


class StockInventory(osv.osv):
    _inherit='stock.inventory'

    _columns = {
    	'description' : fields.text('Description', store=True),
          }


class AccountVoucher(osv.osv):
    _inherit='account.voucher'

    _columns = {
        'x_instrument': fields.selection([('cheque','Cheque/DD'),('rtgs','RTGS/NEFT'),('others','Others')], required=True),
	
           }







    
