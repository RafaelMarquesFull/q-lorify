"""
Orchestrator Controllers.
Main endpoint for AI orchestration with deterministic functions.
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..utils import get_db
from .parser import parse_action
from .resolver import resolve_function
from .executor import execute_function, log_execution, check_rate_limit
from .registry import is_function_registered, list_functions


def authenticate_client(request):
    """
    Authenticate orchestrator client via Bearer token.
    Returns (client_id, error_response)
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, JsonResponse({
            "success": False,
            "error": "Missing or invalid Authorization header"
        }, status=401)
    
    token = auth_header.split(' ')[1]
    
    db = get_db()
    
    try:
        result = db.query_raw(
            'SELECT id, name, enabled FROM OrchClient WHERE token = ?',
            token
        )
        
        if not result or len(result) == 0:
            return None, JsonResponse({
                "success": False,
                "error": "Invalid token"
            }, status=401)
        
        client = result[0] if isinstance(result[0], dict) else {}
        
        if not client.get("enabled", False):
            return None, JsonResponse({
                "success": False,
                "error": "Client is disabled"
            }, status=403)
        
        return client.get("id"), None
        
    except Exception as e:
        return None, JsonResponse({
            "success": False,
            "error": f"Authentication error: {str(e)}"
        }, status=500)


@csrf_exempt
def execute(request):
    """
    Main orchestration endpoint.
    
    POST /ai/execute
    Authorization: Bearer {client_token}
    
    Body:
    {
        "prompt": "[ACTION:function_name param=value]\n```\ncontent here\n```"
    }
    
    Response:
    {
        "success": true,
        "action": "function_name",
        "data": { ... },
        "meta": {
            "used_ai": false,
            "model": null,
            "cost": "low",
            "duration_ms": 45
        }
    }
    """
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "error": "Method not allowed"
        }, status=405)
    
    # Authenticate client
    client_id, error_response = authenticate_client(request)
    if error_response:
        return error_response
    
    # Check rate limit
    allowed, rate_error = check_rate_limit(client_id)
    if not allowed:
        return JsonResponse({
            "success": False,
            "error": rate_error
        }, status=429)
    
    # Parse request body
    try:
        body = json.loads(request.body)
        prompt = body.get("prompt", "")
        
        if not prompt:
            return JsonResponse({
                "success": False,
                "error": "Missing 'prompt' in request body"
            }, status=400)
            
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON body"
        }, status=400)
    
    # Parse action from prompt
    action_name, params, content = parse_action(prompt)
    
    if not action_name:
        # TODO: Implement implicit mode with AI classification
        return JsonResponse({
            "success": False,
            "error": "No [ACTION:name] found in prompt. Explicit action required.",
            "hint": "Use format: [ACTION:function_name param=value]\n```\ncontent\n```"
        }, status=400)
    
    # Resolve function
    resolved, func_config, resolve_error = resolve_function(action_name, client_id)
    
    if not resolved:
        log_execution(
            client_id=client_id,
            function_name=action_name,
            input_data={"content": content, "params": params},
            output_data=None,
            success=False,
            duration_ms=0,
            error=resolve_error
        )
        return JsonResponse({
            "success": False,
            "action": action_name,
            "error": resolve_error
        }, status=403)
    
    # Check if function exists in registry
    if not is_function_registered(action_name):
        log_execution(
            client_id=client_id,
            function_name=action_name,
            input_data={"content": content, "params": params},
            output_data=None,
            success=False,
            duration_ms=0,
            error=f"Function '{action_name}' not implemented"
        )
        return JsonResponse({
            "success": False,
            "action": action_name,
            "error": f"Function '{action_name}' is registered but not implemented"
        }, status=501)
    
    # Get function config
    timeout_ms = func_config.get("timeout", 30000) if func_config else 30000
    cost = func_config.get("cost", "low") if func_config else "low"
    requires_ai = func_config.get("requiresAi", False) if func_config else False
    
    # Execute function
    success, result, error, duration_ms = execute_function(
        function_name=action_name,
        content=content,
        params=params,
        timeout_ms=timeout_ms
    )
    
    # Log execution
    log_execution(
        client_id=client_id,
        function_name=action_name,
        input_data={"content": content, "params": params},
        output_data=result,
        success=success,
        duration_ms=duration_ms,
        cost=cost,
        used_ai=False,
        error=error
    )
    
    if not success:
        return JsonResponse({
            "success": False,
            "action": action_name,
            "error": error,
            "meta": {
                "used_ai": False,
                "model": None,
                "cost": cost,
                "duration_ms": duration_ms
            }
        }, status=500)
    
    return JsonResponse({
        "success": True,
        "action": action_name,
        "data": result,
        "meta": {
            "used_ai": False,
            "model": None,
            "cost": cost,
            "duration_ms": duration_ms
        }
    })


@csrf_exempt
def list_available_functions(request):
    """
    List all available functions.
    
    GET /ai/functions
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    # Authenticate
    client_id, error_response = authenticate_client(request)
    if error_response:
        return error_response
    
    db = get_db()
    
    try:
        # Get all enabled functions
        functions = db.query_raw(
            'SELECT name, displayName, description, cost, requiresAi, inputSchema FROM OrchFunction WHERE enabled = 1'
        )
        
        result = []
        for f in functions:
            if isinstance(f, dict):
                result.append({
                    "name": f.get("name"),
                    "displayName": f.get("displayName"),
                    "description": f.get("description"),
                    "cost": f.get("cost"),
                    "requiresAi": bool(f.get("requiresAi")),
                    "inputSchema": json.loads(f.get("inputSchema")) if f.get("inputSchema") else None
                })
        
        return JsonResponse({
            "functions": result,
            "count": len(result)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
