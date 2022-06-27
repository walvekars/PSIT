# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Devintelle Software Solutions (<http://devintelle.com>).
#
##############################################################################
from datetime import timedelta
from openerp import models, fields, api, _
from openerp.exceptions import Warning

			

class res_partner(models.Model):
    
    """ Add gst Number """
    _inherit = 'res.partner'
    _description = 'Add gst Number'

    partner_gst_number = fields.Char('GSTIN Number')
    gst_reverse_charge =  fields.Boolean("GST on Reverse Charge")
    
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

