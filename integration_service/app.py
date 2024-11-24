from flask import Flask, render_template, redirect, request
import requests
from utils.oauth import get_access_token, fetch_user_data
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

CLIENT_ID = os.getenv('EVE_CLIENT_ID')
CLIENT_SECRET = os.getenv('EVE_CLIENT_SECRET')
REDIRECT_URI = os.getenv('EVE_REDIRECT_URI')
SCOPE = 'esi-characters.read_corporation_roles.v1 esi-mail.send_mail.v1'

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login')
def login():
    return redirect(f'https://login.eveonline.com/v2/oauth/authorize/?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPE}')

@app.route('/callback')
def callback():
    code = request.args.get('code')
    access_token = get_access_token(code)
    user_data = fetch_user_data(access_token)
    return render_template('success.html', user_data=user_data)

if __name__ == '__main__':
    app.run(debug=True)