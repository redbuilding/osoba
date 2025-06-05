import os
import httpx
from typing import List, Optional
from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP
# from dotenv import load_dotenv # Optional: for loading .env file if you choose to use a .env file

# --- Pydantic Models (Step 2) ---
class ContentArgs(BaseModel):
    templatePath: str
    plainTextVersion: str

class FromArgs(BaseModel):
    # In HubSpot API, 'from' is an email address, 'fromName' is the display name.
    # The JS tool definition for 'from' has 'fromName' and 'replyTo'. Let's match that.
    # If the HubSpot API expects 'from' to be the email, this might need adjustment
    # based on actual API field names, but we follow the JS tool's parameter structure.
    fromName: str
    replyTo: str # This is typically an email address
    customReplyTo: Optional[str] = None # Also an email address

class ContactListsArgs(BaseModel):
    include: List[int] # List of contact list IDs
    exclude: List[int] # List of contact list IDs to exclude

class ToArgs(BaseModel):
    contactLists: ContactListsArgs

# --- MCP Server Setup (Step 4) ---
mcp = FastMCP("HubspotMarketingEmailServer")

# --- Tool Implementation (Step 3 & 5) ---
@mcp.tool()
async def create_hubspot_marketing_email(
    content: ContentArgs,
    from_sender: FromArgs, # Maps to JS 'from' which is an object
    name: str, # Internal name of the email
    subject: str, # Subject line of the email
    to_recipients: ToArgs, # Maps to JS 'to'
    sendOnPublish: Optional[bool] = None # Whether to send immediately upon publishing
) -> dict:
    """
    Create a new marketing email in HubSpot.

    :param content: Content details for the email, including templatePath and plainTextVersion.
    :param from_sender: Sender details, including fromName and replyTo email addresses.
    :param name: The internal name for this marketing email in HubSpot.
    :param subject: The subject line of the marketing email.
    :param to_recipients: Specifies the contact lists to include and exclude for sending.
    :param sendOnPublish: If true, the email will be sent immediately after publishing. Defaults to false.
    :return: The HubSpot API response for the email creation or an error dictionary.
    """
    # Uncomment the next line if you are using python-dotenv and a .env file
    # load_dotenv() 
    api_key = os.getenv("HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY")
    
    if not api_key:
        print("Error: HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY not found in environment variables.")
        return {"error": "Configuration error: HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY not set."}

    base_url = 'https://api.hubapi.com'
    # As per JS, endpoint is /marketing/v3/emails without a trailing slash for POST
    # However, it's common for POST endpoints to end with a slash.
    # Let's assume /marketing/v3/emails/ is suitable or check HubSpot docs if issues arise.
    # The JS uses `new URL(`${BASE_URL}/marketing/v3/emails`)` which does not add a trailing slash if BASE_URL has no trailing slash.
    # However, the JSON body description indicates a POST to `/marketing/v3/emails/` (with slash).
    # We'll use the one with the slash as per the tool description in the JS.
    url = f"{base_url}/marketing/v3/emails/" 
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        # The JS context for the tool shows "private-app-legacy" with the key.
        # This implies it's likely a Private App Access Token.
        'Authorization': f'Bearer {api_key}' # Standard for new private apps
        # If HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY is indeed an older API key (HAPIkey), 
        # the auth method might be different (e.g., ?hapikey=YOUR_KEY in URL, or different header).
        # The JS tool used 'private-app-legacy': api_key which is non-standard.
        # For private apps, 'Authorization: Bearer <token>' is typical.
        # Let's assume 'api_key' is a private app access token.
        # If `private-app-legacy` was a custom header expected by some proxy, that's different.
        # Given the name "HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY" it could be an old Portal API key.
        # Let's stick to 'Authorization: Bearer {api_key}' as it's the modern way for private apps.
        # If this fails, and the key is an old HAPIKey, it would be `url = f"{url}?hapikey={api_key}"`
        # and no Authorization header.
        # The JS `headers: { ..., "private-app-legacy": HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY}` is unusual.
        # Let's use the common `Authorization: Bearer <token>` and adjust if testing shows an issue.
        # UPDATE based on JS context: The JS explicitly uses: headers.append("private-app-legacy", HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY);
        # So, we must use that specific header.
    }
    # Re-evaluating headers based on the provided JS snippet for this specific tool:
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'private-app-legacy': api_key # Directly using the header name from the JS snippet
    }


    # Construct payload ensuring HubSpot expected keys ('from', 'to')
    # It's crucial that the top-level keys match HubSpot's API.
    # The Pydantic models `from_sender` and `to_recipients` are for Python ergonomics.
    # The actual payload keys should be `from` and `to` if HubSpot expects that.
    # The JS tool definition parameters: `from`, `to`. So we map back.
    payload = {
        "content": content.model_dump(),
        "from": from_sender.model_dump(), # Map Python `from_sender` to HubSpot's `from`
        "name": name,
        "subject": subject,
        "to": to_recipients.model_dump(),   # Map Python `to_recipients` to HubSpot's `to`
    }
    if sendOnPublish is not None:
        payload["sendOnPublish"] = sendOnPublish
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
        
        # Try to parse JSON in all cases, as HubSpot often returns JSON errors
        try:
            response_data = response.json()
        except Exception: # If response is not JSON
            response_data = {"raw_response": response.text}

        if not response.is_success: # Checks for 2xx status codes
            error_detail = response_data.get("message", response.text) if isinstance(response_data, dict) else response.text
            print(f"HubSpot API Error: Status {response.status_code} - Detail: {error_detail} - Full Response: {response_data}")
            return {
                "error": f"Failed to create marketing email. HubSpot API returned status {response.status_code}.",
                "details": response_data,
                "status_code": response.status_code
            }

        return response_data
    except httpx.RequestError as e:
        error_message = f"HTTP Request error when trying to create marketing email: {e}"
        print(error_message)
        return {"error": "Network or request error occurred while contacting HubSpot.", "details": str(e)}
    except Exception as e:
        error_message = f"An unexpected error occurred during HubSpot marketing email creation: {e}"
        print(error_message)
        return {"error": "An unexpected server-side error occurred.", "details": str(e)}

# --- Run Server (Step 6) ---
if __name__ == "__main__":
    # Uncomment the next line if you are using python-dotenv and a .env file
    # load_dotenv() 
    print("Starting HubSpot Marketing Email MCP Server...")
    print("Ensure HUBSPOT_PUBLIC_API_WORKSPACE_API_KEY environment variable is set.")
    # For stdio transport (default for quickstart and simplicity):
    mcp.run(transport='stdio')
    # For HTTP transport (example, if needed, ensure mcp-sdk[http] is installed):
    # from mcp import transports
    # mcp.run(transport=transports.Http(host="0.0.0.0", port=8003)) # Example port