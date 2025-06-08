import logging
import httpx
from typing import Dict, Any, Optional
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP

# Initialize logger
logger = logging.getLogger("server_hubspot")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
logger.addHandler(handler)

# Instantiate the MCP server for business-logic tools only
mcp = FastMCP(
    name="HubspotBusinessLogic",
    version="0.1.0",
    display_name="HubSpot Business Logic Tools",
    description="Provides create/update marketing-email tools for HubSpot using a provided access token",
)

# Pydantic models for request validation
ContentDict = Dict[str, Any]

class ContentArgs(BaseModel):
    templatePath: str
    plainTextVersion: str

class FromArgs(BaseModel):
    fromName: str
    replyTo: str
    customReplyTo: Optional[str] = None

class ContactListsArgs(BaseModel):
    include: list[int]
    exclude: list[int]

class ToArgs(BaseModel):
    contactLists: ContactListsArgs


@mcp.tool()
async def create_hubspot_marketing_email(
    access_token: str,
    content: ContentArgs,
    from_sender: FromArgs,
    name: str,
    subject: str,
    to_recipients: ToArgs,
    sendOnPublish: Optional[bool] = None
) -> dict:
    """
    Create a new marketing email in HubSpot. Requires a valid OAuth access token.
    """
    url = "https://api.hubapi.com/marketing/v3/emails"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    payload: ContentDict = {
        "content": content.model_dump(),
        "from": from_sender.model_dump(),
        "name": name,
        "subject": subject,
        "to": to_recipients.model_dump(),
    }
    if sendOnPublish is not None:
        payload["sendOnPublish"] = sendOnPublish

    # Log request details
    logger.info(f"[create] URL: {url}")
    logger.debug(f"[create] Headers: {headers}")
    logger.debug(f"[create] Payload: {payload}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            # Log response details
            logger.info(f"[create] Response status: {response.status_code}")
            logger.debug(f"[create] Response body: {response.text}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        # Log HTTP errors specifically
        status = e.response.status_code
        body = e.response.text
        logger.error(f"[create] HTTP error {status}: {body}")
        return {"error": "HTTP status error", "status": status, "body": body}
    except Exception as e:
        logger.error(f"[create] Unexpected error: {e}")
        return {"error": "Exception", "details": str(e)}


@mcp.tool()
async def update_hubspot_marketing_email(
    access_token: str,
    emailId: str,
    emailData: Dict[str, Any],
    archived: Optional[bool] = False
) -> Dict[str, Any]:
    """
    Update or archive an existing marketing email in HubSpot. Requires a valid OAuth access token.
    """
    url = (
        f"https://api.hubapi.com/marketing/v3/emails/{emailId}"
        f"?archived={'true' if archived else 'false'}"
    )
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    # Log request details
    logger.info(f"[update] URL: {url}")
    logger.debug(f"[update] Headers: {headers}")
    logger.debug(f"[update] Payload: {emailData}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.patch(url, json=emailData, headers=headers, timeout=30.0)
            # Log response details
            logger.info(f"[update] Response status: {response.status_code}")
            logger.debug(f"[update] Response body: {response.text}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        body = e.response.text
        logger.error(f"[update] HTTP error {status}: {body}")
        return {"error": "HTTP status error", "status": status, "body": body}
    except Exception as e:
        logger.error(f"[update] Unexpected error: {e}")
        return {"error": "Exception", "details": str(e)}


if __name__ == "__main__":
    logger.info("Starting HubSpot business-logic MCP server...")
    mcp.run(transport='stdio')
