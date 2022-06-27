# -*- encoding: utf-8 -*-

##############################################################################
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
import pdb
from openerp import SUPERUSER_ID

class mrp_production_class(osv.osv):

    _inherit = "mrp.production"
#To add new field on mrp production 
    _columns = {

	
           }


#Function to change stock move for routing location
    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        production = self.browse(cr, uid, production_id, context=context)
        for produce_product in production.move_created_ids:
            #function to change
	    	routing = production.routing_id
	    	if routing:
		    	routing_loc = routing.location_id 
			if routing_loc.usage != 'internal':
				self.write(cr, uid, [production_id], {'location_dest_id': routing_loc.id})
			#pdb.set_trace()
			#move_created_ids = production.move_created_ids
			#if move_created_ids:
			#	   self.pool.get('stock.move').write(cr, 1, [move_created_ids[0].id], {'location_dest_id': routing_loc.id})
				       
        return super(mrp_production_class,self).action_produce(cr, uid, production_id, production_qty, production_mode, wiz=False, context=None)
        
        
        


#Function to write routing on bom if user selcts new routing on mrp production while confirming
    def action_ready(self, cr, uid, ids, context=None):
        """ Changes the production state to Ready and location id of stock move.
        @return: True
        """

        for production in self.browse(cr, uid, ids, context=context):
            bom_id = production.bom_id.id
            bom_routing_id = production.bom_id.routing_id
            routing_id = production.routing_id
            
            if routing_id:
                if bom_routing_id:
                    if routing_id.id != bom_routing_id.id:
                        self.pool.get('mrp.bom').write(cr, uid, bom_id, {'routing_id': routing_id.id})
                else:
                        self.pool.get('mrp.bom').write(cr, uid, bom_id, {'routing_id': routing_id.id})
           # if routing_id:
	#	routing_loc = routing_id.location_id 
	#	if routing_loc.usage != 'internal':
               		#pdb.set_trace()
	#		self.write(cr, uid, ids, {'location_dest_id': routing_loc.id})
	#		move_created_ids = production.move_created_ids
	#		if move_created_ids:
	#		   self.pool.get('stock.move').write(cr, uid, [move_created_ids[0].id], {'location_dest_id': routing_loc.id})	
        return super(mrp_production_class,self).action_ready(cr, uid, ids, context=context)



    def create(self, cr, uid, vals, context=None):
       
       if 'date_planned' in vals:
       	 print vals['date_planned']
       	 vals['date_planned'] = time.strftime('%Y-%m-%d %H:%M:%S')
       return super(mrp_production_class, self).create(cr, uid, vals, context=context)

mrp_production_class()

class account_invoice_labour_class(osv.osv):

    _inherit = "account.invoice"

    def write(self, cr, uid, ids, vals, context=None):

	if 'state' in vals:
        	if vals.get('state') in ['paid']:
			production_id = self.browse(cr,uid,ids).production_id
			if production_id:
				jbw = self.pool.get('job.work.order').search(cr,1, [('order', '=', production_id.id)])
			        if jbw:
					self.pool.get('job.work.order').write(cr,1,jbw,{'state':'work_order'})
			  		

        return super(account_invoice_labour_class, self).write(cr, uid, ids, vals, context=context)
        
    _columns = {

	'jobwork_invoice': fields.boolean('Labour Invoices'),
	'production_id':fields.many2one('mrp.production'),

    }

    _defaults = {
	'jobwork_invoice': False,
           }


account_invoice_labour_class()


class mrp_procurement_order(osv.osv):

    _inherit = "procurement.order"

    def make_mo(self, cr, uid, ids, context=None):
        """ Make Manufacturing(production) order from procurement
        @return: New created Production Orders procurement wise
        """
        res = {}
        production_obj = self.pool.get('mrp.production')
        procurement_obj = self.pool.get('procurement.order')
        for procurement in procurement_obj.browse(cr, uid, ids, context=context):
            if self.check_bom_exists(cr, uid, [procurement.id], context=context):
                #create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
                vals = self._prepare_mo_vals(cr, uid, procurement, context=context)
                produce_id = production_obj.create(cr, SUPERUSER_ID, vals, context=dict(context, force_company=procurement.company_id.id))
                res[procurement.id] = produce_id
                self.write(cr, uid, [procurement.id], {'production_id': produce_id})
                self.production_order_create_note(cr, uid, procurement, context=context)
                production_obj.action_compute(cr, uid, [produce_id], properties=[x.id for x in procurement.property_ids])
                mrp_id = production_obj.search(cr,uid,[('name','=',procurement.origin)])
                mrp_bom = self.pool.get("mrp.bom")
                    
                if 'bom_id' in vals:
                    bom_id = vals['bom_id']
                    bom_brow = mrp_bom.browse(cr,uid,bom_id)
                    bom_id_copy = mrp_bom.search(cr,uid,[('product_tmpl_id','=',bom_brow.product_tmpl_id.id)])
                    if bom_id_copy:
                                
                        if len(bom_id_copy) == 1 :
                            production_obj.signal_workflow(cr, uid, [produce_id], 'button_confirm')
            else:
                res[procurement.id] = False
                self.message_post(cr, uid, [procurement.id], body=_("No BoM exists for this product!"), context=context)
        return res

mrp_procurement_order()

