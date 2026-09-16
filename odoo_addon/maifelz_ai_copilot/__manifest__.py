{
    'name': 'mAifelZ AI Copilot',
    'version': '1.0.0',
    'category': 'Productivity/AI',
    'summary': 'Conversational AI Executive & Financial Copilot for Odoo',
    'sequence': 1,
    'author': 'mAifelZ Technologies',
    'website': 'https://maifelz.com',
    'license': 'OPL-1',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/copilot_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/copilot_menus.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}

