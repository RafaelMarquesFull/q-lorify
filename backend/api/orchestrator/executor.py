"""
Safe Executor for Orchestrator.
Executes deterministic functions with timeout and error handling.
"""
import json
import time
import uuid
import concurrent.futures
from datetime import datetime
from typing import Any, Dict, Tuple, Optional
from .registry import get_function, is_function_registered
from ..utils import get_db


def execute_function(
    function_name: str,
    content: str,
    params: Dict[str, Any],
    timeout_ms: int = 30000
) -> Tuple[bool, Any, Optional[str], int]:
    """
    Safely execute a registered function.
    
    Args:
        function_name: Name of the function to execute
        content: Main content/text to process
        params: Additional parameters
        timeout_ms: Timeout in milliseconds
    
    Returns:
        (success, result, error, duration_ms)
    """
    start_time = time.time()
    
    # Get function from registry
    func = get_function(function_name)
    
    if not func:
        duration = int((time.time() - start_time) * 1000)
        return False, None, f"Function '{function_name}' not found in registry", duration
    
    # Execute with timeout
    timeout_seconds = timeout_ms / 1000
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            # Pass content as first positional arg, rest as kwargs
            future = executor.submit(func, content, **params)
            
            try:
                result = future.result(timeout=timeout_seconds)
                duration = int((time.time() - start_time) * 1000)
                return True, result, None, duration
                
            except concurrent.futures.TimeoutError:
                duration = int((time.time() - start_time) * 1000)
                return False, None, f"Function timed out after {timeout_ms}ms", duration
                
    except Exception as e:
        duration = int((time.time() - start_time) * 1000)
        return False, None, f"Execution error: {str(e)}", duration


def log_execution(
    client_id: str,
    function_name: str,
    input_data: Dict[str, Any],
    output_data: Any,
    success: bool,
    duration_ms: int,
    cost: str = "low",
    used_ai: bool = False,
    model_used: Optional[str] = None,
    error: Optional[str] = None
):
    """Log execution to database."""
    db = get_db()
    
    try:
        exec_id = str(uuid.uuid4())
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        db.orchexecution.create(
            data={
                "id": exec_id,
                "clientId": client_id,
                "functionName": function_name,
                "input": json.dumps(input_data),
                "output": json.dumps(output_data) if output_data else None,
                "success": success,
                "usedAi": used_ai,
                "modelUsed": model_used,
                "cost": cost,
                "durationMs": duration_ms,
                "error": error
            }
        )
    except Exception as e:
        print(f"Failed to log execution: {e}")


def check_rate_limit(client_id: str) -> Tuple[bool, Optional[str]]:
    """
    Check if client is within rate limits.
    
    Returns:
        (allowed, error_message)
    """
    db = get_db()
    
    try:
        # Get client rate limit and request count
        client = db.orchclient.find_first(
            where={"id": client_id}
        )
        
        if not client:
            return False, "Client not found"
        
        rate_limit = client.rateLimit
        request_count = client.requestCount
        last_request = client.lastRequestAt
        
        # Reset count if more than 1 minute since last request
        from datetime import timedelta
        
        should_reset = False
        if last_request:
            try:
                # Parse the datetime (already a datetime object in Prisma ORM)
                if isinstance(last_request, str):
                    last_dt = datetime.fromisoformat(last_request.replace('Z', '+00:00'))
                else:
                    last_dt = last_request
                    
                if datetime.now(last_dt.tzinfo) - last_dt > timedelta(minutes=1):
                    should_reset = True
            except:
                should_reset = True
        else:
            should_reset = True
        
        if should_reset:
            request_count = 0
        
        if request_count >= rate_limit:
            return False, f"Rate limit exceeded ({rate_limit} requests/minute)"
        
        # Increment request count
        db.orchclient.update(
            where={"id": client_id},
            data={
                "requestCount": request_count + 1,
                "lastRequestAt": datetime.utcnow()
            }
        )
        
        return True, None
        
    except Exception as e:
        print(f"Rate limit check error: {e}")
        return True, None  # Allow on error (fail open for now)
