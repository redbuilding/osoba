import os
import httpx
import urllib.parse
import logging
import sys
from typing import Dict, Optional, Any, List

from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

# --- Logger Setup ---
script_logger = logging.getLogger("server_hubspot_script")
script_logger.setLevel(logging.INFO) # Set to DEBUG for more detailed logs
if not script_logger.hasHandlers():
    stderr_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [SERVER_HUBSPOT] %(message)s')
    stderr_handler.setFormatter(formatter)
    script_logger.addHandler(stderr_handler)
    script_logger.propagate = False

script_logger.info(f"Script starting. Python Executable: {sys.executable}")
script_logger.info(f"Current Working Directory (CWD): {os.getcwd()}")

# --- Environment Variable Loading ---
dotenv_path = find_dotenv(usecwd=False, raise_error_if_not_found=False)
if dotenv_path:
    script_logger.info(f"Loading .env file from: {dotenv_path}")
    load_dotenv(dotenv_path)
else:
    script_logger.warning("No .env file found by find_dotenv(). Relying on default load_dotenv() or existing environment variables.")
    load_dotenv()

HUBSPOT_API_KEY = os.getenv("HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY")
if HUBSPOT_API_KEY and len(HUBSPOT_API_KEY) > 5:
    script_logger.info(f"HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY found (length: {len(HUBSPOT_API_KEY)}).")
else:
    # This key is used by create_hubspot_marketing_email and update_hubspot_marketing_email
    script_logger.warning("HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY environment variable NOT FOUND or is too short. Some tools may not function.")
    # Not raising a critical error as some tools (OAuth related) might not need this specific key.

HUBSPOT_BASE_URL = 'https://api.hubapi.com'
script_logger.info("Environment variables processed.")

# --- FastMCP Instance ---
mcp = FastMCP(
    name="HubspotServer",
    version="0.1.0",
    display_name="HubSpot Integration Server",
    description="Provides tools to interact with the HubSpot API.",
)
script_logger.info("FastMCP instance created for HubSpot.")

# --- Pydantic Models for create_hubspot_marketing_email ---
class ContentArgs(BaseModel):
    templatePath: str
    plainTextVersion: str

class FromArgs(BaseModel):
    fromName: str
    replyTo: str 
    customReplyTo: Optional[str] = None

class ContactListsArgs(BaseModel):
    include: List[int]
    exclude: List[int]

class ToArgs(BaseModel):
    contactLists: ContactListsArgs

script_logger.info("Pydantic models for HubSpot tools defined.")


# --- Tool Definitions ---

@mcp.tool()
async def refresh_hubspot_access_token(
    grant_type: str,
    code: str, # Required if grant_type is 'authorization_code'
    redirect_uri: str, # Required if grant_type is 'authorization_code'
    client_id: str,
    client_secret: str,
    refresh_token: str # Required if grant_type is 'refresh_token'
) -> dict:
    """
    Refresh an access token or obtain an access token using an authorization code for HubSpot OAuth.

    :param grant_type: The type of grant being requested. (e.g., 'authorization_code', 'refresh_token')
    :param code: The authorization code received from the initial OAuth request.
    :param redirect_uri: The redirect URI used in the initial request.
    :param client_id: The client ID of your HubSpot app.
    :param client_secret: The client secret of your HubSpot app.
    :param refresh_token: The refresh token to obtain a new access token.
    :return: The result of the token operation, including access_token, refresh_token, expires_in, etc., or an error dictionary.
    """
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json'
    }
    payload = {
        'grant_type': grant_type,
        'client_id': client_id,
        'client_secret': client_secret,
    }

    if grant_type == 'authorization_code':
        if not code or not redirect_uri:
            msg = "For 'authorization_code' grant_type, 'code' and 'redirect_uri' are required."
            script_logger.error(msg)
            return {"error": "Missing parameters for grant_type.", "details": msg}
        payload['code'] = code
        payload['redirect_uri'] = redirect_uri
    elif grant_type == 'refresh_token':
        if not refresh_token:
            msg = "For 'refresh_token' grant_type, 'refresh_token' is required."
            script_logger.error(msg)
            return {"error": "Missing parameters for grant_type.", "details": msg}
        payload['refresh_token'] = refresh_token
    else:
        msg = "Invalid grant_type specified. Must be 'authorization_code' or 'refresh_token'."
        script_logger.error(msg)
        return {"error": "Invalid grant_type.", "details": msg}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{HUBSPOT_BASE_URL}/oauth/v1/token", headers=headers, data=payload)
        
        response.raise_for_status() 
        return response.json()
    except httpx.HTTPStatusError as e:
        error_message = f"Error processing token request: Status {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "message" in error_data:
                 error_message = error_data["message"]
            elif "error_description" in error_data:
                 error_message = error_data["error_description"]
        except Exception:
            error_data = {'error_description': e.response.text if e.response.text else "Unknown API error"}
        
        script_logger.error(f"{error_message} - Details: {error_data}", exc_info=True)
        return {"error": "An error occurred while processing the HubSpot token request.", "details": error_data, "status_code": e.response.status_code}
    except httpx.RequestError as e:
        script_logger.error(f"RequestError during HubSpot token request: {e}", exc_info=True)
        return {"error": "A network or request error occurred while contacting HubSpot.", "details": str(e)}
    except Exception as e:
        script_logger.exception(f"Unexpected error during HubSpot token request: {e}")
        return {"error": "An unexpected server-side error occurred.", "details": str(e)}

script_logger.info("Tool 'refresh_hubspot_access_token' defined.")


@mcp.tool()
async def retrieve_oauth_token_metadata(token: str) -> dict:
    """
    Retrieve OAuth token metadata from HubSpot.

    :param token: The OAuth access token to retrieve metadata for.
    :return: The metadata associated with the OAuth token or an error dictionary.
    """
    url = f"{HUBSPOT_BASE_URL}/oauth/v1/access-tokens/{token}"
    headers = {'Accept': 'application/json'}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        error_message_for_log = f"Error retrieving OAuth token metadata: Status {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "message" in error_data: 
                 error_message_for_log = f"{error_message_for_log} - HubSpot Message: {error_data['message']}"
        except Exception: 
            error_data = {'error_description': e.response.text if e.response.text else "Unknown API error from HubSpot"}
        
        script_logger.error(f"{error_message_for_log} - Full Details: {error_data}", exc_info=True)
        return {"error": "An error occurred while retrieving OAuth token metadata from HubSpot.", "details": error_data, "status_code": e.response.status_code}
    except httpx.RequestError as e:
        script_logger.error(f"RequestError for OAuth token metadata: {e}", exc_info=True)
        return {"error": "A network or request error occurred while contacting HubSpot.", "details": str(e)}
    except Exception as e:
        script_logger.exception(f"Unexpected error in retrieve_oauth_token_metadata: {e}")
        return {"error": "An unexpected server-side error occurred.", "details": str(e)}

script_logger.info("Tool 'retrieve_oauth_token_metadata' defined.")


@mcp.tool()
async def retrieve_refresh_token_metadata(token: str) -> dict:
    """
    Retrieve metadata for a given refresh token from HubSpot.

    :param token: The refresh token to retrieve metadata for.
    :return: The metadata associated with the refresh token or an error dictionary.
    """
    encoded_token = urllib.parse.quote(token, safe='')
    url = f"{HUBSPOT_BASE_URL}/oauth/v1/refresh-tokens/{encoded_token}"
    headers = {'Accept': 'application/json'}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        error_message_log = f"Error retrieving refresh token metadata: Status {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "message" in error_data:
                 error_message_log = f"{error_message_log} - HubSpot Message: {error_data['message']}"
        except Exception:
            error_data = {'error_description': e.response.text if e.response.text else "Unknown API error"}
        
        script_logger.error(f"{error_message_log} - Details: {error_data}", exc_info=True)
        return {"error": "An error occurred while retrieving refresh token metadata from HubSpot.", "details": error_data, "status_code": e.response.status_code}
    except httpx.RequestError as e:
        script_logger.error(f"RequestError for refresh token metadata: {e}", exc_info=True)
        return {"error": "A network or request error occurred while contacting HubSpot.", "details": str(e)}
    except Exception as e:
        script_logger.exception(f"Unexpected error in retrieve_refresh_token_metadata: {e}")
        return {"error": "An unexpected server-side error occurred.", "details": str(e)}

script_logger.info("Tool 'retrieve_refresh_token_metadata' defined.")


@mcp.tool()
async def create_hubspot_marketing_email(
    content: ContentArgs,
    from_sender: FromArgs,
    name: str,
    subject: str,
    to_recipients: ToArgs,
    sendOnPublish: Optional[bool] = None
) -> dict:
    """
    Create a new marketing email in HubSpot.

    :param content: Content details for the email.
    :param from_sender: Sender details.
    :param name: The internal name for this marketing email.
    :param subject: The subject line of the email.
    :param to_recipients: Specifies contact lists to include/exclude.
    :param sendOnPublish: If true, send immediately after publishing.
    :return: HubSpot API response or an error dictionary.
    """
    if not HUBSPOT_API_KEY:
        msg = "HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY not configured. Cannot create marketing email."
        script_logger.error(msg)
        return {"error": "Configuration error", "details": msg}

    url = f"{HUBSPOT_BASE_URL}/marketing/v3/emails/" 
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'private-app-legacy': HUBSPOT_API_KEY # Specific header for this tool/API
    }
    payload = {
        "content": content.model_dump(),
        "from": from_sender.model_dump(),
        "name": name,
        "subject": subject,
        "to": to_recipients.model_dump(),
    }
    if sendOnPublish is not None:
        payload["sendOnPublish"] = sendOnPublish
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
        
        try:
            response_data = response.json()
        except Exception:
            response_data = {"raw_response": response.text, "status_code": response.status_code}

        if not response.is_success:
            error_detail = response_data.get("message", response.text) if isinstance(response_data, dict) else response.text
            script_logger.error(f"HubSpot API Error (Create Email): Status {response.status_code} - Detail: {error_detail} - Full Response: {response_data}", exc_info=True)
            return {"error": f"Failed to create marketing email. HubSpot API returned status {response.status_code}.", "details": response_data, "status_code": response.status_code}
        return response_data
    except httpx.RequestError as e:
        script_logger.error(f"RequestError creating marketing email: {e}", exc_info=True)
        return {"error": "Network or request error occurred while contacting HubSpot.", "details": str(e)}
    except Exception as e:
        script_logger.exception(f"Unexpected error creating HubSpot marketing email: {e}")
        return {"error": "An unexpected server-side error occurred.", "details": str(e)}

script_logger.info("Tool 'create_hubspot_marketing_email' defined.")


@mcp.tool()
async def update_hubspot_marketing_email(
    emailId: str,
    emailData: Dict[str, Any],
    archived: Optional[bool] = False
) -> Dict[str, Any]:
    """
    Update a marketing email in HubSpot.

    :param emailId: The ID of the marketing email to update.
    :param emailData: Dictionary of email properties to update.
    :param archived: Specifies if the operation includes archived emails or if the email should be archived/unarchived.
    :return: HubSpot API response or an error dictionary.
    """
    if not HUBSPOT_API_KEY:
        msg = "HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY not configured. Cannot update marketing email."
        script_logger.error(msg)
        return {"error": "Configuration error", "details": msg}

    url = f"{HUBSPOT_BASE_URL}/marketing/v3/emails/{emailId}"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {HUBSPOT_API_KEY}' # Standard Bearer token auth
    }
    query_params: Dict[str, str] = {}
    if archived is not None:
        query_params['archived'] = str(archived).lower()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(url, headers=headers, params=query_params, json=emailData)
        
        try:
            response_data = response.json()
        except Exception:
            response_data = {"raw_response": response.text, "status_code": response.status_code}

        if not response.is_success:
            error_detail = response_data.get("message", response.text) if isinstance(response_data, dict) else response.text
            script_logger.error(f"HubSpot API Error (Update Email): Status {response.status_code} - EmailID: {emailId} - Detail: {error_detail} - Full Response: {response_data}", exc_info=True)
            return {"error": f"Failed to update marketing email. HubSpot API returned status {response.status_code}.", "details": response_data, "status_code": response.status_code}
        return response_data
    except httpx.RequestError as e:
        script_logger.error(f"RequestError updating marketing email {emailId}: {e}", exc_info=True)
        return {"error": "Network or request error occurred while contacting HubSpot.", "details": str(e)}
    except Exception as e:
        script_logger.exception(f"Unexpected error updating HubSpot marketing email {emailId}: {e}")
        return {"error": "An unexpected server-side error occurred.", "details": str(e)}

script_logger.info("Tool 'update_hubspot_marketing_email' defined.")


# --- Main Execution Block ---
if __name__ == "__main__":
    script_logger.info("Starting HubSpot MCP Server directly...")
    script_logger.info("Ensure HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY (and any other necessary client IDs/secrets for OAuth tools) environment variable(s) are set if you intend to use all tools.")
    script_logger.info("This FastMCP server can also be run using 'fastmcp dev server_hubspot.py' for development.")
    
    # For stdio transport (default for quickstart and simplicity):
    mcp.run(transport='stdio')
    
    # Example for HTTP transport (if you need to access it over network):
    # from mcp import transports
    # script_logger.info("Attempting to run on HTTP transport at 0.0.0.0:8000") # Choose an appropriate port
    # mcp.run(transport=transports.Http(host="0.0.0.0", port=8000))
