# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp import pooler
import pdb

class job(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
       
        super(job, self).__init__(cr, uid, name, context=context)
        #if 'active_ids' in context:

         #   jw_ids = context['active_ids']

          #  for jwo in jw_ids:

           #     state = self.pool.get('job.work.order').browse(cr,uid,jwo).state

            #    if state == 'new':

             #   	self.pool.get('job.work.order').write(cr,uid,jwo,{'state': 'work_order'})


report_sxw.report_sxw('report.job.work.order','job.work.order','addons/psit_jobwork_order/report/job_order.rml',parser=job)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

