from flask import Flask, render_template, redirect, request, session, url_for
import requests
from utils.oauth import get_access_token, fetch_user_data
from dotenv import load_dotenv
import os
import secrets

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Set a secret key for the session

CLIENT_ID = os.getenv('EVE_CLIENT_ID')
CLIENT_SECRET = os.getenv('EVE_CLIENT_SECRET')
REDIRECT_URI = os.getenv('EVE_REDIRECT_URI')
SCOPE = 'esi-corporations.read_corporation_membership.v1 esi-mail.send_mail.v1'  # Updated scope

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login')
def login():
    state = secrets.token_hex(16)  # Generate a random state parameter
    session['oauth_state'] = state  # Store the state in the session
    authorization_url = f"https://login.eveonline.com/v2/oauth/authorize/?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPE}&state={state}"
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')

    # Verify the state parameter
    stored_state = session.pop('oauth_state', None)
    if state != stored_state:
        return "Invalid state parameter."

    access_token = get_access_token(code)
    user_data = fetch_user_data(access_token)

    # Send user data to Odoo
    odoo_url = 'http://localhost:8069/eve/auth'  # Update this URL
    response = requests.post(odoo_url, json=user_data)

    return render_template('success.html', user_data=user_data)

if __name__ == '__main__':
    app.run(debug=True)
