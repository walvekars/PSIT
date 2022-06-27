# -*- coding: utf-8 -*-
##############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2009-TODAY Cybrosys Technologies(<http://www.cybrosys.com>).
#    Author: Niyas Raphy(<http://www.cybrosys.com>)
#    you can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    It is forbidden to publish, distribute, sublicense, or sell copies
#    of the Software or modified copies of the Software.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    GENERAL PUBLIC LICENSE (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import api, models,_
import pdb
from openerp.exceptions import ValidationError


class PurchaseOrderAppend(models.Model):
    _inherit = "purchase.order"

    @api.model
    def create(self, vals):
        if "order_line" in vals.keys():
            try:
                if vals['order_line']:
                    if  vals['order_line'][0]:
                        if list(vals['order_line'][0])[2]:
                            print list(vals['order_line'][0])[2]
                            product_list = []
                            for obj in self.env['purchase.order.line'].search([('id', '=', list(vals['order_line'][0])[2])]):
                                if obj not in product_list:
                                    product_list.append(obj)
                            list_new = self.env['purchase.order.line'].search([('id', '=', list(vals['order_line'][0])[2])])
                            new_list = []
                            c=0
                            for obj in product_list:
                                count = 0
                                qty = 0
                                for ele in list_new:
                                    if obj.product_id == ele.product_id:
                                        count = count+1
                                        qty =qty+ ele.product_qty
                                        if count == 1:
                                            if ele not in new_list:
                                                new_list.append(ele)
                                for att in new_list:
                                    if obj.product_id == att.product_id:
                                        att.product_qty = qty
                                    for n, i in enumerate(product_list):
                                        if i == att:
                                            product_list[n] = ''
                            lists=[]
                            for i in new_list:
                                lists.append(i.id)
                vals.update({'order_line': [(6, 0, lists)]})

            except Exception:
                pass

        res = super(PurchaseOrderAppend, self).create(vals)
        return res

    @api.one
    def write(self, vals):
        product_list_ext = []
        product_list_new = []
        if "order_line" in vals.keys():
            new_list = vals['order_line']
            pro_list = []
            for att in new_list:
                if att[0] == 4:
                    s = self.order_line.browse(att[1])
                    if s.product_id.id not in product_list_ext:
                        product_list_ext.append(s.product_id.id)
                if att[0] == 0:
                    if att[2]['product_id'] not in product_list_new:
                        product_list_new.append(att[2]['product_id'])

            for obj in product_list_new:
                pro_qty = 0
                if obj in product_list_ext:
                    for att in new_list:
                        if att[0] == 4:
                            o = self.order_line.browse(att[1])
                            if o.product_id.id == obj:
                                pro_qty += o.product_qty
                        if att[1] == 0:
                            if att[2]['product_id'] == obj:
                                pro_qty += att[2]['product_qty']
                    for att1 in new_list:
                        if att1[0] == 4:
                            o = self.order_line.browse(att1[1])
                            if o.product_id.id == obj:
                                    o.product_qty = pro_qty
            for obj1 in product_list_new:
                pro_qty = 0
                count = 0
                if obj not in product_list_ext:
                    for att1 in new_list:
                        if att1[0] == 0:
                            if att1[2]['product_id'] == obj1:
                                pro_qty += 1
                    for att2 in new_list:
                        if att2[0] == 0:
                            if att2[2]['product_id'] == obj:
                                count += 1
                                if count == 1:
                                    att2[2]['product_qty'] = pro_qty
                                    pro_list.append(att2)

            for obj2 in product_list_ext:
                if obj2 not in product_list_new:
                    for att2 in new_list:
                        if att2[0] == 4:
                            o = self.order_line.browse(att2[1])
                            if o.product_id == obj2:
                                pro_list.append(att2)
            for att3 in new_list:
                if att3[0] == 2:
                    pro_list.append(att3)
                if att3[0] == 1:
                    o = self.order_line.browse(att3[1])
                    o.product_qty = att3[2]['product_qty']
            vals['order_line'] = pro_list

        res = super(PurchaseOrderAppend, self).write(vals)
        return res





