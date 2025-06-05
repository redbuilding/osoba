# 1. Imports
from mcp.server.fastmcp import FastMCP
import httpx # or requests

# 2. Initialize FastMCP
mcp = FastMCP("HubspotToolServer")

# 3. Define the refactored tool
@mcp.tool()
async def refresh_hubspot_access_token( # Mark as async if using httpx.AsyncClient
    grant_type: str,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
    refresh_token: str
) -> dict:
    """
    Refresh an access token for HubSpot OAuth.

    :param grant_type: The type of grant being requested. (e.g., 'authorization_code', 'refresh_token')
    :param code: The authorization code received from the initial OAuth request. (Required if grant_type is 'authorization_code')
    :param redirect_uri: The redirect URI used in the initial request. (Required if grant_type is 'authorization_code')
    :param client_id: The client ID of your HubSpot app.
    :param client_secret: The client secret of your HubSpot app.
    :param refresh_token: The refresh token to obtain a new access token. (Required if grant_type is 'refresh_token')
    :return: The result of the token refresh operation, including access_token, refresh_token, expires_in, etc., or an error dictionary.
    """
    base_url = 'https://api.hubapi.com'
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
        payload['code'] = code
        payload['redirect_uri'] = redirect_uri
    elif grant_type == 'refresh_token':
        payload['refresh_token'] = refresh_token
    else:
        return {"error": "Invalid grant_type specified.", "details": "grant_type must be 'authorization_code' or 'refresh_token'."}


    try:
        # Using httpx (async version)
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{base_url}/oauth/v1/token", headers=headers, data=payload)
        
        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        return response.json()
    except httpx.HTTPStatusError as e:
        # Attempt to parse error data if possible, otherwise return a generic error
        error_message = f"Error refreshing access token: Status {e.response.status_code}"
        try:
            error_data = e.response.json()
            if "message" in error_data: # HubSpot specific error format sometimes
                 error_message = error_data["message"]
            elif "error_description" in error_data:
                 error_message = error_data["error_description"]

        except Exception:
            error_data = {'error_description': e.response.text if e.response.text else "Unknown API error"}
        
        print(f"{error_message} - Details: {error_data}")
        return {"error": "An error occurred while refreshing the HubSpot access token.", "details": error_data, "status_code": e.response.status_code}
    except httpx.RequestError as e:
        print(f"An error occurred while making the request to HubSpot: {e}")
        return {"error": "An error occurred while making the request to HubSpot.", "details": str(e)}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"error": "An unexpected error occurred while refreshing the access token.", "details": str(e)}

# 4. Run the server
if __name__ == "__main__":
    print("Starting HubSpot MCP Server...")
    # Example: mcp.run(transport='stdio')
    # For HTTP server (requires mcp-sdk[http]):
    # from mcp import transports
    # mcp.run(transport=transports.Http("0.0.0.0", 8000))
    # Defaulting to stdio for simplicity as per quickstart
    mcp.run(transport='stdio')