from openerp import api, models,fields, _
from openerp.tools import float_is_zero
import pdb
from openerp.exceptions import ValidationError
from datetime import date, datetime
import pdb

class JobworkOrder(models.Model):
    _inherit = "job.work.order"
    
    @api.model
    def create(self,vals):
	
	res = super(JobworkOrder, self).create(vals)
	#pdb.set_trace()
	res.product_id = res.order.product_id.id
        return res

    product_name = fields.Many2one(related='order.product_id', store=True, readonly=True, copy=False)               

class StockPickingAppend(models.Model):
    _inherit = "stock.picking"

    @api.model
    def create(self, vals):
        print 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', vals
        if "move_lines" in vals.keys():
            try:
                if vals['move_lines']:
                    # pdb.set_trace()
                    if vals['move_lines'][0]:
                        if list(vals['move_lines'][0])[2]:
                            print list(vals['move_lines'][0])[2]
                            product_list = []
                            for obj in self.env['stock.move'].search([('id', '=', list(vals['move_lines'][0])[2])]):
                                if obj not in product_list:
                                    product_list.append(obj)
                            list_new = self.env['stock.move'].search([('id', '=', list(vals['move_lines'][0])[2])])
                            new_list = []
                            c = 0

                            for obj in product_list:
                                count = 0
                                qty = 0
                                for ele in list_new:
                                    if obj.product_id == ele.product_id:
                                        count = count + 1
                                        qty = qty + ele.product_uom_qty
                                        if count == 1:
                                            if ele not in new_list:
                                                new_list.append(ele)
                                for att in new_list:
                                    if obj.product_id == att.product_id:
                                        att.product_uom_qty = qty
                                    for n, i in enumerate(product_list):
                                        if i == att:
                                            product_list[n] = ''

                            lists = []
                            for i in new_list:
                                lists.append(i.id)
                vals.update({'move_lines': [(6, 0, lists)]})

            except Exception:
                pass

        res = super(StockPickingAppend, self).create(vals)
        return res

    @api.onchange('move_lines')
    def onchange_move_line(self):
        print 'akjxzkjfhkjdszhlkjd'
        list = []
        for line in [x for n, x in enumerate(self.move_lines) if x.product_id not in self.move_lines[:n]]:
            list.append(str(line.name) + ',')

        self.origin = str(list)

    @api.one
    def write(self, vals):
        print vals
        product_list_ext = []
        product_list_new = []
        if "move_lines" in vals.keys():
            new_list = vals['move_lines']
            for att in new_list:
                if att[0] == 4:
                    s = self.move_lines.browse(att[1])
                    if s.product_id.id not in product_list_ext:
                        product_list_ext.append(s.product_id.id)
                if att[0] == 0:
                    if att[2]['product_id'] not in product_list_new:
                        product_list_new.append(att[2]['product_id'])
            pro_list = []
            for obj in product_list_new:
                pro_qty = 0
                if obj in product_list_ext:
                    for att in new_list:
                        if att[0] == 4:
                            o = self.move_lines.browse(att[1])
                            if o.product_id.id == obj:
                                pro_qty += o.product_uom_qty
                        if att[1] == 0:
                            if att[2]['product_id'] == obj:
                                pro_qty += 1
                    for att1 in new_list:
                        if att1[0] == 4:
                            o = self.move_lines.browse(att1[1])
                            if o.product_id.id == obj:
                                o.product_uom_qty = pro_qty
            for obj1 in product_list_new:
                pro_qty = 0
                count = 0
                if obj not in product_list_ext:
                    for att1 in new_list:
                        if att1[0] == 0:
                            if att1[2]['product_id'] == obj1:
                                pro_qty += att1[2]['product_uom_qty']
                    for att2 in new_list:
                        if att2[0] == 0:
                            if att2[2]['product_id'] == obj:
                                count += 1
                                if count == 1:
                                    att2[2]['product_uom_qty'] = pro_qty
                                    pro_list.append(att2)
            for obj2 in product_list_ext:
                if obj2 not in product_list_new:
                    for att2 in new_list:
                        if att2[0] == 4:
                            o = self.move_lines.browse(att2[1])
                            if o.product_id == obj2:
                                pro_list.append(att2)
            for att3 in new_list:
                if att3[0] == 2:
                    pro_list.append(att3)
                if att3[0] == 1:
                    o = self.move_lines.browse(att3[1])
                    if "product_uom_qty" in att3[2]:
                        o.product_uom_qty = att3[2]['product_uom_qty']
            vals['move_lines'] = pro_list
        res = super(StockPickingAppend, self).write(vals)
        return res

    @api.multi
    def do_enter_transfer_details(self, picking):
	res = super(StockPickingAppend, self).do_enter_transfer_details()
	origin = (self.origin).strip()
	if self.picking_type_id.code == 'outgoing' and origin[:2] == 'MO':

	    for move_obj in self.move_lines:
	        if move_obj.state=='assigned':
		    if self.env['job.work.order'].search(
			    [('order.name', '=', move_obj.name), ('state', '=', 'work_order')]):
			pass
		    elif self.env['job.work.order'].search(
			    [('order_id', 'ilike', move_obj.name), ('state', '=', 'work_order')]):
			pass
		    else:
			raise ValidationError(
			    _("Please confirm job workorder related to delivery order"))

	return res



