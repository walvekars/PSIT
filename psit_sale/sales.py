##############################################################################
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare
import pdb



class stock_picking(osv.osv):

    _inherit = "stock.picking"


    def unlink(self, cr, uid, ids, context=None):
        #on picking deletion, cancel its move then unlink them too
        move_obj = self.pool.get('stock.move')
        context = context or {}
        for pick in self.browse(cr, 1, ids, context=context):
            if pick.state in ['done','cancel']:
                # retrieve the string value of field in user's language
                state = dict(self.fields_get(cr, uid, context=context)['state']['selection']).get(pick.state, pick.state)
                raise osv.except_osv(_('Error!'), _('You cannot remove the picking which is in %s state!')%(state,))
            else:
                move_ids = [move.id for move in pick.move_lines]
                move_obj.action_cancel(cr, 1, move_ids, context=context)
                move_obj.unlink(cr, 1, move_ids, context=context)
        return super(stock_picking, self).unlink(cr, 1, ids, context=context)
           
           
           
# To add new field on mrp.production
class mo_order(osv.osv):

    _inherit = "mrp.production"


    def create(self, cr, uid, vals, context=None):
        
        vals['refer_routing'] = 'Refer Work Orders and Scheduled Produts below'
        return super(mo_order, self).create(cr, uid, vals, context=context)


    _columns = {
        'refer_routing':fields.char('Routing & BOM', size=100),

           }
           
           
# To add new sequence on sale.order
class sale_order(osv.osv):

    _inherit = "sale.order"


    def action_button_confirm(self, cr, uid, ids, context=None):
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        self.signal_workflow(cr, uid, ids, 'order_confirm')
        self.pool.get('procurement.order').run_scheduler(cr, 1)
        print "run schduler 1111111111111111111111"
        self.pool.get('procurement.order').run_scheduler(cr, 1)
        print "run schduler 222222222222222222222"
        self.pool.get('procurement.order').run_scheduler(cr, 1)
        print "run schduler 3333333333333333333333"
        return True
        
        
    def create(self, cr, uid, vals, context=None):
        if vals.get('qtn_sequence','/')=='/':
            vals['qtn_sequence'] = self.pool.get('ir.sequence').get(cr, uid, 'sale.order.confirmed') or '/'
        return super(sale_order, self).create(cr, uid, vals, context=context)
        

        
    _columns = {
        'qtn_sequence':fields.char('Sale Order Reference', size=64, select = True),
       	'so_sequence':fields.char('Sale Order Reference', size=64, select = True),
           }
           
# To add new fields in sale order line

class class_sale_line_order(osv.osv):

    _inherit = "sale.order.line"
    

    _defaults = {
        'product_uom_qty': 0.0,
    }    

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Prepare the dict of values to create the new invoice line for a
           sales order line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: sale.order.line record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
        res = {}
        if not line.invoiced:
            if not account_id:
                if line.product_id:
                    account_id = line.product_id.property_account_income.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ.id
                    if not account_id:
                        raise osv.except_osv(_('Error!'),
                                _('Please define income account for this product: "%s" (id:%d).') % \
                                    (line.product_id.name, line.product_id.id,))
                else:
                    prop = self.pool.get('ir.property').get(cr, uid,
                            'property_account_income_categ', 'product.category',
                            context=context)
                    account_id = prop and prop.id or False
            uosqty = self._get_line_qty(cr, uid, line, context=context)
            uos_id = self._get_line_uom(cr, uid, line, context=context)
            pu = 0.0
            if uosqty:
                pu = round(line.price_unit * line.product_uom_qty / uosqty,
                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
            fpos = line.order_id.fiscal_position or False
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
            if not account_id:
                raise osv.except_osv(_('Error!'),
                            _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
            res = {
                'name': line.name,
                'sequence': line.sequence,
                'origin': line.order_id.name,
                'account_id': account_id,
                'price_unit': pu,
                'quantity': uosqty,
                'discount': line.discount,
                'uos_id': uos_id,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
                'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
		'product_hsn_code':line.product_id.product_tmpl_id.product_hsn_code,
		
            }

        return res    


    def update_bom(self, cr, uid, ids, context=None):
    	for so_line in self.browse(cr,uid,ids):
    	  self.write(cr, uid, ids,{'product_id':so_line.product_id.id}, context=context)              

    	return True

    def change_for_bom(self, cr, uid, ids, pricelist, product, qty=0,
                       uom=False, qty_uos=0, uos=False, name='', partner_id=False,
                       lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False,
                       flag=False, context=None):
        # pdb.set_trace()
        value = {}
        bom_list = []
        if qty >= 1:
            newqty = 0
            productbrowse = self.pool.get('product.product').browse(cr, uid, product)
            newqty = qty - productbrowse.qty_available
            bom = self.pool.get('mrp.bom').search(cr, uid, [('product_id', '=', product)], context=context)
            if bom:
                lines = self.pool.get('mrp.bom').browse(cr, uid, bom[0]).bom_line_ids
                for line in lines:
                    bom_list.append((2, line.id, 0))
                    product_qty_new = line.product_qty * newqty
                    line.product_qty = product_qty_new
                    line.write({'product_qty_new3': product_qty_new})

                    bom_list.append((0, 0, {'product_qty_new3': product_qty_new}))
                    bom_list.append((1, line.id, {'product_qty_new3': product_qty_new}))
                    bom1 = self.pool.get('mrp.bom').search(cr, uid, [('product_id', '=', line.product_id.id)],
                                                           context=context)
                    if bom1:
                        lines_p = self.pool.get('mrp.bom').browse(cr, uid, bom1[0]).bom_line_ids
                        if lines_p:
                            for a in lines_p:
                                bom_list.append((2, a.id, 0))
                                product_qty_new = a.product_qty * newqty
                                a.write({'product_qty_new3': product_qty_new})
                                bom2 = self.pool.get('mrp.bom').search(cr, uid, [('product_id', '=', a.product_id.id)],
                                                                       context=context)
                                
                                bom_list.append((0, 0, {'product_qty_new3': product_qty_new}))
                                bom_list.append((1, a.id, {'product_qty_new3': product_qty_new}))
                                if bom2:
                                    lines1 = self.pool.get('mrp.bom').browse(cr, uid, bom2[0]).bom_line_ids
                                    if lines1:
                                        for b in lines1:
                                            bom_list.append((2, b.id, 0))
                                            product_qty_new = b.product_qty * newqty
                                            b.write({'product_qty_new3': product_qty_new})
                                            bom3 = self.pool.get('mrp.bom').search(cr, uid, [
                                                ('product_id', '=', b.product_id.id)], context=context)
                                        bom_list.append((0, 0, {'product_qty_new3': product_qty_new}))
                                        bom_list.append((1, b.id, {'product_qty_new3': product_qty_new}))
                                        if bom3:
                                            lines3 = self.pool.get('mrp.bom').browse(cr, uid, bom3[0]).bom_line_ids
                                            if lines3:
                                                for c in lines3:
                                                    bom_list.append((2, c.id, 0))
                                                    product_qty_new = c.product_qty * newqty
                                                    c.write({'product_qty_new3': product_qty_new})
                                                    bom_list.append((0, 0, {'product_qty_new3': product_qty_new}))
                                                    bom_list.append((1, c.id, {'product_qty_new3': product_qty_new}))

                value['product_bom'] = bom_list
            value['qty_onhand'] = productbrowse.qty_available
        return {'value': value}
    	
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        context = context or {}
        lang = lang or context.get('lang', False)
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
        warning = False
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        context = {'lang': lang, 'partner_id': partner_id}
        partner = partner_obj.browse(cr, uid, partner_id)
        lang = partner.lang
        context_partner = {'lang': lang, 'partner_id': partner_id}

        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)

        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False

        fpos = False
        if not fiscal_position:
            fpos = partner.property_account_position or False
        else:
            fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)
        if update_tax: #The quantity only have changed
            result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, product_obj.taxes_id)

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom or result.get('product_uom'),
                        'date': date_order,
                        })[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }  
#To create the bom ---- for 3 consequent parent-child relationship

	qty_onhand = product_obj.qty_available
	result['qty_onhand'] = qty_onhand  
	
        #pdb.set_trace()
	product_hsn_code=product_obj.product_tmpl_id.product_hsn_code
	result['product_hsn_code']=product_hsn_code
	bom_list = []
	bom = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',product)],context=context)               
	if bom:	
		lines = self.pool.get('mrp.bom').browse(cr,uid,bom[0]).bom_line_ids
		
		if lines:
			for line in lines:	
				bom_list.append((1, line.id, {'product_qty_new3': line.product_qty}))
				bom_list.append(line.id)
				bom1 = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',line.product_id.id)],context=context)
				if bom1:
					lines_p = self.pool.get('mrp.bom').browse(cr,uid,bom1[0]).bom_line_ids
					if lines_p:
					    for a in lines_p:
					    	bom2 = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',a.product_id.id)],context=context) 
						bom_list.append((1, a.id, {'product_qty_new3': a.product_qty}))
						bom_list.append(a.id)
						if bom2:
							lines1 = self.pool.get('mrp.bom').browse(cr,uid,bom2[0]).bom_line_ids
							if lines1:
					    			for b in lines1:
					    				bom3 = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',b.product_id.id)],context=context) 
									bom_list.append((1, b.id, {'product_qty_new3': b.product_qty}))
									bom_list.append(b.id)
									if bom3:
										lines3 = self.pool.get('mrp.bom').browse(cr,uid,bom3[0]).bom_line_ids
										if lines3:
											for c in lines3:
												bom_list.append((1, c.id, {'product_qty_new3': c.product_qty}))
												bom_list.append(c.id)
									
						              
			                 
        result['product_uom_qty'] = 1.00
        result['product_bom'] = bom_list            
        return {'value': result, 'domain': domain, 'warning': warning}
 
    def create(self, cr, uid, vals, context=None):
	
	if 'product_id' in vals:
		product = vals['product_id']
        	#product_obj = self.pool.get('product.product').browse(cr, uid, product)
		#qty_onhand = product_obj.qty_available
		#vals.update({'qty_onhand':qty_onhand})

		bom_list = []
		bom = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',product)],context=context)               
		if bom:	
		  lines = self.pool.get('mrp.bom').browse(cr,uid,bom[0]).bom_line_ids
		
		  if lines:
			for line in lines:
				#pdb.set_trace()	
				bom_list.append(line.id)
				bom1 = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',line.product_id.id)],context=context)
				if bom1:
					lines_p = self.pool.get('mrp.bom').browse(cr,uid,bom1[0]).bom_line_ids
					if lines_p:
					    for a in lines_p:
					    	bom2 = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',a.product_id.id)],context=context) 
						bom_list.append(a.id)
						if bom2:
							lines1 = self.pool.get('mrp.bom').browse(cr,uid,bom2[0]).bom_line_ids
							if lines1:
					    			for b in lines1:
					    				bom3 = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',b.product_id.id)],context=context) 
									bom_list.append(b.id)
									if bom3:
										lines3 = self.pool.get('mrp.bom').browse(cr,uid,bom3[0]).bom_line_ids
										if lines3:
					    						for c in lines3:
												bom_list.append(c.id)
						              
			

#		vals.update({'product_bom':[(6,0,bom_list)]})
        return super(class_sale_line_order, self).create(cr, uid, vals, context=context)  


    def write(self, cr, uid, ids, vals, context=None):
	if 'product_id' in vals:
		product = vals['product_id']
		bom_list = []
		bom = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',product)],context=context)               
		if bom:	
		  lines = self.pool.get('mrp.bom').browse(cr,uid,bom[0]).bom_line_ids
		
		  if lines:
			for line in lines:
				#pdb.set_trace()	
				bom_list.append(line.id)
				bom1 = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',line.product_id.id)],context=context)
				if bom1:
					lines_p = self.pool.get('mrp.bom').browse(cr,uid,bom1[0]).bom_line_ids
					if lines_p:
					    for a in lines_p:
					    	bom2 = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',a.product_id.id)],context=context) 
						bom_list.append(a.id)
						if bom2:
							lines1 = self.pool.get('mrp.bom').browse(cr,uid,bom2[0]).bom_line_ids
							if lines1:
					    			for b in lines1:
					    				bom3 = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',b.product_id.id)],context=context) 
									bom_list.append(b.id)
									if bom3:
										lines3 = self.pool.get('mrp.bom').browse(cr,uid,bom3[0]).bom_line_ids
										if lines3:
					    						for c in lines3:
												bom_list.append(c.id)
									
								      
			

		vals.update({'product_bom':[(6,0,bom_list)]})
        return super(class_sale_line_order, self).write(cr, uid, ids, vals, context=context)

     

    def _qty_onhand(self, cr, uid, ids, field_name, arg, context=None):
        product_obj = self.pool.get('product.product')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            product = line.product_id.id
            qty_onhand = product_obj.browse(cr, uid, product).qty_available
            outgoing = product_obj.browse(cr, uid, product).outgoing_qty
            res[line.id] = qty_onhand - outgoing
        return res
 

    _columns = {
        'product_bom': fields.many2many('mrp.bom.line', 'mrp_bom_sale_order_line_rela', 'line_id', 'bom_line_id', 'BOM',readonly = True, help="This is the list of products required to manufacture the main product"),
        'qty_onhand': fields.function(_qty_onhand, string = 'Quantity On Hand',readonly = True),
	
           }

class_sale_line_order()


class mrp_bom_line(osv.osv):
 
    _inherit = "mrp.bom.line"
    #_order = "bom_id,sequence"


    def _product_qty_bom(self, cr, uid, ids, field_name, arg, context=None):
        product_obj = self.pool.get('product.product')
        bom =  self.pool.get('mrp.bom')
        res = {}
	
        for line in self.browse(cr, uid, ids, context=context):
            req_qty = 0.0
	    line_parent_bom_id = line.bom_id.id
	    if 'product_uom_qty' in context:
		product_uom_qty = context['product_uom_qty']
	    else:
		product_uom_qty = 1
		
	    if 'product_id' in context:
	    	product_id = context['product_id']
		qty_avl = product_obj.browse(cr, uid, product_id).qty_available
		qty_out = product_obj.browse(cr, uid, product_id).outgoing_qty
		qty_onhand = qty_avl - qty_out
		if qty_onhand < 0:
			qty_onhand = 0.0
		req_qty = product_uom_qty - qty_onhand				    	
	    if 'product_id' in context and req_qty > 0:
            	product_id = context['product_id']
            	parent_bom = bom.search(cr, uid, [('product_id','=',product_id)],context=context)
            	parent_bom_search = bom.browse(cr,uid,parent_bom[0])
            	#for 1st level bom
            	
            	if line_parent_bom_id in parent_bom:
			
			product_qty = line.product_qty
			res[line.id] = product_qty * req_qty
		            		            		
            	#for 2nd level bom

            	else:
			#pdb.set_trace()
            		parent_product = line.bom_id.product_id.id
            		child_bom = self.search(cr, uid, [('product_id','=',line.bom_id.product_id.id),('bom_id','in',parent_bom)],context=context)
            		if child_bom:
            			product_qty = self.browse(cr,uid,child_bom[0]).product_qty
				#product_qty = line.bom_id.product_qty
				fst_parent_qty = product_qty * req_qty
				child_prdt_onhand = product_obj.browse(cr, uid, parent_product).qty_available
				child_prdt_qty_outgoing =  product_obj.browse(cr, uid, parent_product).outgoing_qty
				child_prdt_qty_onhand = child_prdt_onhand - child_prdt_qty_outgoing
				if child_prdt_qty_onhand > 0:
					req_qty = fst_parent_qty - child_prdt_qty_onhand  
				else:
					req_qty = fst_parent_qty
				if req_qty > 0:   		
					res[line.id] = req_qty * line.product_qty
				else:
					res[line.id] = 0.0
			else:
				res[line.id] = 0.0
											
		#for 3rd level bom
	    else:
			res[line.id] = 0.0
	
        return res
        
        
        	 
    def _qty_onhand(self, cr, uid, ids, field_name, arg, context=None):
        product_obj = self.pool.get('product.product')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            product = line.product_id.id
            qty_onhand = product_obj.browse(cr, uid, product).qty_available
            outgoing = product_obj.browse(cr, uid, product).outgoing_qty
            res[line.id] = qty_onhand - outgoing
        return res
        
    def _qty_incoming(self, cr, uid, ids, field_name, arg, context=None):
        product_obj = self.pool.get('product.product')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            product = line.product_id.id
            qty_incoming = product_obj.browse(cr, uid, product).incoming_qty
            res[line.id] = qty_incoming
        return res

    def _qty_difference(self, cr, uid, ids, field_name, arg, context=None):
        product_obj = self.pool.get('product.product')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            bom_qty = line.product_qty_new3
            qty_onhand = line.qty_onhand
            res[line.id] = bom_qty - qty_onhand  
        return res
                

    def _max_delivery_lead_time(self, cr, uid, ids, field_name, arg, context=None):
        product_obj = self.pool.get('product.product')
        res = {}
        if context is None:
            context = {}
	#pdb.set_trace()
        for line in self.browse(cr, uid, ids, context=context):
            product = line.product_id.id
	    max_time = 0 
            sellers = product_obj.browse(cr, uid, product).seller_ids
	    if sellers:
		for seller in sellers:
			delivery_lead_time = seller.delay
			if delivery_lead_time > max_time:
				max_time = delivery_lead_time 
            res[line.id] = max_time
        return res


    def _child_bom_id(self, cr, uid, ids, field_name, arg, context=None):
        product_obj = self.pool.get('product.product')
        res = {}
        if context is None:
            context = {}
	#pdb.set_trace()
	value = False
        for line in self.browse(cr, uid, ids, context=context):
            product = line.product_id.id
	    bom = self.pool.get('mrp.bom').search(cr, uid, [('product_id','=',product)],context=context) 
	    if bom:
	    	  #child = self.pool.get('mrp.bom.line').search(cr, uid, [('bom_id','in',bom)],context=context)
	    	  #if child:
	    	 	value = True
            else:
                  	 value = False
            res[line.id]  = value    	 
        return res

    def _cost_price(self, cr, uid, ids, field_name, arg, context=None):
        product_obj = self.pool.get('product.product')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            product = line.product_id.id
            cost = product_obj.browse(cr, uid, product).standard_price
            res[line.id] = cost

        return res
               
	
    _columns = {

        'child_bom_id': fields.function(_child_bom_id, type='boolean', string='Child'),
        'product_bom_qty': fields.function(_product_qty_bom, string = 'Product Quantity'), 
        'qty_onhand': fields.function(_qty_onhand, string = 'Quantity On Hand'), 
        'qty_difference': fields.function(_qty_difference, string = 'Qty Difference'), 
        'incoming_qty': fields.function(_qty_incoming, string = 'Incoming Qty'), 
        'max_lead': fields.function(_max_delivery_lead_time, string = 'Max Lead Time'),
        'cost': fields.function(_cost_price, string='Cost Per Piece'),
        'sale_orderlineid': fields.many2one('sale.order.line', 'Sale Order Line Ref'),
        'product_qty': fields.float(string='BOM Quantity'),
        'product_qty_new3': fields.float(related="product_qty",string='Planned Quantity '),
        }
    
mrp_bom_line() 

