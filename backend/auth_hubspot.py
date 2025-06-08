import os
import logging
import time
from typing import Dict
import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from uuid import uuid4
from dotenv import load_dotenv

# --- Setup ---
logger = logging.getLogger("auth_hubspot")
load_dotenv()

HUBSPOT_CLIENT_ID = os.getenv('HUBSPOT_CLIENT_ID')
HUBSPOT_CLIENT_SECRET = os.getenv('HUBSPOT_CLIENT_SECRET')
# This should be the full URL to your backend's callback endpoint
REDIRECT_URI = os.getenv('HUBSPOT_REDIRECT_URI', 'http://localhost:8000/auth/hubspot/oauth-callback')
# The URL to redirect to after successful authentication
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')

SESSION_COOKIE_NAME = "mcp_chat_session_id"

# In-memory store for tokens. In a production app, use a database.
# { session_id: { "access_token": ..., "refresh_token": ..., "expires_at": ... } }
hubspot_tokens: Dict[str, Dict] = {}

router = APIRouter()

# --- Helper Functions ---
def get_session_id(request: Request, response: Response) -> str:
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        session_id = str(uuid4())
        # The response object is used to set the cookie on the client
        response.set_cookie(key=SESSION_COOKIE_NAME, value=session_id, httponly=True, samesite='lax')
    return session_id

async def get_valid_token(session_id: str) -> str | None:
    """
    Retrieves a valid access token for the given session, refreshing if necessary.
    """
    token_info = hubspot_tokens.get(session_id)
    if not token_info:
        return None

    # Check if token is expired or close to expiring (e.g., 5 minutes buffer)
    if time.time() > token_info.get("expires_at", 0) - 300:
        logger.info(f"HubSpot token for session {session_id[:8]}... expired or expiring soon. Refreshing.")
        try:
            refresh_data = {
                'grant_type': 'refresh_token',
                'client_id': HUBSPOT_CLIENT_ID,
                'client_secret': HUBSPOT_CLIENT_SECRET,
                'refresh_token': token_info['refresh_token'],
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post('https://api.hubapi.com/oauth/v1/token', data=refresh_data)
                resp.raise_for_status()
                new_tokens = resp.json()

                # Update stored tokens
                token_info['access_token'] = new_tokens['access_token']
                # HubSpot might issue a new refresh token
                if 'refresh_token' in new_tokens:
                    token_info['refresh_token'] = new_tokens['refresh_token']
                token_info['expires_at'] = time.time() + new_tokens['expires_in']
                hubspot_tokens[session_id] = token_info
                logger.info(f"Successfully refreshed HubSpot token for session {session_id[:8]}...")
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to refresh HubSpot token for session {session_id[:8]}: {e.response.status_code} {e.response.text}")
            # If refresh fails, the token is invalid. Remove it.
            if session_id in hubspot_tokens:
                del hubspot_tokens[session_id]
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during token refresh for session {session_id[:8]}: {e}")
            return None

    return token_info.get("access_token")

# --- API Endpoints ---
@router.get("/auth/hubspot/connect", summary="Redirect to HubSpot for OAuth consent")
async def hubspot_connect():
    """
    Initiates the HubSpot OAuth2 flow by redirecting the user to HubSpot's authorization page.
    """
    if not HUBSPOT_CLIENT_ID:
        logger.error("HUBSPOT_CLIENT_ID is not set.")
        raise HTTPException(status_code=500, detail="HubSpot integration is not configured on the server.")
    
    params = {
        'client_id': HUBSPOT_CLIENT_ID,
        'scope': 'content marketing-email',
        'redirect_uri': REDIRECT_URI,
    }
    authorize_url = f"https://app.hubspot.com/oauth/authorize?{httpx.QueryParams(params)}"
    return RedirectResponse(authorize_url)

@router.get("/auth/hubspot/oauth-callback", summary="Handle HubSpot OAuth callback")
async def hubspot_oauth_callback(request: Request, code: str | None = None, error: str | None = None):
    """
    Handles the callback from HubSpot after user consent. Exchanges the authorization
    code for an access token and refresh token.
    """
    # Start with a failure redirect URL, change on success
    response = RedirectResponse(url=f"{FRONTEND_URL}?auth_status=failed")
    if error:
        logger.error(f"HubSpot OAuth error: {error}")
        return response
    if not code:
        logger.error("HubSpot OAuth callback missing 'code'.")
        return response

    session_id = get_session_id(request, response)

    token_data = {
        'grant_type': 'authorization_code',
        'client_id': HUBSPOT_CLIENT_ID,
        'client_secret': HUBSPOT_CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'code': code,
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post('https://api.hubapi.com/oauth/v1/token', data=token_data)
            resp.raise_for_status()
            tokens = resp.json()

            # Store tokens in our session-keyed dictionary
            hubspot_tokens[session_id] = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": time.time() + tokens["expires_in"],
            }
            logger.info(f"Successfully obtained HubSpot tokens for session {session_id[:8]}...")
            
            # Redirect back to the frontend, indicating success
            response = RedirectResponse(url=f"{FRONTEND_URL}?auth_status=success")
            # Ensure the session cookie is set on the successful response
            response.set_cookie(key=SESSION_COOKIE_NAME, value=session_id, httponly=True, samesite='lax')
            return response
    except Exception as e:
        logger.error(f"HubSpot token exchange failed: {e}", exc_info=True)
        # The response is already set to the failure URL
        return response

@router.get("/api/auth/hubspot/status", summary="Check HubSpot authentication status")
async def hubspot_auth_status(request: Request):
    """
    Checks if the current user session has a valid, non-expired HubSpot token.
    """
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return {"authenticated": False}
    
    # get_valid_token will return None if the token is missing, expired and cannot be refreshed.
    token = await get_valid_token(session_id)
    return {"authenticated": token is not None}
