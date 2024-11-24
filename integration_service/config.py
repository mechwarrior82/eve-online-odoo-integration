import os

CLIENT_ID = os.getenv('EVE_CLIENT_ID', 'default_client_id')
CLIENT_SECRET = os.getenv('EVE_CLIENT_SECRET', 'default_client_secret')
REDIRECT_URI = os.getenv('EVE_REDIRECT_URI', 'default_redirect_uri')
ODOO_URL = os.getenv('ODOO_URL', 'http://localhost:8069')  # Add this line
SCOPE = 'esi-corporations.read_corporation_membership.v1 esi-mail.send_mail.v1'
