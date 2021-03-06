
# -*- encoding: utf-8 -*-

##############################################################################
import time
from openerp.osv import osv, fields
from openerp.tools.translate import _
from lxml import etree
from openerp import netsvc
import pdb

#New class to merge delivery orders
class delivery_order_merge_class(osv.osv_memory):
    _name = "delivery.order.merge"
    _description = "Delivery Order Merge"
    _columns = {
       # "target_picking_id": fields.many2one("stock.picking","Target Picking"),
        "picking_ids": fields.many2many("stock.picking.out","wizard_stock_move_picking_merge","merge_id","picking_id"),

    }

# Auto check while user clicks on Merge Delivery order action
    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):
        """
         Changes the view dynamically
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param context: A standard dictionary
         @return: New arch of view.
        """
	
        if context is None:
            context={}
        res = super(delivery_order_merge_class, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar,submenu=False)
        if context.get('active_model','') == 'stock.picking' and len(context['active_ids']) < 2:
            raise osv.except_osv(_('Warning!'),
            _('Please select multiple order to merge in the list view.'))
	partner_id = False
	if 'active_ids' in context:
		delivery_orders = context['active_ids']
		
		part = False
		state = False
		for order in delivery_orders:
			order_brow = self.pool.get('stock.picking').browse(cr,uid,order)
			next_part = order_brow.partner_id.id
			next_state = order_brow.state
			if next_state == 'cancel':
				raise osv.except_osv(_('Warning!'),_("Merging Delivery Order's State Should not be Cancelled"))
			if next_state == 'done':
				raise osv.except_osv(_('Warning!'),_("Merging Delivery Order's State Should not be delivered"))
			if state:
			  if  state != next_state:
				raise osv.except_osv(_('Warning!'),_("Merging Delivery Order's State Should be Same"))
			if part:
			  if part != next_part :
				raise osv.except_osv(_('Warning!'),_("Merging Delivery Order's Partner Should be Same"))
			part = next_part
			state = next_state

        return res

#Merge Button Function
    def merge_orders(self, cr, uid, ids, context=None):
        """
             To merge similar type(same customer and state) of delivery orders.
             @return: delivery order view

        """
	
        order_obj = self.pool.get('stock.picking')
        mod_obj =self.pool.get('ir.model.data')
        if context is None:
            context = {}
        result = mod_obj._get_id(cr, uid, 'stock', 'vpicktree')
        id = mod_obj.read(cr, uid, result, ['res_id'])
	
        allorders = order_obj.do_merge_delivery_order(cr, uid, context.get('active_ids',[]), context)
	
	#view_id = self.pool.get('ir.ui.view').search(cr,uid,[('model','=','stock.picking.out'), ('name','=','stock.picking.out.tree')])
        return True

delivery_order_merge_class()

#Inherit stock picking to handle merge and merge notes
class delivery_order_class(osv.osv):

    _inherit = "stock.picking"


    _columns = {
        'merge_notes': fields.text('Merge Notes'),
		}

    def get_specialhandlers(self):
        return {}

    def is_view(self, browse):
        # _auto=False is used to overload __init__ with a "create or replace view" if you don't need a table
        # so: return TRUE if _auto exists and is False, otherwise return False
        if (browse):
            if (hasattr(browse, "_auto")):
                if (not getattr(browse, "_auto")):
                    return True
        return False

    def do_merge_delivery_order(self, cr, uid, ids, context=None):
        """
        @return: new delivery order id

        """
	#pdb.set_trace()
        picking_pool = self.pool.get("stock.picking")
        fields_pool = self.pool.get("ir.model.fields")
	notes = " "
	origin = ""
	new_date = False
	moves = []

#Created new DO

	target = picking_pool.create(cr, uid,{"date": time.strftime('%Y-%m-%d %H:%M:%S'),"type": 'out',"picking_type_id":2, "move_type":'one'})
        for merge in self.browse(cr, uid, ids):
		target_changes ={}
		merge_state = merge.state
                if (merge.origin):
                    origin += " " + str(merge.origin)

                target_changes['origin'] = origin 
                if (merge.name):
                    notes += " " + str(merge.name)
		    if (merge.origin):
			notes += " From" + str(merge.origin) + ","
		target_changes['merge_notes'] = notes

                # handle changeable values

                # if any one merge has partial delivery, deliver the whole picking as partial (direct)
               # if (merge.move_type == 'direct'):
                #    target_changes['move_type'] = 'direct'
                
                # date_done = MAX(date_done)
		if (merge.date_done):
		  date = merge.date_done
		  if 'date_done' in target_changes:
                    if (target_changes['date_done'] < merge.date_done):
                    	target_changes['date_done'] = merge.date_done
		  else:
			target_changes['date_done'] = merge.date_done
			
                    
                # if any one merge is NOT auto_picking, then the target is not.
                # should never occur, as auto_picking would set it to done instantly, which can't be merged
#		if(merge.stock_journal_id):
#			 target_changes['stock_journal_id'] = merge.stock_journal_id.id
		if(merge.partner_id):
			 target_changes['partner_id'] = merge.partner_id.id
 #               if (not (merge.auto_picking)):
#			 target_changes['auto_picking'] = False

                if merge.move_lines:
			
			move_lines = merge.move_lines
			for line in move_lines:
				product_id = line.product_id.id
				line_picking_search = self.pool.get('stock.move').search(cr, uid, [('picking_id','=', target),('product_id','=',product_id)])
				if line_picking_search:
					line_quantity = line.product_qty
					old_quantity = self.pool.get('stock.move').browse(cr,uid,line_picking_search[0]).product_qty
					new_quantity = line_quantity+old_quantity
					self.pool.get('stock.move').write(cr,uid,line_picking_search[0], {'product_qty': new_quantity})
					self.pool.get('stock.move').write(cr,uid,line.id, {'state': 'draft'})
					#self.pool.get('stock.move').unlink(cr, uid, [line.id])
				else:
				
					self.pool.get('stock.move').write(cr,uid,line.id, {'picking_id': target}) 

       	#	if(merge.state):
	#		 target_changes['state'] = merge.state
                        # handle many2one: simply replace the id 
                fields_search = fields_pool.search(cr, uid, [('relation','=','stock.picking'),('model','<>','stock.picking'),
                                                             '|',('ttype','=','many2one'),('ttype','=','many2many')])
                
                # go through these fields
                for field in fields_pool.browse(cr, uid, fields_search):
                    
                    if field.name in self.get_specialhandlers().keys():
                        # use special handler
                        # use special handler
                        specialhandler_name = self.get_specialhandlers().get(field.name)
                        specialhandler = getattr(self, specialhandler_name)
                        target_changes = specialhandler(cr, uid, field.name, merge, target, target_changes)

                        
                ## update all relations to the old picking to look for the new one
                ## includes stock.move lines merge


                # go through these fields and change things, using field_search from before (many2one | many2many)
                for field in fields_pool.browse(cr, uid, fields_search):


                    if not (field.name in self.get_specialhandlers().keys()):
                        # find the model they're in
                        model_pool = self.pool.get(field.model)

                        # this can happen if you deinstalled modules by deleting their code, so they left something behind in the definition.
                        if (not model_pool):
                            continue

                        # do not handle relations to views
                        if self.is_view(model_pool):
                            continue

		                                
                        # handle many2one: simply replace the id 
                        if (field.ttype == 'many2one'):
                            # find all entries that are old
                            model_search = model_pool.search(cr, uid, [(field.name,'=',merge.id)])
                            # and update them in one go
                            model_pool.write(cr, uid, model_search, {field.name: target})

                        # handle many2many:  
                        if (field.ttype == 'many2many'):
                            # find all entries that are old (don't know how yet, so I'll have to take 'em all
                            model_search = model_pool.search(cr, uid, []) # (field.name,'=',merge.id)
                            # and update them in one go
                            model_pool.write(cr, uid, model_search, {field.name: [(3,merge.id),(4,target)]})

                        
                # updated everything, so now I can get rid of the object- Delete merging DO's
                #picking_pool.unlink(cr, uid, [merge.id])

        picking_pool.write(cr, uid, target, target_changes)
	wf_service = netsvc.LocalService("workflow")
        if target:
		if merge_state == 'auto':
            		picking_pool.write(cr, uid, target, {'state': 'auto'})
		if merge_state == 'confirmed':
            		wf_service.trg_validate(uid, 'stock.picking', target, 'button_confirm', cr)

		if merge_state == 'assigned':
            		wf_service.trg_validate(uid, 'stock.picking', target, 'button_confirm', cr)
			picking_pool.write(cr, uid, target, {'state': 'assigned'})
	    		#res = picking_pool.action_assign(cr, uid, [target])
	    
	return target

delivery_order_class()

