"""
Function Resolver for Orchestrator.
Validates and resolves functions based on client permissions.
"""
import json
from typing import Optional, Dict, Any, Tuple
from ..utils import get_db


def resolve_function(
    function_name: str,
    client_id: str
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Resolve and validate a function for execution.
    
    Args:
        function_name: Name of the function to execute
        client_id: ID of the client making the request
    
    Returns:
        (success, function_config, error_message)
    """
    db = get_db()
    
    # Get function from database
    try:
        func_result = db.query_raw(
            'SELECT id, name, displayName, description, enabled, pricePerUnit, unitSize, enrichPricePerUnit, requiresAi, inputSchema, timeout, defaultModelId, fallbackModelId, createdAt, updatedAt FROM OrchFunction WHERE name = ? AND enabled = 1',
            function_name
        )
        
        if not func_result or len(func_result) == 0:
            return False, None, f"Function '{function_name}' not found or disabled"
        
        func_config = func_result[0] if isinstance(func_result[0], dict) else {}
        
    except Exception as e:
        return False, None, f"Database error: {str(e)}"
    
    # Get client and check permissions
    try:
        client_result = db.query_raw(
            'SELECT id, name, token, enabled, rateLimit, allowedFunctions, allowedModels, requestCount, lastRequestAt, createdAt FROM OrchClient WHERE id = ? AND enabled = 1',
            client_id
        )
        
        if not client_result or len(client_result) == 0:
            return False, None, "Client not found or disabled"
        
        client = client_result[0] if isinstance(client_result[0], dict) else {}
        
        # Check if client has permission to use this function
        allowed_functions = client.get("allowedFunctions")
        if allowed_functions:
            try:
                allowed_list = json.loads(allowed_functions)
                if function_name not in allowed_list:
                    return False, None, f"Client not authorized to use function '{function_name}'"
            except:
                pass  # If parsing fails, allow all
        
    except Exception as e:
        return False, None, f"Client validation error: {str(e)}"
    
    return True, func_config, None


def get_allowed_models_for_function(
    function_name: str,
    client_id: str
) -> list:
    """
    Get intersection of models allowed for function and client.
    """
    db = get_db()
    
    try:
        # Get function's allowed models
        func_result = db.query_raw(
            'SELECT allowedModels FROM OrchFunction WHERE name = ?',
            function_name
        )
        func_models = set()
        if func_result and isinstance(func_result[0], dict):
            models_str = func_result[0].get("allowedModels")
            if models_str:
                func_models = set(json.loads(models_str))
        
        # Get client's allowed models
        client_result = db.query_raw(
            'SELECT allowedModels FROM OrchClient WHERE id = ?',
            client_id
        )
        client_models = set()
        if client_result and isinstance(client_result[0], dict):
            models_str = client_result[0].get("allowedModels")
            if models_str:
                client_models = set(json.loads(models_str))
        
        # If both have restrictions, take intersection
        if func_models and client_models:
            return list(func_models & client_models)
        elif func_models:
            return list(func_models)
        elif client_models:
            return list(client_models)
        else:
            return []  # No restrictions
            
    except Exception as e:
        print(f"Error getting allowed models: {e}")
        return []
