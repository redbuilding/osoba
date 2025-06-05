import httpx

async def retrieve_oauth_token_metadata(token: str) -> dict:
    """
    Retrieve OAuth token metadata from HubSpot.

    :param token: The OAuth access token to retrieve metadata for.
    :return: The metadata associated with the OAuth token or an error dictionary.
    """
    base_url = 'https://api.hubapi.com'
    url = f"{base_url}/oauth/v1/access-tokens/{token}"
    headers = {
        'Accept': 'application/json'
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
        
        response.raise_for_status()  # Raises an HTTPStatusError for bad responses (4XX or 5XX)
        return response.json()
    except httpx.HTTPStatusError as e:
        error_message_for_log = f"Error retrieving OAuth token metadata: Status {e.response.status_code}"
        try:
            error_data = e.response.json()
            # Attempt to extract more specific error message from HubSpot's response
            if "message" in error_data: 
                 error_message_for_log = f"{error_message_for_log} - HubSpot Message: {error_data['message']}"
        except Exception: 
            error_data = {'error_description': e.response.text if e.response.text else "Unknown API error from HubSpot"}
        
        print(f"{error_message_for_log} - Full Details: {error_data}")
        return {
            "error": "An error occurred while retrieving OAuth token metadata from HubSpot.",
            "details": error_data,
            "status_code": e.response.status_code
        }
    except httpx.RequestError as e: # Covers network errors, DNS, timeout before response
        print(f"RequestError while contacting HubSpot for token metadata: {e}")
        return {
            "error": "A network or request error occurred while contacting HubSpot.",
            "details": str(e)
        }
    except Exception as e: # Catch-all for any other unexpected errors
        print(f"An unexpected error occurred in retrieve_oauth_token_metadata: {e}")
        return {
            "error": "An unexpected server-side error occurred.",
            "details": str(e)
        }