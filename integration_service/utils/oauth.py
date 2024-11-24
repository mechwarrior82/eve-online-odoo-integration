import requests
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI

def get_access_token(code):
    response = requests.post('https://login.eveonline.com/v2/oauth/token', data={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI
    })
    token_data = response.json()
    return token_data['access_token']

def fetch_user_data(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get('https://esi.evetech.net/verify', headers=headers)
    return response.json()
