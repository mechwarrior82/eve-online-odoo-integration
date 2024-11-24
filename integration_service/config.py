import os

CLIENT_ID = os.getenv('EVE_CLIENT_ID', 'default_client_id')
CLIENT_SECRET = os.getenv('EVE_CLIENT_SECRET', 'default_client_secret')
REDIRECT_URI = os.getenv('EVE_REDIRECT_URI', 'default_redirect_uri')
SCOPE = 'esi-characters.read_corporation_roles.v1 esi-mail.send_mail.v1'
