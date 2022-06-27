#OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today Julius Network Solutions SARL <contact@julius.fr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import time
from openerp.osv import fields,osv, orm
from openerp.tools.translate import _
from openerp.tools import float_compare
from openerp import netsvc, SUPERUSER_ID
from openerp.tools.float_utils import float_round
from openerp.tools import float_compare, float_is_zero
import openerp.addons.decimal_precision as dp
import pdb


class stock_move(osv.osv):
    _inherit = "stock.move"


#To make the Source(Incoming shipment) and destination location(delivery order) as blank for Incoming shipment and for delivery order


    def _default_location_destination_inherit(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_picking_type_id', False):
            pick_type = self.pool.get('stock.picking.type').browse(cr, uid, context['default_picking_type_id'], context=context)
           # pdb.set_trace()
            if pick_type.id != 2:
                return pick_type.default_location_dest_id and pick_type.default_location_dest_id.id or False
        return False

    def _default_location_source_inherit(self, cr, uid, context=None):
        context = context or {}
        if context.get('default_picking_type_id', False):
            pick_type = self.pool.get('stock.picking.type').browse(cr, uid, context['default_picking_type_id'], context=context)
            if pick_type.id != 1:
                return pick_type.default_location_src_id and pick_type.default_location_src_id.id or False
        return False

    def _get_domain_locations(self, cr, uid, ids,source_location, context=None):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, force_company, compute_child
        '''
        context = context or {}

        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')
        location_ids = [source_location]


        operator = context.get('compute_child', True) and 'child_of' or 'in'
        domain = context.get('force_company', False) and ['&', ('company_id', '=', context['force_company'])] or []
        locations = location_obj.browse(cr, uid, location_ids, context=context)
        if operator == "child_of" and locations and locations[0].parent_left != 0:
            loc_domain = []
            dest_loc_domain = []
            for loc in locations:
                if loc_domain:
                    loc_domain = ['|'] + loc_domain  + ['&', ('location_id.parent_left', '>=', loc.parent_left), ('location_id.parent_left', '<', loc.parent_right)]
                    dest_loc_domain = ['|'] + dest_loc_domain + ['&', ('location_dest_id.parent_left', '>=', loc.parent_left), ('location_dest_id.parent_left', '<', loc.parent_right)]
                else:
                    loc_domain += ['&', ('location_id.parent_left', '>=', loc.parent_left), ('location_id.parent_left', '<', loc.parent_right)]
                    dest_loc_domain += ['&', ('location_dest_id.parent_left', '>=', loc.parent_left), ('location_dest_id.parent_left', '<', loc.parent_right)]

            return (
                domain + loc_domain,
                domain + ['&'] + dest_loc_domain + ['!'] + loc_domain,
                domain + ['&'] + loc_domain + ['!'] + dest_loc_domain
            )
        else:
            return (
                domain + [('location_id', operator, location_ids)],
                domain + ['&', ('location_dest_id', operator, location_ids), '!', ('location_id', operator, location_ids)],
                domain + ['&', ('location_id', operator, location_ids), '!', ('location_dest_id', operator, location_ids)]
            )



    def _compute_component_quantity_available(self, cr, uid, ids, field_name, arg=False, context=None):
        context = context or {}
        res = {}
        for move in self.browse(cr, uid, ids, context=context):
            source_location = move.location_id.id
            domain_products = [('product_id', 'in', [move.product_id.id])]
            domain_quant, domain_move_in, domain_move_out = [], [], []
            domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations(cr, uid, domain_products,source_location , context=context)

            domain_quant += domain_products
            domain_quant += domain_quant_loc
            quants = self.pool.get('stock.quant').read_group(cr, uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=context)
            quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))

            id = move.product_id.id
            qty_available = float_round(quants.get(id, 0.0), precision_rounding=move.product_id.uom_id.rounding)

            print "SSSSSSSSSSSs" , move.id ,qty_available 
            res[move.id]  = qty_available
        return res




    _columns = {
        'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True, auto_join=True,
                                       states={'done': [('readonly', True)]}, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', required=True, states={'done': [('readonly', True)]}, select=True,
                                            auto_join=True, help="Location where the system will stock the finished products."),
            }


    _defaults = {
        'location_id': _default_location_source_inherit,
        'location_dest_id': _default_location_destination_inherit,

                }


stock_move()

class mrp_production(osv.osv):
    _inherit = "mrp.production"
    
    def _get_produced_qty(self, cr, uid, production, context=None):
        ''' returns the produced quantity of product 'production.product_id' for the given production, in the product UoM
        '''
        produced_qty = 0
        for produced_product in production.move_created_ids2:
            if (produced_product.product_id.id != production.product_id.id):
                continue
            produced_qty += produced_product.product_qty
        return produced_qty


    def action_assign(self, cr, uid, ids, context=None):
        """
        Checks the availability on the consume lines of the production order
        """
        from openerp import workflow
        move_obj = self.pool.get("stock.move")
        for production in self.browse(cr, uid, ids, context=context):
	 #pdb.set_trace()
         if production.state == 'confirmed':
            quantity_ready = production.product_qty_ready
            quantity_produced = production.qty_produced
            quantity_to_produce = production.qty_to_produce
            quantity_remain = quantity_produced - quantity_to_produce
            if quantity_ready > 0.0 and quantity_ready != quantity_remain:
                self.write(cr, uid, [production.id], {'partial_ready': True})
            else:
                self.write(cr, uid, [production.id], {'partial_ready': False})    

            move_obj.action_assign(cr, uid, [x.id for x in production.move_lines], context=context)
            if self.pool.get('mrp.production').test_ready(cr, uid, [production.id]):
                workflow.trg_validate(uid, 'mrp.production', production.id, 'moves_ready', cr)


    def _get_available_quantity_ready(self, cr, uid, ids,field_names=None, arg=False, context=None):
        if context is None: context = {}
        res = {}
        move_obj = self.pool.get('stock.move')
        for prod in self.browse(cr, uid, ids, context=context):
            res[prod.id] = 0
           # res[prod.id] = {
            #    'product_qty_ready': 0,
              #  'partial_ready': False,   }
            compo_list = {}
            if prod.state in ('confirmed'):
                available = 0
                partial_ready = False
                start = True
                for component in prod.bom_id.bom_line_ids:
                    product_id = component.product_id.id
                    compo_list.setdefault(product_id, 0)
                    compo_list[product_id] += component.product_qty


                for component in prod.bom_id.bom_line_ids:
                    assigned = True
                    available_quantity = 0.0
                    waiting = False
                    prod_type = component.product_id.type
                    if prod_type != 'product' :
                        continue
                    for move in prod.move_lines:
                       if move.product_id.id == component.product_id.id :

                    #if move.state = 'waiting':
                        #assigned = False
                        #for m in prod.move_lines:
                          #  if m.product_id.id == move.product_id.id:
                          if move.state in ('assigned','confirmed'):

                                    #total_product_qty += move.product_uom_qty

                                    available_quantity += move.reserved_availability

                    print "AAAAAAAAVVVVVVVV", available_quantity,component.product_id.name           
                    if available_quantity <= 0 : 
                        available = 0
                        break           
                    component_qty = compo_list.get(component.product_id.id)
                    if component_qty == 0:
                        component_qty = 1
                    quantity = (available_quantity - (available_quantity % component_qty)) / component_qty
                    

                    if not start:
                        available = min(quantity, available)
                    else:
                        start = False
                        available = quantity

                print "AAAAAviaaaableeee" , available               
                if available > prod.product_qty:
                   available = prod.product_qty

                res[prod.id]= available


        return res

    def _get_available_quantity_ready_old(self, cr, uid, ids,field_names=None, arg=False, context=None):
        if context is None: context = {}
        res = {}
        move_obj = self.pool.get('stock.move')
        for prod in self.browse(cr, uid, ids, context=context):
            res[prod.id] = 0
           # res[prod.id] = {
            #    'product_qty_ready': 0,
              #  'partial_ready': False,   }
            compo_list = {}
            if prod.state in ('confirmed'):
                available = 0
                partial_ready = False
                start = True
                for component in prod.bom_id.bom_line_ids:
                    product_id = component.product_id.id
                    compo_list.setdefault(product_id, 0)
                    compo_list[product_id] += component.product_qty
                for move in prod.move_lines:
                    assigned = True
                    total_product_qty = 0.0
                    waiting = False
                    if move.state == 'waiting':
                        assigned = False
                        for m in prod.move_lines:
                            if m.product_id.id == move.product_id.id:
                                if m.state in ('assigned','confirmed'):
                                    assigned = True
                                    waiting = True
                                    total_product_qty += m.product_uom_qty

                    available_quantity = move.reserved_availability
                                    
                    if assigned == False and available_quantity <= 0 : 
                        available = 0
                        break           

                    if waiting == True :
                            continue
                    prod_type = move.product_id.type
                    if prod_type != 'product' :
                        continue
                    #pdb.set_trace()
                    if available_quantity <= 0 and waiting == False:
                        available = 0
                        break
                    component_qty = compo_list.get(move.product_id.id)
                    if component_qty == 0:
                        component_qty = 1
                    quantity = (available_quantity - (available_quantity % component_qty)) / component_qty
                    

                    if not start:
                        available = min(quantity, available)
                    else:
                        start = False
                        available = quantity

                print "AAAAAviaaaableeee" , available               
                if available > prod.product_qty:
                   available = prod.product_qty
                   #partial_ready = False
                   #if prod.partial_ready == True:
                    #    self.write(cr, uid, [prod.id], {'partial_ready': False})

                #elif available >= 1:
                    #partial_ready = True
                 ##   if prod.partial_ready == False:
                  #      self.write(cr, uid, [prod.id], {'partial_ready': True})
                #else:
                    #partial_ready = False
                   # if prod.partial_ready == True:
                    #    self.write(cr, uid, [prod.id], {'partial_ready': False})
                #res[prod.id] = {
                #'product_qty_ready': available,
               # 'partial_ready': partial_ready,}
                res[prod.id]= available


        return res


    def action_produce(self, cr, uid, production_id, production_qty, production_mode, wiz=False, context=None):
        """ To produce final product based on production mode (consume/consume&produce).
        If Production mode is consume, all stock move lines of raw materials will be done/consumed.
        If Production mode is consume & produce, all stock move lines of raw materials will be done/consumed
        and stock move lines of final product will be also done/produced.
        @param production_id: the ID of mrp.production object
        @param production_qty: specify qty to produce in the uom of the production order
        @param production_mode: specify production mode (consume/consume&produce).
        @param wiz: the mrp produce product wizard, which will tell the amount of consumed products needed
        @return: True
        """

        stock_mov_obj = self.pool.get('stock.move')
        uom_obj = self.pool.get("product.uom")
        production = self.browse(cr, uid, production_id, context=context)

#To check the partial ready quantity

        if production.state == 'confirmed':
            quantity_ready = production.product_qty_ready
            if production_qty > quantity_ready:
              raise orm.except_orm(_("Warning !"),
                                 _("You can't Produce more than %s quantity.") % quantity_ready)

        production_qty_uom = uom_obj._compute_qty(cr, uid, production.product_uom.id, production_qty, production.product_id.uom_id.id)
        precision = self.pool['decimal.precision'].precision_get(cr, uid, 'Product Unit of Measure')
        main_production_move = False

        if production_mode in ['consume', 'consume_produce']:
            if wiz:
                consume_lines = []
                for cons in wiz.consume_lines:
                    consume_lines.append({'product_id': cons.product_id.id, 'lot_id': cons.lot_id.id, 'product_qty': cons.product_qty})
            else:
                consume_lines = self._calculate_qty(cr, uid, production, production_qty_uom, context=context)
            for consume in consume_lines:
                remaining_qty = consume['product_qty']
                for raw_material_line in production.move_lines:
                    if raw_material_line.state in ('done', 'cancel'):
                        continue
                    if remaining_qty <= 0:
                        break
                    if consume['product_id'] != raw_material_line.product_id.id:
                        continue
                    consumed_qty = min(remaining_qty, raw_material_line.product_qty)
                    stock_mov_obj.action_consume(cr, uid, [raw_material_line.id], consumed_qty, raw_material_line.location_id.id,
                                                 restrict_lot_id=consume['lot_id'], consumed_for=main_production_move, context=context)
                    remaining_qty -= consumed_qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    #consumed more in wizard than previously planned
                    product = self.pool.get('product.product').browse(cr, uid, consume['product_id'], context=context)
                    extra_move_id = self._make_consume_line_from_data(cr, uid, production, product, product.uom_id.id, remaining_qty, False, 0, context=context)
                    stock_mov_obj.write(cr, uid, [extra_move_id], {'restrict_lot_id': consume['lot_id'],
                                                                    'consumed_for': main_production_move}, context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)

        if production_mode == 'consume_produce':
            # To produce remaining qty of final product
            produced_products = {}
            for produced_product in production.move_created_ids2:
                if produced_product.scrapped:
                    continue
                if not produced_products.get(produced_product.product_id.id, False):
                    produced_products[produced_product.product_id.id] = 0
                produced_products[produced_product.product_id.id] += produced_product.product_qty
            for produce_product in production.move_created_ids:
                subproduct_factor = self._get_subproduct_factor(cr, uid, production.id, produce_product.id, context=context)
                lot_id = False
                if wiz:
                    lot_id = wiz.lot_id.id
                qty = min(subproduct_factor * production_qty_uom, produce_product.product_qty) #Needed when producing more than maximum quantity
                location_destination = produce_product.location_dest_id
                routing = production.routing_id
                if routing:
                    routing_loc = routing.location_id 
                    ir_sequence = self.pool.get('ir.sequence')
                    stock_picking = self.pool.get('stock.picking')
                    partner_id = False
                    if routing_loc.usage != 'internal':
				        self.pool.get('stock.move').write(cr, 1, [produce_product.id], {'location_dest_id': routing_loc.id})

                new_moves = stock_mov_obj.action_consume(cr, uid, [produce_product.id], qty,
                                                         location_id=produce_product.location_id.id, restrict_lot_id=lot_id, context=context)


                stock_mov_obj.write(cr, uid, new_moves, {'production_id': production_id,'location_dest_id':location_destination.id}, context=context)
                remaining_qty = subproduct_factor * production_qty_uom - qty
                if not float_is_zero(remaining_qty, precision_digits=precision):
                    # In case you need to make more than planned
                    #consumed more in wizard than previously planned
                    extra_move_id = stock_mov_obj.copy(cr, uid, produce_product.id, default={'product_uom_qty': remaining_qty,
                                                                                             'production_id': production_id}, context=context)
                    stock_mov_obj.action_confirm(cr, uid, [extra_move_id], context=context)
                    stock_mov_obj.action_done(cr, uid, [extra_move_id], context=context)

                if produce_product.product_id.id == production.product_id.id:
                    main_production_move = produce_product.id

	 #Code to generate Incoming Shipment and Invoice at the end of production if the routing works on supplier location
                routing = production.routing_id
                if routing:
                    routing_loc = routing.location_id 
                    ir_sequence = self.pool.get('ir.sequence')
                    stock_picking = self.pool.get('stock.picking')
                    partner_id = False
                    if routing_loc.usage != 'internal':
                        labour_product = self.pool.get('product.product').search(cr, 1, [('parent_id', '=',production.product_id.id )], context=context)

                        if not labour_product:
					        raise osv.except_osv(_('Warning!'),_('Service Product is not defined for the Job work order %s' )%(production.product_id.name))
				        #self.write(cr, uid, ids, {'location_dest_id': routing_loc.id})
				        #move_created_ids = production.move_created_ids2
				        #if move_created_ids:
				         #  self.pool.get('stock.move').write(cr, 1, [move_created_ids[0].id], {'location_dest_id': routing_loc.id})

                        pick_type = 'in'
                        partner_id = routing_loc.partner_id and routing_loc.partner_id.id or False

                        if not partner_id:
                            raise osv.except_osv(_('Warning!'), _("Please select Routing's  Production Location Address."))
                        ptype_id = 1
                        sequence_id = self.pool.get('stock.picking.type').browse(cr, uid, ptype_id, context=context).sequence_id.id
                        pick_name = self.pool.get('ir.sequence').get_id(cr, uid, sequence_id, 'id', context=context)

                        picking_id = stock_picking.create(cr, uid, {
			                        'name': pick_name,
			                        'origin': (production.origin or '').split(':')[0] + ':' + production.name,
			                        'type': pick_type,
			                        'move_type': 'one',
			                        'state': 'draft',
			                        'partner_id': partner_id,
			                        'picking_type_id':1,
			                        #'auto_picking': self._get_auto_picking(cr, uid, production),
		                        'company_id': production.company_id.id,
                        })	

                        production_line = produce_product
                        line_id = self.pool.get('stock.move').create(cr, uid, {
                                'name': production.name,
                                'picking_id': picking_id,
                                'product_id': production_line.product_id.id,
                                #'product_qty': production_line.product_qty,
                                'product_uom_qty': qty,
                                'product_uom': production_line.product_uom.id,
                                'product_uos_qty': qty,
		                        'product_uos': production_line.product_uos and production_line.product_uos.id or False,
				                'date': time.strftime('%Y-%m-%d %H:%M:%S'),
				                'move_dest_id': False,
				                'location_id': routing_loc.id,
				                'location_dest_id': 12,
				                'state': 'assigned',
				                'company_id': production.company_id.id,
                        })
				        #stock_picking.draft_force_assign(cr,uid,picking_id)
        # To create Invoices With Labour
                        fposition_id = False
                        invoice_obj = self.pool.get('account.invoice')
                        invoice_line_obj = self.pool.get('account.invoice.line')
                        partner = self.pool.get('res.partner').browse(cr, 1, partner_id, context=context)
                        #				labour_product = self.pool.get('product.product').search(cr, 1, [('parent_id', '=',production.product_id.id )], context=context)
                        #                               if not labour_product:
                        #					labour_product = self.pool.get('product.product').search(cr, 1, [('name', '=', 'Job Work')], context=context)
                        res = self.pool.get('product.product').browse(cr,uid,labour_product[0])
                        fpos_obj = self.pool.get('account.fiscal.position')
                        fpos = fpos_obj.browse(cr, 1, fposition_id, context=context) or False

                        a = res.property_account_expense.id
                        if not a:
                            a = res.categ_id.property_account_expense_categ.id
                        a = fpos_obj.map_account(cr, 1, fpos, a)
                        if a:
                            account_id = a
                        taxes = res.supplier_taxes_id and res.supplier_taxes_id or (a and self.pool.get('account.account').browse(cr, 1, a, context=context).tax_ids or False)
                        tax_id = fpos_obj.map_tax(cr, 1, fpos, taxes)
                        account_id = partner.property_account_payable.id
                        payment_term = partner.property_supplier_payment_term.id or False
                        #pdb.set_trace()
                        stock_move_ids = self.pool.get('stock.move').search(cr,uid,[('name', '=', production.name),('picking_type_id','=',2)])
                        #job_work_name = self.pool.get('stock.move').browse(cr,uid,production.id)
                        for job_work_id in stock_move_ids:
			    jobwork_name = self.pool.get('stock.move').browse(cr,uid,job_work_id).job_id.name
                        invoice_id = invoice_obj.create(cr, 1, {
                            'name': pick_name,
                            'origin': (pick_name or '') + (production.origin or '').split(':')[0] + ':' + (production.name or '') + ':' + (jobwork_name or '') ,
                            'account_id': account_id or 46,
                            'journal_id': 2,
                            'partner_id': partner_id,
                            #'comment': comment,
                            'payment_term': payment_term,
                            'fiscal_position': partner.property_account_position.id,
                            'date_invoice': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'company_id': production.company_id.id,
                            'user_id': uid,
                            'jobwork_invoice': True,
                            'type': 'in_invoice',
                            'production_id':production.id,
                            
                            
                        })
                        #pdb.set_trace()

                        account_id = res.property_account_expense
                        if not account_id:
                            account_id = res.categ_id.\
                            property_account_expense_categ


                        invoice_line_id = invoice_line_obj.create(cr, 1, {
                            'name': res.name,
                            'origin': pick_name,
                            'invoice_id': invoice_id,
                            #'uos_id': product_id.product_uos and product_id.product_uos.id or False,
                            'uos_id':res.uom_id.id or 1,
                            'product_id': res.id,
                            'account_id': account_id.id,
                            'price_unit': res.standard_price,
                            'invoice_line_tax_id':[(6,0, tax_id)],
                            #'account_analytic_id':1,
                            #'price_unit': self._get_price_unit_invoice(cr, uid, move_line, invoice_vals['type']),
                            #'discount': self._get_discount_invoice(cr, uid, move_line),
                            'quantity': qty,
                            #'invoice_line_tax_id': [(6, 0, self._get_taxes_invoice(cr, uid, move_line, invoice_vals['type']))],
                            #'account_analytic_id': self._get_account_analytic_invoice(cr, uid, picking, move_line),
                        })







        self.message_post(cr, uid, production_id, body=_("%s produced") % self._description, context=context)

        # Remove remaining products to consume if no more products to produce
        if not production.move_created_ids and production.move_lines:
            stock_mov_obj.action_cancel(cr, uid, [x.id for x in production.move_lines], context=context)

        self.signal_workflow(cr, uid, [production_id], 'button_produce_done')

# To update the products remaining to produce and quantity produced
        done = 0.0
        
        for move in production.move_created_ids2:
            if move.product_id == production.product_id:
                if not move.scrapped:
                    done += move.product_uom_qty # As uom of produced products and production order should correspond

        produced_qty = done 
        qty_to_produce = production.product_qty - done 
        self.write(cr, uid, [production.id], {'qty_produced': produced_qty ,'qty_to_produce': qty_to_produce }, context=context)
        return True



    _columns = {
        'qty_produced' : fields.float('Produced Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), copy=False),
        'qty_to_produce': fields.float('Quantity to Produce', digits_compute=dp.get_precision('Product Unit of Measure'), copy=False),
        'product_qty_ready': fields.function(_get_available_quantity_ready,
             type='float', string='Quantity Ready',
             help='If you\'ve got at least the component to produce one element,' \
             'you will have a quantity here.',
             ),

        'partial_ready': fields.boolean('Partially Ready', copy=False),
       # 'partial_ready': fields.function(_get_available_quantity_ready, multi = "partial_func",
         #    type='boolean', string='Partial Produce',
          #   help='If you\'ve got at least the component to produce one element,' \
           #  'you will have a quantity here.',
            # ),
    }

    _defaults = {
        'qty_produced': 0.0,
        'partial_ready':False,
     }

   

class mrp_product_produce_inherit(osv.osv_memory):

    _inherit = "mrp.product.produce"

    def _get_product_qty_partially(self, cr, uid, context=None):
        """ To obtain product quantity
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param context: A standard dictionary
        @return: Quantity
        """

        if context is None:
            context = {}
        prod_qty = 0.0
        if 'active_id' in context:
                prod = self.pool.get('mrp.production').browse(cr, uid,
                                        context['active_id'], context=context)
                done = 0.0
                
                for move in prod.move_created_ids2:
                    if move.product_id == prod.product_id:
          #              if not move.scrapped:
                            done += move.product_uom_qty # As uom of produced products and production order should correspond
                
                if prod.state == 'confirmed':
                    prod_qty = prod.product_qty_ready
                else:
                   prod_qty = prod.product_qty - done 

        return prod_qty


    def do_produce(self, cr, uid, ids, context=None):

        production_id = context.get('active_id', False)
        assert production_id, "Production Id should be specified in context as a Active ID."
        data = self.browse(cr, uid, ids[0], context=context)
        product_qty = data.product_qty
        mrp_production = self.pool.get('mrp.production').browse(cr, uid, production_id)
        #qty_ready = mrp_production.product_qty_ready
        #state = mrp_production.state
        if mrp_production.state == 'confirmed':
            qty_ready = mrp_production.product_qty_ready
        else:
            qty_ready = mrp_production.product_qty - mrp_production.qty_produced

        if product_qty > qty_ready:
              raise orm.except_orm(_("Warning !"),
                                 _("You can't Produce more than %s quantity.") % qty_ready)
        self.pool.get('mrp.production').action_produce(cr, uid, production_id,
                            data.product_qty, data.mode, data, context=context)
        return {}


    _columns = {

        'product_qty': fields.float('Select Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),

    }

    _defaults = {
         'product_qty': _get_product_qty_partially,

    }



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:`



