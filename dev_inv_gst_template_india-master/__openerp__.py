
{
    'name': 'Indian GST Invoice Format',
    'version': '1.0',
    'sequence':1,
    'category': 'Account',
    'description': """
        App will print New Invocie Format of Indian GST.
    """,
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'summary': 'App will print New Invocie Format of Indian GST.',
    'website': 'http://www.devintellecs.com/',
    'images': [],
    'depends': ['account','sale','product',],
    'data': [
        
        'dev_gst_invoice_menu.xml',
        'report/demo_gst_invoice_report.xml',
        'view/res_partner.xml',
    ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
