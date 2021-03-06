# -*- encoding: utf-8 -*-

##############################################################################
import time
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare
import pdb


# To add new fields in Purchase report change

class purchase_order(osv.osv):

    _inherit = "purchase.order"

    def print_purchase_order(self, cr, uid, ids, context=None):
        '''
        This function prints the purchase order       '''
        #assert len(ids) == 1, 'This option should only be used for a single id at a time'
        #wf_service = netsvc.LocalService("workflow")
        #wf_service.trg_validate(uid, 'purchase.order', ids[0], 'send_rfq', cr)
        datas = {
                 'model': 'purchase.order',
                 'ids': ids,
                 'form': self.read(cr, uid, ids[0], context=context),
        }
        return {'type': 'ir.actions.report.xml', 'report_name': 'purchase.order', 'datas': datas, 'nodestroy': True}
        
        
        #While creating, the value should from  take the default amount field 
    def create(self, cr, uid, vals, context=None):
        product_obj = self.pool.get('product.product')
        vals['date_order']=fields.date.context_today(self,cr,uid,context=context)
	#pdb.set_trace()
        return super(purchase_order, self).create(cr, uid, vals, context=context)
         
    _columns = {
    	 'create_date': fields.datetime('Creation Date', readonly=True, select=True, help="Date on which PO is created."),
            #'rfq_sequence': fields.char('RFQ_Sequence',size=250),
            }
            


 
  

purchase_order()     
