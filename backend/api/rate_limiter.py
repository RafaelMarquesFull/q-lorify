"""
Rate Limiter for AI Models

Implements sliding window rate limiting per model per user.
NOTE: In-memory storage — suitable for single-process dev.
For production (multi-process), swap to Redis-backed storage
while keeping the same public interface.
"""
import time
from collections import defaultdict
from threading import Lock

# Storage: {model_id: {user_id: [timestamps]}}
_rate_limit_storage = defaultdict(lambda: defaultdict(list))
_storage_lock = Lock()


def check_rate_limit(model_id: str, user_id: str, rpm_limit: int) -> tuple[bool, int]:
    """
    Check if request is within rate limit.
    
    Args:
        model_id: The AI model ID
        user_id: The user making the request
        rpm_limit: Requests per minute limit
    
    Returns:
        (allowed, remaining): Tuple of whether request is allowed and remaining requests
    """
    if rpm_limit <= 0:
        return True, 999  # No limit
    
    current_time = time.time()
    window_start = current_time - 60  # 1 minute window
    
    with _storage_lock:
        # Get user's requests for this model
        user_requests = _rate_limit_storage[model_id][user_id]
        
        # Remove old timestamps outside the window
        user_requests[:] = [ts for ts in user_requests if ts > window_start]
        
        # Check if under limit
        current_count = len(user_requests)
        remaining = max(0, rpm_limit - current_count)
        
        if current_count < rpm_limit:
            # Add this request
            user_requests.append(current_time)
            return True, remaining - 1
        else:
            return False, 0


def get_rate_limit_headers(model_id: str, user_id: str, rpm_limit: int) -> dict:
    """
    Get rate limit headers for response.
    """
    current_time = time.time()
    window_start = current_time - 60
    
    with _storage_lock:
        user_requests = _rate_limit_storage[model_id][user_id]
        user_requests[:] = [ts for ts in user_requests if ts > window_start]
        current_count = len(user_requests)
        remaining = max(0, rpm_limit - current_count)
        
        # Calculate reset time (oldest request + 60 seconds)
        if user_requests:
            reset_time = int(min(user_requests) + 60)
        else:
            reset_time = int(current_time + 60)
    
    return {
        "X-RateLimit-Limit": str(rpm_limit),
        "X-RateLimit-Remaining": str(remaining),
        "X-RateLimit-Reset": str(reset_time),
    }


def clear_user_limits(user_id: str):
    """Clear all rate limits for a user (for testing)."""
    with _storage_lock:
        for model_requests in _rate_limit_storage.values():
            if user_id in model_requests:
                del model_requests[user_id]
