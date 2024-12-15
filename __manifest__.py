{
    'name': 'Sales Target vs Achievement',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Track sales targets and achievements for each salesperson.',
    'description': 'Track sales targets and achievements for each salesperson.',
    'author': 'Hasinur Arefin Shawon',
    'depends': ['base', 'sale','sha_salextra'],
    'license': 'LGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/sales_target_view.xml',
        'views/target_setup_view.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}