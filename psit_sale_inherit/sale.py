from openerp import fields,models,api




class sale_line_order(models.Model):

    _inherit = "sale.order.line"

    @api.depends('product_bom')
    def _total_cost(self):
        count=0
        for el in self.product_bom:
            count=el.cost+count

        self.total_rmper_qty=count
        self.total_cost_qty = self.total_rmper_qty * self.product_uom_qty




    total_rmper_qty =  fields.Float(string='Total  RM Cost Per Quantity', readonly=True, compute ='_total_cost')
    total_cost_qty = fields.Float(string='Total RM Cost ', readonly=True, compute='_total_cost')



