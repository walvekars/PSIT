
{
    'name': 'GST Taxes Report',
    'version': '1.0',
    'sequence':1,
    'category': 'Account',
    'description': """
        App will print New Invocie Format of Indian GST.
    """,
    'author': 'Shivashant Dambal',
    'summary': 'App will print New Tax Format of Indian GST.',
    'website': 'http://www.pmcs.com/',
    'images': [],
    'depends': ['account','sale','product',],
    'data': [
        
        'dev_gst_tax_menu.xml',
        'report/demo_gst_tax_report.xml',
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
