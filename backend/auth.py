import os
import logging
from flask import Flask, redirect, request, url_for, session
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
HUBSPOT_CLIENT_ID = os.getenv('HUBSPOT_CLIENT_ID')
HUBSPOT_CLIENT_SECRET = os.getenv('HUBSPOT_CLIENT_SECRET')
REDIRECT_URI = os.getenv('HUBSPOT_REDIRECT_URI')

# Configure Flask
auth_app = Flask(__name__)
auth_app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth_app")

# Step 1: Redirect user to HubSpot consent page
@auth_app.route('/connect')
def connect():
    params = {
        'client_id': HUBSPOT_CLIENT_ID,
        'scope': 'content marketing-email',
        'redirect_uri': REDIRECT_URI,
        'state': 'optional_csrf_token',
    }
    # Construct the OAuth consent URL with proper query parameters
    authorize_url = (
        "https://app.hubspot.com/oauth/authorize?"
        + str(httpx.QueryParams(params))
    )
    return redirect(authorize_url)

# Step 2: Handle OAuth callback and exchange code for tokens
@auth_app.route('/oauth-callback')
def oauth_callback():
    error = request.args.get('error')
    if error:
        return f"Error: {error}", 400

    code = request.args.get('code')
    state = request.args.get('state')
    # TODO: validate state for CSRF

    data = {
        'grant_type': 'authorization_code',
        'client_id': HUBSPOT_CLIENT_ID,
        'client_secret': HUBSPOT_CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'code': code,
    }
    try:
        resp = httpx.post('https://api.hubapi.com/oauth/v1/token', data=data)
        resp.raise_for_status()
        tokens = resp.json()
        # Store tokens securely (e.g. in database tied to user session)
        session['hubspot_tokens'] = tokens
        # Log the actual access token so you can copy it from your terminal
        logger.info(f"▶️  Access token: {tokens['access_token']}")
        return "Connected to HubSpot successfully! (check your Flask logs for the token)"
    except Exception as e:
        logger.error(f"OAuth token exchange failed: {e}")
        return "Token exchange error", 500

if __name__ == '__main__':
    auth_app.run(host='0.0.0.0', port=8000, debug=True)
