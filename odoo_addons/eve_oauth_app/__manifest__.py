{
    'name': "Eve Online Odoo Intergration",
    'summary': """
                Login via Eve Online logs user into Odoo using their Eve Online credentials.
    """,
    'description': """
                    Eve Online
                    Odoo Eve Online
                    Eve Online login
                    Odoo Eve Online integration
                    Eve Online Odoo integration
                    Odoo+Eve Online
                    Eve Online Odoo login
                    Odoo Eve Online authentication
                    Eve Online login on Odoo
                    Knights Cross Engineering
    """,

    'author': "Knights Cross Engineering",
    'website': "https://www.knightscrossengineering.com",
    'category': 'Technical',
    'version': '1.0.0',
    'application': True,
    'license': 'LGPL-3',
    'maintainer': 'Knights Cross Engineering',
    'support': 'support@knightscrossengineering.com',
    'images': ['static/KCE_logo.png'],
    'depends': ['auth_oauth'],
    'data': [
        'data/eve_oauth_auth.xml',
        'views/eve_oauth_providers_views.xml',
    ]
}
