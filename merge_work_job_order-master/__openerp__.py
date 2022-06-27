# -*- coding: utf-8 -*-

{
    'name': 'Merge Job Order',
    'category': 'Job Work Order',
    'version': '8.0',
    'website': 'http://www.aktivsoftware.com',
    'author': 'Athira',
    'description': 'Merge Job Order',

    'depends': [
        'purchase','stock','psit_jobwork_order',
    ],

    'data': [
        'wizard/merge_job_work_order_wizard_view.xml',
    ],


    'auto_install': False,
    'installable': True,
    'application': False

}
