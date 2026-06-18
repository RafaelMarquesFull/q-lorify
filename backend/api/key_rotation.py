"""
Key Rotation Service for AI Providers.
Implements round-robin selection of API keys for providers with rotation enabled.
"""
from typing import Optional
from .utils import get_db
from datetime import datetime

def get_next_api_key(provider_id: str) -> Optional[str]:
    """
    Get the next API key to use for a provider.
    
    If rotation is enabled and there are active keys, selects the one with 
    the lowest usage count (round-robin behavior).
    
    Falls back to provider.apiKey if:
    - rotationEnabled is False
    - No active ProviderApiKey entries exist
    
    Returns the API key string or None if no key available.
    """
    db = get_db()
    
    # Get provider to check rotation status
    provider = db.aiprovider.find_unique(where={"id": provider_id})
    
    if not provider:
        return None
    
    if not provider.rotationEnabled:
        # Use legacy single key
        return provider.apiKey
    
    # Get active key with lowest usage
    # We use find_first with sorting to get the candidate
    selected_key = db.providerapikey.find_first(
        where={
            "providerId": provider_id,
            "isActive": True
        },
        order={
            "usageCount": "asc"
        }
    )
    
    if not selected_key:
        # Fallback to single key if no rotation keys
        return provider.apiKey
        
    # Update usage count and lastUsedAt
    try:
        db.providerapikey.update(
            where={"id": selected_key.id},
            data={
                "usageCount": {"increment": 1},
                "lastUsedAt": datetime.utcnow()
            }
        )
    except Exception as e:
        print(f"Failed to update key usage: {e}")
    
    return selected_key.apiKey


def reset_key_usage(provider_id: str) -> None:
    """
    Reset usage counts for all keys of a provider.
    Useful for periodic resets (e.g., daily).
    """
    db = get_db()
    
    try:
        db.providerapikey.update_many(
            where={"providerId": provider_id},
            data={"usageCount": 0}
        )
    except Exception as e:
        print(f"Failed to reset key usage: {e}")
