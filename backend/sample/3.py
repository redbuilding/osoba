# 1. Imports
from mcp.server.fastmcp import FastMCP
import httpx
import urllib.parse # For URL encoding the token path variable

# 2. Initialize FastMCP
mcp = FastMCP("HubspotRefreshTokenServer")

# 3. Define the refactored tool
@mcp.tool()
async def retrieve_refresh_token_metadata(token: str) -> dict:
    """
    Retrieve metadata for a given refresh token from HubSpot.

    :param token: The refresh token to retrieve metadata for.
    :return: The metadata associated with the refresh token or an error dictionary.
    """
    base_url = 'https://api.hubapi.com'
    # Ensure the token is URL-encoded as it's part of the path
    # HubSpot refresh tokens can be long and may contain characters that need encoding.
    encoded_token = urllib.parse.quote(token, safe='')
    url = f"{base_url}/oauth/v1/refresh-tokens/{encoded_token}"
    headers = {
        'Accept': 'application/json'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        
        response.raise_for_status()  # Raises an HTTPStatusError for bad responses (4XX or 5XX)
        return response.json()
    except httpx.HTTPStatusError as e:
        error_message_log = f"Error retrieving refresh token metadata: Status {e.response.status_code}"
        try:
            error_data = e.response.json()
            # HubSpot error responses often include a 'message' field
            if "message" in error_data:
                 error_message_log = f"{error_message_log} - HubSpot Message: {error_data['message']}"
        except Exception: # If response is not JSON or 'message' key is not present
            error_data = {'error_description': e.response.text if e.response.text else "Unknown API error"}
        
        # Log to stderr for MCP server host to capture
        print(f"{error_message_log} - Details: {error_data}")
        return {
            "error": "An error occurred while retrieving refresh token metadata from HubSpot.",
            "details": error_data,
            "status_code": e.response.status_code
        }
    except httpx.RequestError as e: # Covers network errors, DNS issues, timeouts before response etc.
        error_message_log = f"RequestError while contacting HubSpot for refresh token metadata: {e}"
        print(error_message_log)
        return {
            "error": "A network or request error occurred while contacting HubSpot.",
            "details": str(e)
        }
    except Exception as e: # Catch-all for any other unexpected errors
        error_message_log = f"An unexpected error occurred in retrieve_refresh_token_metadata: {e}"
        print(error_message_log)
        return {
            "error": "An unexpected server-side error occurred.",
            "details": str(e)
        }

# 4. Run the server
if __name__ == "__main__":
    print("Starting HubSpot Refresh Token Metadata MCP Server...")
    # For stdio transport (default for quickstart and simplicity):
    mcp.run(transport='stdio')
    # For HTTP transport (example, if needed, ensure mcp-sdk[http] is installed):
    # from mcp import transports
    # mcp.run(transport=transports.Http(host="0.0.0.0", port=8002))