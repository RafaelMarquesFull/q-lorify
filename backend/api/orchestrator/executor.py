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
        
        db.execute_raw('''
            INSERT INTO OrchExecution 
            (id, clientId, functionName, input, output, success, usedAi, modelUsed, cost, durationMs, error, createdAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
            exec_id,
            client_id,
            function_name,
            json.dumps(input_data),
            json.dumps(output_data) if output_data else None,
            1 if success else 0,
            1 if used_ai else 0,
            model_used,
            cost,
            duration_ms,
            error,
            now
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
        result = db.query_raw(
            'SELECT rateLimit, requestCount, lastRequestAt FROM OrchClient WHERE id = ?',
            client_id
        )
        
        if not result:
            return False, "Client not found"
        
        client = result[0] if isinstance(result[0], dict) else {}
        rate_limit = client.get("rateLimit", 100)
        request_count = client.get("requestCount", 0)
        last_request = client.get("lastRequestAt")
        
        # Reset count if more than 1 minute since last request
        from datetime import timedelta
        
        should_reset = False
        if last_request:
            try:
                # Parse the datetime
                last_dt = datetime.fromisoformat(last_request.replace('Z', '+00:00'))
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
        db.execute_raw(
            "UPDATE OrchClient SET requestCount = ?, lastRequestAt = ? WHERE id = ?",
            request_count + 1,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            client_id
        )
        
        return True, None
        
    except Exception as e:
        print(f"Rate limit check error: {e}")
        return True, None  # Allow on error (fail open for now)
