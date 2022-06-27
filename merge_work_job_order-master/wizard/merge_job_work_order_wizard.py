import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.osv.orm import browse_record_list, browse_record, browse_null
import pdb
from datetime import date, datetime
from dateutil import relativedelta
import json
import time

from openerp.tools.float_utils import float_compare, float_round
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.exceptions import Warning
from openerp import SUPERUSER_ID, api
import openerp.addons.decimal_precision as dp
# from openerp.addons.procurement import procurement
import logging

_logger = logging.getLogger(__name__)


class job_order_group(osv.osv_memory):
    _name = "job.order.group"
    _description = "Job Work Order Merge"

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
            context = {}
        res = super(job_order_group, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                           context=context, toolbar=toolbar, submenu=False)
        if context.get('active_model', '') == 'job.work.order' and len(context['active_ids']) < 2:
            raise osv.except_osv(_('Warning!'),
                                 _('Please select multiple order to merge in the list view.'))
        return res

    def merge_orders(self, cr, uid, ids, context=None):
        """
             To merge similar type of job work orders.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs
             @param context: A standard dictionary

             @return: job work order view

        """
        order_obj = self.pool.get('job.work.order')
        proc_obj = self.pool.get('procurement.order')
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        result = mod_obj._get_id(cr, uid, 'psit_jobwork_order', 'view_job_work_order_tree')
        id = mod_obj.read(cr, uid, result, ['res_id'])

        allorders = order_obj.do_merge(cr, uid, context.get('active_ids', []), context)

        return {
            'domain': "[('id','in', [" + ','.join(map(str, allorders.keys())) + "])]",
            'name': _('Job Orders'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'job.work.order',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
        }


class job_orderwork(osv.osv_memory):
    _inherit = "job.work.order"
    _description = "Job Work Order Merge"

    _columns = {
        'state': fields.selection([('new', 'Open'), ('work_order', 'Closed'), ('cancelled', 'Cancelled')], 'State'),
        'order_id': fields.text('Manufacturing Order'),
        'bool': fields.boolean('check'),
    }

    def do_merge(self, cr, uid, ids, context=None):
        print 'l,xcmclkmdlkxmccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'
        """
        To merge similar type of job work orders.
        Orders will only be merged if:
        * job work Orders are in draft
        * job work Orders belong to the same partner
        * job work Orders are have same stock location, same pricelist, same currency
        Lines will only be merged if:
        * Order lines are exactly the same except for the quantity and unit

         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: the ID or list of IDs
         @param context: A standard dictionary

         @return: new job work order id

        """

        # TOFIX: merged order line should be unlink
        def make_key(br, fields):
            list_key = []
            for field in fields:
                field_val = getattr(br, field)
                if field in ('product_id', 'account_analytic_id'):
                    if not field_val:
                        field_val = False
                if isinstance(field_val, browse_record):
                    field_val = field_val.id
                elif isinstance(field_val, browse_null):
                    field_val = False
                elif isinstance(field_val, browse_record_list):
                    field_val = ((6, 0, tuple([v.id for v in field_val])),)
                list_key.append((field, field_val))
            list_key.sort()
            return tuple(list_key)

        context = dict(context or {})

        # Compute what the new orders should contain
        new_orders = {}

        order_lines_to_move = {}
        list = []
        for porder in [order for order in self.browse(cr, uid, ids, context=context) if order.state == 'new']:
            order_key = make_key(porder, ('supplier', 'pricelist_id',))
            new_order = new_orders.setdefault(order_key, ({}, []))
            new_order[1].append(porder.id)
            order_infos = new_order[0]
            order_lines_to_move.setdefault(order_key, [])
            list.append(str(porder.order.name))

            if not order_infos:
                order_infos.update({
                    'date': porder.date,
                    'supplier': porder.supplier.id,
                    'sup_ref': porder.sup_ref,
                    'pricelist_id': porder.pricelist_id.id,
                    'order': porder.order.id,
                    'state': 'new',
                    'line': {},
                    'order_id': list,
                    'bool': True
                })
            else:
                if porder.date < order_infos['date']:
                    order_infos['date'] = porder.date

            order_lines_to_move[order_key] += [order_line.id for order_line in porder.line]

        allorders = []
        orders_info = {}
        for order_key, (order_data, old_ids) in new_orders.iteritems():
            # skip merges with only one order
            if len(old_ids) < 2:
                allorders += (old_ids or [])
                continue

            # cleanup order line data
            for key, value in order_data['line'].iteritems():
                print key, value
                del value['uom_factor']
                value.update(dict(key))
            order_data['line'] = [(6, 0, order_lines_to_move[order_key])]

            # create the new order
            context.update({'mail_create_nolog': True})
            neworder_id = self.create(cr, uid, order_data)
            # self.message_post(cr, uid, [neworder_id], body=_("RFQ created"), context=context)
            orders_info.update({neworder_id: old_ids})
            allorders.append(neworder_id)

            # make triggers pointing to the old orders point to the new order
            for old_id in old_ids:
                self.redirect_workflow(cr, uid, [(old_id, neworder_id)])
                self.pool['job.work.order'].write(cr, uid, old_id, {'state': 'cancelled'}, context=context)

        return orders_info


job_orderwork()

class DeliveryOrderwork(osv.osv_memory):
    _inherit = "stock.picking"
    _description = "Delivery Order Merge"



    _columns = {
        'merge_notes': fields.text('Merge Notes'),
    }

    def do_merge(self, cr, uid, ids, context=None):
        print 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        """
        To merge similar type of purchase orders.
        Orders will only be merged if:
        * Purchase Orders are in draft
        * Purchase Orders belong to the same partner
        * Purchase Orders are have same stock location, same pricelist, same currency
        Lines will only be merged if:
        * Order lines are exactly the same except for the quantity and unit

         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: the ID or list of IDs
         @param context: A standard dictionary

         @return: new purchase order id

        """

        # TOFIX: merged order line should be unlink
        def make_key(br, fields):
            list_key = []
            for field in fields:
                field_val = getattr(br, field)
                if field in ('product_id'):
                    if not field_val:
                        field_val = False
                if isinstance(field_val, browse_record):
                    field_val = field_val.id
                elif isinstance(field_val, browse_null):
                    field_val = False
                elif isinstance(field_val, browse_record_list):
                    field_val = ((6, 0, tuple([v.id for v in field_val])),)
                list_key.append((field, field_val))
            list_key.sort()
            print list_key, 'list_key'
            return tuple(list_key)


        context = dict(context or {})

        # Compute what the new orders should contain
        new_orders = {}

        move_liness_to_move = {}
        for porder in [order for order in self.browse(cr, uid, ids, context=context) if order.state == 'assigned']:
            print porder
            order_key = make_key(porder, ('partner_id',))
            new_order = new_orders.setdefault(order_key, ({}, []))
            new_order[1].append(porder.id)
            order_infos = new_order[0]
            move_liness_to_move.setdefault(order_key, [])

            if not order_infos:
                order_infos.update({
                    'origin': porder.origin,
                    'date': porder.date,
                    'partner_id': porder.partner_id.id,
                    'min_date': porder.min_date,
                    'invoice_type_id':porder.invoice_type_id.id,
                    'move_type':porder.move_type,
                    'inv_state':porder.invoice_state,
                    'picking_type_id':porder.picking_type_id.id,
                    'date_done':porder.date_done,
                    'group_id':porder.group_id,
                    'priority':porder.priority,
                    'carrier_id':porder.carrier_id.id,
                    'carrier_tracking_ref':porder.carrier_tracking_ref,
                    'weight':porder.weight,
                    'weight_uom_id':porder.weight_uom_id.id,
                    'weight_net':porder.weight_net,
                    'number_of_packages':porder.number_of_packages,
                    'state': 'draft',
                    'move_lines': {},
                })
            else:
                if porder.date < order_infos['date']:
                    order_infos['date'] = porder.date
                if porder.origin:
                    order_infos['origin'] = (order_infos['origin'] or '') + ' ' + porder.origin

            move_liness_to_move[order_key] += [move_lines.id for move_lines in porder.move_lines]

        allorders = []
        orders_info = {}
        for order_key, (order_data, old_ids) in new_orders.iteritems():
            # skip merges with only one order
            if len(old_ids) < 2:
                allorders += (old_ids or [])
                continue

            # cleanup order line data
            for key, value in order_data['move_lines'].iteritems():
                del value['uom_factor']
                value.update(dict(key))
            order_data['move_lines'] = [(6, 0, move_liness_to_move[order_key])]

            # create the new order
            context.update({'mail_create_nolog': True})
            neworder_id = self.create(cr, uid, order_data)
            self.message_post(cr, uid, [neworder_id], body=_("RFQ created"), context=context)
            orders_info.update({neworder_id: old_ids})
            allorders.append(neworder_id)

            # make triggers pointing to the old orders point to the new order
            for old_id in old_ids:
                self.redirect_workflow(cr, uid, [(old_id, neworder_id)])
                self.signal_workflow(cr, uid, [old_id], 'purchase_cancel')

        return orders_info
DeliveryOrderwork()


class delivery_order_merge_class(osv.osv_memory):
    _name = "delivery.order.merge"
    _description = "Delivery Order Merge"
    _columns = {
        # "target_picking_id": fields.many2one("stock.picking","Target Picking"),
        "picking_ids": fields.many2many("stock.picking.out", "wizard_stock_move_picking_merge", "merge_id",
                                        "picking_id"),

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
            context = {}
        res = super(delivery_order_merge_class, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type,
                                                                      context=context, toolbar=toolbar, submenu=False)
        if context.get('active_model', '') == 'stock.picking' and len(context['active_ids']) < 2:
            raise osv.except_osv(_('Warning!'),
                                 _('Please select multiple order to merge in the list view.'))
        partner_id = False
        if 'active_ids' in context:
            delivery_orders = context['active_ids']

            part = False
            state = False
            for order in delivery_orders:
                order_brow = self.pool.get('stock.picking').browse(cr, uid, order)
                next_part = order_brow.partner_id.id
                next_state = order_brow.state
                if next_state == 'cancel':
                    raise osv.except_osv(_('Warning!'), _("Merging Delivery Order's State Should not be Cancelled"))
                if next_state == 'done':
                    raise osv.except_osv(_('Warning!'), _("Merging Delivery Order's State Should not be delivered"))
                if state:
                    if state != next_state:
                        raise osv.except_osv(_('Warning!'), _("Merging Delivery Order's State Should be Same"))
                if part:
                    if part != next_part:
                        raise osv.except_osv(_('Warning!'), _("Merging Delivery Order's Partner Should be Same"))
                part = next_part
                state = next_state

        return res

    # # Merge Button Function
    # def merge_orders(self, cr, uid, ids, context=None):
    #     """
    #          To merge similar type(same customer and state) of delivery orders.
    #          @return: delivery order view
    #
    #     """
    #
    #     order_obj = self.pool.get('stock.picking')
    #     mod_obj = self.pool.get('ir.model.data')
    #     if context is None:
    #         context = {}
    #     result = mod_obj._get_id(cr, uid, 'stock', 'vpicktree')
    #     id = mod_obj.read(cr, uid, result, ['res_id'])
    #
    #     allorders = order_obj.do_merge(cr, uid, context.get('active_ids', []), context)
    #
    #     # view_id = self.pool.get('ir.ui.view').search(cr,uid,[('model','=','stock.picking.out'), ('name','=','stock.picking.out.tree')])
    #     return True


    def merge_orders(self, cr, uid, ids, context=None):
        """
             To merge similar type of purchase orders.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs
             @param context: A standard dictionary

             @return: purchase order view

        """
        order_obj = self.pool.get('stock.picking')
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        result = mod_obj._get_id(cr, uid, 'stock', 'view_picking_internal_search')
        id = mod_obj.read(cr, uid, result, ['res_id'])

        allorders = order_obj.do_merge(cr, uid, context.get('active_ids', []), context)

        return {
            'domain': "[('id','in', [" + ','.join(map(str, allorders.keys())) + "])]",
            'name': _('Delivery Orders'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'search_view_id': id['res_id']
        }


delivery_order_merge_class()
