# -*- encoding: utf-8 -*-

##############################################################################
import time
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare
import pdb
from openerp import netsvc

#To create new object job work order
class job_work_order(osv.osv):

    _name = "job.work.order"

    def create(self, cr, uid, vals, context=None):

        if 'date' in vals:
		date = vals['date']
		if date:
			year = int(date[:4])
			month = int(date[5:7])
			#pdb.set_trace() 
			seq = self.pool.get('ir.sequence').get(cr, uid, 'job.work.order') or '/'
			#today=date.today()
			#months=today.month
			if month<=3:
				start_year = year - 1
			 	next_year = year
			else:
				start_year = year
			 	next_year = year + 1
			n_year = str(next_year)
			c_next_year = int(n_year[2:4])				 
			vals['name'] = 'JO/' + str(start_year) +'-' + str(c_next_year)+ '/' + seq
        return super(job_work_order, self).create(cr, uid, vals, context=context)
        
    def button_confirm(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'work_order'})
        return True
        

    def button_dummy(self, cr, uid, ids, context=None):
        return True
        
                
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj=self.pool.get('res.currency')
        for order in self.browse(cr, uid, ids, context=context):
            #pdb.set_trace()
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            for line in order.line:
               val1 += line.tot
               for c in self.pool.get('account.tax').compute_all(cr, uid, line.taxes_id, line.unit_price, line.quantity, line.name, order.supplier)['taxes']:
                    val += c.get('amount', 0.0)
            res[order.id]['amount_tax']= round(val)
            res[order.id]['amount_untaxed']= round(val1)
            res[order.id]['amount_total']=res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res

   
    _columns = {
            'name': fields.char('Job Work Order',size=100),
            'date':fields.date('Date'),
            'order':fields.many2one('mrp.production','Manufacturing Order'),
            'supplier':fields.many2one('res.partner','Supplier'),
            'sup_ref':fields.char('Supplier Reference',size=100),
            'pricelist_id':fields.many2one('product.pricelist','Price List'),
            'amount_untaxed': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Untaxed Amount', multi="sums"),
            'amount_tax': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Taxes', multi="sums"),
            'amount_total': fields.function(_amount_all, digits_compute= dp.get_precision('Account'), string='Total', multi="sums"),
            'line':fields.one2many('job.work.order.line','line_id','Work order lines'),
            'state':fields.selection([('new', 'Open'),('work_order','Closed')],'State'),
            'product_id': fields.many2one('product.product', 'Product'),

           }
           
    _defaults = {
	     'state':'new',
	   }
           

job_work_order()

class job_work_order_line(osv.osv):

    _name = "job.work.order.line"
    
    def onchange_product_change(self,cr,uid,ids,product,context=None):
        v = {}
        price= 0.0
        if product:
                 price = self.pool.get('product.product').browse(cr,uid,product).list_price
        v['unit_price'] = price
        return {'value': v}  
        
    def _tot_total(self, cr, uid, ids, field_names, args, context=None):
    	res = {}
	for line in self.browse(cr, uid, ids, context=context):
           
            res[line.id] = line.unit_price * line.quantity
        return res        

   
    _columns = {
            'name': fields.many2one('product.product','Product'),
            'description':fields.char('Description'),
            'quantity':fields.float('Quantity'),
            'taxes_id': fields.many2many('account.tax', 'job_order_taxe', 'ord_id', 'tax_id', 'Taxes'),
            'unit_price':fields.float('Unit Price'),
            'tot':fields.function(_tot_total,'Total'),
            'line_id':fields.many2one('job.work.order'),
           }
           

job_work_order_line()


class job_work(osv.osv):

    _inherit = "mrp.production.workcenter.line"

    def modify_production_order_state(self, cr, uid, ids, action):
        """ Modifies production order state if work order state is changed.
        @param action: Action to perform.
        @return: Nothing
        """
        wf_service = netsvc.LocalService("workflow")
        prod_obj_pool = self.pool.get('mrp.production')
        oper_obj = self.browse(cr, uid, ids)[0]
        prod_obj = oper_obj.production_id
	#pdb.set_trace()
        if action == 'start':
               if prod_obj.state =='confirmed':
                   raise osv.except_osv(_('Error!'),_('R.M awaiting availability. Check Delivery order!'))
		   #prod_obj_pool.force_production(cr, uid, [prod_obj.id])
                   #wf_service.trg_validate(uid, 'mrp.production', prod_obj.id, 'button_produce', cr)
               elif prod_obj.state =='ready':
                   wf_service.trg_validate(uid, 'mrp.production', prod_obj.id, 'button_produce', cr)
               elif prod_obj.state =='in_production':
                   return
               else:
                   raise osv.except_osv(_('Error!'),_('Manufacturing order cannot be started in state "%s"!') % (prod_obj.state,))
        else:
            oper_ids = self.search(cr,uid,[('production_id','=',prod_obj.id)])
            obj = self.browse(cr,uid,oper_ids)
            flag = True
            for line in obj:
                if line.state != 'done':
                     flag = False
            if flag:
                for production in prod_obj_pool.browse(cr, uid, [prod_obj.id], context= None):
                    if production.move_lines or production.move_created_ids:
                        prod_obj_pool.action_produce(cr,uid, production.id, production.product_qty, 'consume_produce', context = None)
                wf_service.trg_validate(uid, 'mrp.production', oper_obj.production_id.id, 'button_produce_done', cr)
        return

    def create(self, cr, uid, vals, context=None):
    	
	if 'production_id' in vals:
		production_id = vals['production_id']
		routing = self.pool.get('mrp.production').browse(cr,uid,production_id).routing_id
		product_id = self.pool.get('mrp.production').browse(cr,uid,production_id).product_id.id
		product_quantity = self.pool.get('mrp.production').browse(cr,uid,production_id).product_qty
		jwo_id = self.pool.get('job.work.order').search(cr,uid,[('order', '=', production_id)])	
		if not jwo_id:	
		   if routing:
			location = routing.location_id
			if location:
				usage = location.usage
				if usage == 'supplier' or 'procurement':
					jwo_data = {
					'date': time.strftime("%Y/%m/%d"),
					'order': production_id,
					'supplier': location.partner_id.id or 8,
					'pricelist_id': location.partner_id.property_product_pricelist_purchase.id or 1,
					#'line': [(6, 0, inv_lines)],
					
					}
					jwo_id = self.pool.get('job.work.order').create(cr, uid, jwo_data, context=context)
				        
				        parent_id = self.pool.get('product.product').search(cr,uid,[('parent_id', '=', product_id)])
				        if parent_id:
				        	prod = self.pool.get('product.product').browse(cr,uid,parent_id[0])
						taxes_id = []
						#pdb.set_trace()
						if prod.supplier_taxes_id:
								account_tax = self.pool.get('account.tax')
								account_fiscal_position = self.pool.get('account.fiscal.position')
							        taxes = account_tax.browse(cr, 1, map(lambda x: x.id, prod.supplier_taxes_id))
        							fpos = False
        							taxes_ids = account_fiscal_position.map_tax(cr, 1, fpos, taxes)
						
				        	self.pool.get('job.work.order.line').create(cr, uid, {'name':prod.id,'quantity':product_quantity,'unit_price': prod.standard_price,'line_id':jwo_id, 
'taxes_id':[(6, 0, [x.id for x in prod.supplier_taxes_id])]} ,context=context)	
					
        return super(job_work, self).create(cr, uid, vals, context=context)

job_work()


# To add new fields in  product page
class product_product(osv.osv):

    _inherit = "product.product"

    _columns = {
            'parent_id': fields.many2one('product.product','Parent Product'),
          }
    def copy(self, cr, uid, id, default=None, context=None):
       if not default:
            default = {}
       prod_type = self.pool.get('product.product').browse(cr,uid,id).type
       if prod_type == 'service':
                default.update({
            'type': 'product',
            'parent_id': False,

        })
       return super(product_product, self).copy(cr, uid, id, default, context=context)
           
    _sql_constraints = [
        ('parent_id_uniq', 'unique(parent_id)', 'The Parent Product already exist!')
    ]

product_product()

class product_template(osv.osv):

    _inherit = "product.template"

    _columns = {
            'parent_id': fields.many2one('product.product','Parent Product'),
          }

product_template()
