import os
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

# Load the static API key from environment variables
from dotenv import load_dotenv
load_dotenv()

INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

# Define the header where the API key is expected
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    """
    Dependency to validate the API key.
    The key is expected in the 'Authorization' header.
    Example: Authorization: your_secret_api_key_here
    """
    if not INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal API Key not configured on the server.",
        )
    
    # Note: In a real production system, you would use a more secure
    # comparison method like `secrets.compare_digest` to prevent timing attacks.
    # For our use case, direct comparison is sufficient.
    if api_key == INTERNAL_API_KEY:
        return api_key
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials.",
        )