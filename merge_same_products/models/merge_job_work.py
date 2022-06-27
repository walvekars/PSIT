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
from openerp import api, models,fields
import pdb



class JobWorkOrderAppend(models.Model):
    _inherit = "job.work.order"

    @api.model
    def create(self, vals):
        if "line" in vals.keys():
            try:
                if vals['line']:
                    # pdb.set_trace()
                    if  vals['line'][0]:
                        if list(vals['line'][0])[2]:
                            print list(vals['line'][0])[2]
                            product_list = []
                            old_job_ids= self.env['job.work.order'].search([('line', 'in', list(vals['line'][0])[2])])
                            for obj in self.env['job.work.order.line'].search([('id', 'in', list(vals['line'][0])[2])]):
                                if obj not in product_list:
                                    product_list.append(obj)
                            list_new = self.env['job.work.order.line'].search([('id', 'in', list(vals['line'][0])[2])])
                            new_list = []
                            c=0
                            print list_new
                            for obj in product_list:
                                count = 0
                                qty = 0
                                for ele in list_new:
                                    if obj.name == ele.name:
                                        count = count+1
                                        qty =qty+ ele.quantity
                                        ele.quantity=0
                                        if count == 1:
                                            if ele not in new_list:
                                                new_list.append(ele)
                                for att in new_list:
                                    if obj.name == att.name:
                                        att.quantity = qty
                                        qty = 0
                                    for n, i in enumerate(product_list):
                                        if i == att:
                                            product_list[n] = ''
                            lists=[]
                            for i in new_list:
                                lists.append(i.id)
                print lists
                vals.update({'line': [(6, 0, lists)]})

            except Exception:
                pass

        res = super(JobWorkOrderAppend, self).create(vals)
        if res.order_id==False:
	    res.order_id = res.order.name
        if "line" in vals.keys():
	    for job_work_id in old_job_ids:
		move_ids = self.env['stock.move'].search([('name','=',job_work_id.order.name),('picking_type_id','=',2)])
		for move_id in move_ids:
		    move_id.write({'job_id': res.id})
        return res
