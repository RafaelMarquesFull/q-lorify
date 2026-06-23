"""
Orchestrator Admin Controllers.
CRUD endpoints for managing functions, clients, and viewing execution logs.
"""
import json
import uuid
import secrets
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..decorators import login_required, admin_required
from ..utils import get_db
from .sync import sync_builtin_functions, BUILTIN_FUNCTIONS


@csrf_exempt
@login_required
@admin_required
def functions(request):
    """
    CRUD for orchestrator functions.
    
    GET: List all functions
    POST: Create new function
    PATCH: Update function
    DELETE: Delete function
    """
    db = get_db()
    
    if request.method == "GET":
        try:
            # Auto-sync built-in functions on every request
            sync_builtin_functions()
            
            result = db.orchfunction.find_many(order={"name": "asc"})
            
            functions_list = []
            for f in result:
                functions_list.append({
                    "id": f.id,
                    "name": f.name,
                    "displayName": f.displayName,
                    "description": f.description,
                    "enabled": bool(f.enabled),
                    "pricePerUnit": f.pricePerUnit or 0,
                    "unitSize": f.unitSize or 1000,
                    "enrichPricePerUnit": f.enrichPricePerUnit or 0.05,
                    "requiresAi": bool(f.requiresAi),
                    "inputSchema": json.loads(f.inputSchema) if f.inputSchema else None,
                    "timeout": f.timeout,
                    "defaultModelId": f.defaultModelId,
                    "fallbackModelId": f.fallbackModelId,
                    "createdAt": str(f.createdAt) if f.createdAt else None,
                    "updatedAt": str(f.updatedAt) if f.updatedAt else None,
                })
            
            return JsonResponse(functions_list, safe=False)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            func_id = str(uuid.uuid4())
            
            db.orchfunction.create(
                data={
                    "id": func_id,
                    "name": body.get("name"),
                    "displayName": body.get("displayName", body.get("name")),
                    "description": body.get("description"),
                    "enabled": bool(body.get("enabled", True)),
                    "pricePerUnit": float(body.get("pricePerUnit", 0.0)),
                    "unitSize": int(body.get("unitSize", 1000)),
                    "enrichPricePerUnit": float(body.get("enrichPricePerUnit", 0.05)),
                    "requiresAi": bool(body.get("requiresAi", False)),
                    "inputSchema": json.dumps(body.get("inputSchema")) if body.get("inputSchema") else None,
                    "timeout": int(body.get("timeout", 30000)),
                    "defaultModelId": body.get("defaultModelId") if body.get("defaultModelId") else None
                }
            )
            
            return JsonResponse({"id": func_id, "name": body.get("name")}, status=201)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            func_id = body.get("id")
            
            if not func_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            # Build dynamic update query
            data = {}
            if "name" in body: data["name"] = body["name"]
            if "displayName" in body: data["displayName"] = body["displayName"]
            if "description" in body: data["description"] = body["description"]
            if "enabled" in body: data["enabled"] = bool(body["enabled"])
            if "pricePerUnit" in body: data["pricePerUnit"] = float(body["pricePerUnit"])
            if "unitSize" in body: data["unitSize"] = int(body["unitSize"])
            if "enrichPricePerUnit" in body: data["enrichPricePerUnit"] = float(body["enrichPricePerUnit"])
            if "requiresAi" in body: data["requiresAi"] = bool(body["requiresAi"])
            if "inputSchema" in body: data["inputSchema"] = json.dumps(body["inputSchema"]) if body["inputSchema"] else None
            if "timeout" in body: data["timeout"] = int(body["timeout"])
            if "defaultModelId" in body: data["defaultModelId"] = body["defaultModelId"] if body["defaultModelId"] else None
            if "fallbackModelId" in body: data["fallbackModelId"] = body["fallbackModelId"] if body["fallbackModelId"] else None
            
            db.orchfunction.update(where={"id": func_id}, data=data)
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            func_id = body.get("id")
            
            if not func_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            db.orchfunction.delete(where={"id": func_id})
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required
@admin_required
def clients(request):
    """
    CRUD for orchestrator clients.
    
    GET: List all clients
    POST: Create new client (generates token)
    PATCH: Update client
    DELETE: Delete client
    """
    db = get_db()
    
    if request.method == "GET":
        try:
            result = db.orchclient.find_many(order={"createdAt": "desc"})
            
            clients_list = []
            for c in result:
                clients_list.append({
                    "id": c.id,
                    "name": c.name,
                    "token": c.token[:12] + "..." if c.token else None,  # Masked
                    "enabled": bool(c.enabled),
                    "rateLimit": c.rateLimit,
                    "allowedFunctions": json.loads(c.allowedFunctions) if getattr(c, "allowedFunctions", None) else None,
                    "allowedModels": json.loads(c.allowedModels) if getattr(c, "allowedModels", None) else None,
                    "requestCount": c.requestCount,
                    "lastRequestAt": str(c.lastRequestAt) if c.lastRequestAt else None,
                    "createdAt": str(c.createdAt) if c.createdAt else None
                })
            
            return JsonResponse(clients_list, safe=False)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            client_id = str(uuid.uuid4())
            token = f"orch-{secrets.token_urlsafe(32)}"
            
            db.orchclient.create(
                data={
                    "id": client_id,
                    "name": body.get("name", "Novo Cliente"),
                    "token": token,
                    "enabled": bool(body.get("enabled", True)),
                    "rateLimit": int(body.get("rateLimit", 100)),
                    "allowedFunctions": json.dumps(body.get("allowedFunctions")) if body.get("allowedFunctions") else None,
                    "allowedModels": json.dumps(body.get("allowedModels")) if body.get("allowedModels") else None
                }
            )
            
            return JsonResponse({
                "id": client_id,
                "name": body.get("name"),
                "token": token  # Return full token only on creation
            }, status=201)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            client_id = body.get("id")
            
            if not client_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            data = {}
            if "name" in body: data["name"] = body["name"]
            if "enabled" in body: data["enabled"] = bool(body["enabled"])
            if "rateLimit" in body: data["rateLimit"] = int(body["rateLimit"])
            if "allowedFunctions" in body: data["allowedFunctions"] = json.dumps(body["allowedFunctions"]) if body["allowedFunctions"] else None
            if "allowedModels" in body: data["allowedModels"] = json.dumps(body["allowedModels"]) if body["allowedModels"] else None
            
            db.orchclient.update(where={"id": client_id}, data=data)
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            client_id = body.get("id")
            
            if not client_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            db.orchclient.delete(where={"id": client_id})
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required  
@admin_required
def executions(request):
    """
    View execution logs.
    
    GET: List recent executions (with pagination)
    """
    db = get_db()
    
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        limit = int(request.GET.get("limit", 50))
        offset = int(request.GET.get("offset", 0))
        
        result = db.orchexecution.find_many(
            order={"createdAt": "desc"},
            take=limit,
            skip=offset
        )
        
        executions_list = []
        for e in result:
            executions_list.append({
                "id": e.id,
                "clientId": e.clientId,
                "functionName": e.functionName,
                "input": json.loads(e.input) if getattr(e, "input", None) else None,
                "output": json.loads(e.output) if getattr(e, "output", None) else None,
                "success": bool(e.success),
                "usedAi": bool(e.usedAi),
                "modelUsed": e.modelUsed,
                "cost": e.cost,
                "durationMs": e.durationMs,
                "error": e.error,
                "createdAt": str(e.createdAt) if e.createdAt else None
            })
        
        # Get total count
        total = db.orchexecution.count()
        
        return JsonResponse({
            "executions": executions_list,
            "total": total,
            "limit": limit,
            "offset": offset
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
@admin_required
def regenerate_client_token(request, client_id):
    """
    Regenerate token for a client.
    
    POST: Generate new token
    """
    db = get_db()
    
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        new_token = f"orch-{secrets.token_urlsafe(32)}"
        
        db.orchclient.update(
            where={"id": client_id},
            data={"token": new_token}
        )
        
        return JsonResponse({
            "token": new_token
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
@login_required
@admin_required
def sync_functions(request):
    """
    Sync built-in functions with database.
    
    POST: Sync all built-in functions
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        sync_builtin_functions()
        
        return JsonResponse({
            "success": True,
            "message": f"Synced {len(BUILTIN_FUNCTIONS)} built-in functions"
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

