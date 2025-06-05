import os
import httpx
from typing import Dict, Optional, Any
from mcp.server.fastmcp import FastMCP
# from dotenv import load_dotenv # Optional: for using .env file

# Initialize FastMCP
mcp = FastMCP("HubspotUpdateMarketingEmailServer")

@mcp.tool()
async def update_hubspot_marketing_email(
    emailId: str,
    emailData: Dict[str, Any], # More specific type hint for emailData
    archived: Optional[bool] = False # Default to False as per common API design
) -> Dict[str, Any]:
    """
    Update a marketing email in HubSpot. Allows modifying various properties of an existing email
    and optionally archiving or unarchiving it.

    :param emailId: The ID of the marketing email to update. This is a required parameter.
    :param emailData: A dictionary containing the properties of the email to update.
                      For example, {"name": "New Email Name", "subject": "Updated Subject Line"}.
                      Refer to HubSpot API documentation for available fields.
    :param archived: Specifies if the context of the operation includes archived emails or if the email
                     should be archived/unarchived. This is appended as a query parameter.
                     Set to True to archive, False to unarchive or operate on unarchived emails.
    :return: The HubSpot API response for the email update operation or an error dictionary.
    """
    # Uncomment the next line if you are using python-dotenv and a .env file
    # load_dotenv() 
    api_key = os.getenv("HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY")
    
    if not api_key:
        error_msg = "Error: HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY not found in environment variables."
        print(error_msg) # Log to server console (stderr for MCP)
        return {"error": "Configuration error: HubSpot API key not set.", "details": error_msg}

    base_url = 'https://api.hubapi.com'
    url = f"{base_url}/marketing/v3/emails/{emailId}"
    
    # As per the JS snippet for this specific tool provided in added_context.txt,
    # 'Authorization': `Bearer ${HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY}` is used.
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {api_key}' 
    }

    # Prepare query parameters
    # The JS code: `if (archived) { url.searchParams.append('archived', archived.toString()); }`
    # This means the 'archived' parameter is only added if it's true or explicitly provided.
    # If `archived` is None or False (default), it might not be added in some JS interpretations.
    # However, to match `archived.toString()` for a boolean, it will be 'true' or 'false'.
    # Let's consistently pass it as a string 'true' or 'false'.
    query_params: Dict[str, str] = {}
    if archived is not None: # Explicitly handle if archived is passed
        query_params['archived'] = str(archived).lower()
    # If archived is False (default Python value), it will be 'false'.
    # If not provided (archived is False by default), it will set {'archived': 'false'}
    # If the API means "only add ?archived=true if true, otherwise no param", then logic needs adjustment.
    # Given `archived.toString()` on a boolean, it strongly implies it's always present if the var is defined.
    # The JS tool parameter definition indicates 'archived' is optional, defaulting to false.
    # So, we will always include it, which matches the Python function's Optional[bool] = False.

    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(url, headers=headers, params=query_params, json=emailData)
        
        # Try to parse JSON response, HubSpot usually returns JSON for errors too
        try:
            response_data = response.json()
        except Exception: # If response is not JSON (e.g., empty or malformed)
            response_data = {"raw_response": response.text, "status_code": response.status_code}

        if not response.is_success: # Checks for 2xx status codes
            error_detail = response_data.get("message", response.text) if isinstance(response_data, dict) else response.text
            error_log_msg = f"HubSpot API Error: Status {response.status_code} - EmailID: {emailId} - Detail: {error_detail} - Full Response: {response_data}"
            print(error_log_msg) # Log to server console
            return {
                "error": f"Failed to update marketing email. HubSpot API returned status {response.status_code}.",
                "details": response_data, # Contains the full error from HubSpot if JSON
                "status_code": response.status_code
            }
        return response_data
    except httpx.RequestError as e:
        error_message = f"HTTP Request error when trying to update marketing email {emailId}: {e}"
        print(error_message) # Log to server console
        return {"error": "Network or request error occurred while contacting HubSpot.", "details": str(e)}
    except Exception as e:
        error_message = f"An unexpected error occurred during HubSpot marketing email update for {emailId}: {e}"
        print(error_message) # Log to server console
        return {"error": "An unexpected server-side error occurred.", "details": str(e)}

# Run the server
if __name__ == "__main__":
    # Uncomment the next line if you are using python-dotenv and a .env file for HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY
    # from dotenv import load_dotenv
    # load_dotenv() 
    
    print("Starting HubSpot Update Marketing Email MCP Server...")
    print("Ensure HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY environment variable is set.")
    
    # For stdio transport (default for quickstart and simplicity with Claude Desktop):
    mcp.run(transport='stdio')
    
    # For HTTP transport (example, if you need to access it over network):
    # from mcp import transports
    # print("Attempting to run on HTTP transport at 0.0.0.0:8004")
    # mcp.run(transport=transports.Http(host="0.0.0.0", port=8004)) # Choose an appropriate port