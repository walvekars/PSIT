from openerp import api, models,_
import pdb
from openerp.exceptions import ValidationError


class ManufacturingOrderAppend(models.Model):
    _inherit = "mrp.production"

    @api.model
    def create(self, vals):
        if "move_lines" in vals.keys():
            try:
                if vals['move_lines']:
                    # pdb.set_trace()
                    if  vals['move_lines'][0]:
                        if list(vals['move_lines'][0])[2]:
                            print list(vals['move_lines'][0])[2]
                            product_list = []
                            for obj in self.env['stock.move'].search([('id', '=', list(vals['move_lines'][0])[2])]):
                                if obj not in product_list:
                                    product_list.append(obj)
                            list_new = self.env['stock.move'].search([('id', '=', list(vals['move_lines'][0])[2])])
                            new_list = []
                            c=0
                            for obj in product_list:
                                count = 0
                                qty = 0
                                for ele in list_new:
                                    if obj.product_id == ele.product_id:
                                        count = count+1
                                        qty =qty+ ele.product_uom_qty
                                        if count == 1:
                                            if ele not in new_list:
                                                new_list.append(ele)
                                for att in new_list:
                                    if obj.product_id == att.product_id:
                                        att.product_uom_qty = qty
                                    for n, i in enumerate(product_list):
                                        if i == att:
                                            product_list[n] = ''
                            lists=[]
                            for i in new_list:
                                lists.append(i.id)
                vals.update({'move_lines': [(6, 0, lists)]})

            except Exception:
                pass

        res = super(ManufacturingOrderAppend, self).create(vals)
        return res
