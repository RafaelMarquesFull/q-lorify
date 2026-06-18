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
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute_raw('''
                INSERT INTO OrchFunction 
                (id, name, displayName, description, enabled, pricePerUnit, unitSize, enrichPricePerUnit, requiresAi, inputSchema, timeout, defaultModelId, createdAt, updatedAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
                func_id,
                body.get("name"),
                body.get("displayName", body.get("name")),
                body.get("description"),
                1 if body.get("enabled", True) else 0,
                body.get("pricePerUnit", 0.0),
                body.get("unitSize", 1000),
                body.get("enrichPricePerUnit", 0.05),
                1 if body.get("requiresAi", False) else 0,
                json.dumps(body.get("inputSchema")) if body.get("inputSchema") else None,
                body.get("timeout", 30000),
                body.get("defaultModelId") if body.get("defaultModelId") else None,
                now,
                now
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
            updates = []
            params = []
            
            if "name" in body:
                updates.append("name = ?")
                params.append(body["name"])
            if "displayName" in body:
                updates.append("displayName = ?")
                params.append(body["displayName"])
            if "description" in body:
                updates.append("description = ?")
                params.append(body["description"])
            if "enabled" in body:
                updates.append("enabled = ?")
                params.append(1 if body["enabled"] else 0)
            if "pricePerUnit" in body:
                updates.append("pricePerUnit = ?")
                params.append(body["pricePerUnit"])
            if "unitSize" in body:
                updates.append("unitSize = ?")
                params.append(body["unitSize"])
            if "enrichPricePerUnit" in body:
                updates.append("enrichPricePerUnit = ?")
                params.append(body["enrichPricePerUnit"])
            if "requiresAi" in body:
                updates.append("requiresAi = ?")
                params.append(1 if body["requiresAi"] else 0)
            if "inputSchema" in body:
                updates.append("inputSchema = ?")
                params.append(json.dumps(body["inputSchema"]) if body["inputSchema"] else None)
            if "timeout" in body:
                updates.append("timeout = ?")
                params.append(body["timeout"])
            if "defaultModelId" in body:
                updates.append("defaultModelId = ?")
                params.append(body["defaultModelId"] if body["defaultModelId"] else None)
            if "fallbackModelId" in body:
                updates.append("fallbackModelId = ?")
                params.append(body["fallbackModelId"] if body["fallbackModelId"] else None)
            
            updates.append("updatedAt = ?")
            params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            params.append(func_id)
            
            query = f"UPDATE OrchFunction SET {', '.join(updates)} WHERE id = ?"
            db.execute_raw(query, *params)
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            func_id = body.get("id")
            
            if not func_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            db.execute_raw("DELETE FROM OrchFunction WHERE id = ?", func_id)
            
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
            result = db.query_raw(
                'SELECT id, name, token, enabled, rateLimit, allowedFunctions, allowedModels, requestCount, lastRequestAt, createdAt FROM OrchClient ORDER BY createdAt DESC'
            )
            
            clients_list = []
            for c in result:
                if isinstance(c, dict):
                    clients_list.append({
                        "id": c.get("id"),
                        "name": c.get("name"),
                        "token": c.get("token")[:12] + "..." if c.get("token") else None,  # Masked
                        "enabled": bool(c.get("enabled")),
                        "rateLimit": c.get("rateLimit"),
                        "allowedFunctions": json.loads(c.get("allowedFunctions")) if c.get("allowedFunctions") else None,
                        "allowedModels": json.loads(c.get("allowedModels")) if c.get("allowedModels") else None,
                        "requestCount": c.get("requestCount"),
                        "lastRequestAt": c.get("lastRequestAt"),
                        "createdAt": c.get("createdAt")
                    })
            
            return JsonResponse(clients_list, safe=False)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            client_id = str(uuid.uuid4())
            token = f"orch-{secrets.token_urlsafe(32)}"
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute_raw('''
                INSERT INTO OrchClient 
                (id, name, token, enabled, rateLimit, allowedFunctions, allowedModels, requestCount, createdAt)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            ''',
                client_id,
                body.get("name", "Novo Cliente"),
                token,
                1 if body.get("enabled", True) else 0,
                body.get("rateLimit", 100),
                json.dumps(body.get("allowedFunctions")) if body.get("allowedFunctions") else None,
                json.dumps(body.get("allowedModels")) if body.get("allowedModels") else None,
                now
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
            
            updates = []
            params = []
            
            if "name" in body:
                updates.append("name = ?")
                params.append(body["name"])
            if "enabled" in body:
                updates.append("enabled = ?")
                params.append(1 if body["enabled"] else 0)
            if "rateLimit" in body:
                updates.append("rateLimit = ?")
                params.append(body["rateLimit"])
            if "allowedFunctions" in body:
                updates.append("allowedFunctions = ?")
                params.append(json.dumps(body["allowedFunctions"]) if body["allowedFunctions"] else None)
            if "allowedModels" in body:
                updates.append("allowedModels = ?")
                params.append(json.dumps(body["allowedModels"]) if body["allowedModels"] else None)
            
            params.append(client_id)
            
            query = f"UPDATE OrchClient SET {', '.join(updates)} WHERE id = ?"
            db.execute_raw(query, *params)
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            client_id = body.get("id")
            
            if not client_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            db.execute_raw("DELETE FROM OrchClient WHERE id = ?", client_id)
            
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
        
        result = db.query_raw(
            'SELECT id, clientId, userId, functionName, input, output, success, usedAi, modelUsed, cost, durationMs, error, createdAt FROM OrchExecution ORDER BY createdAt DESC LIMIT ? OFFSET ?',
            limit, offset
        )
        
        executions_list = []
        for e in result:
            if isinstance(e, dict):
                executions_list.append({
                    "id": e.get("id"),
                    "clientId": e.get("clientId"),
                    "functionName": e.get("functionName"),
                    "input": json.loads(e.get("input")) if e.get("input") else None,
                    "output": json.loads(e.get("output")) if e.get("output") else None,
                    "success": bool(e.get("success")),
                    "usedAi": bool(e.get("usedAi")),
                    "modelUsed": e.get("modelUsed"),
                    "cost": e.get("cost"),
                    "durationMs": e.get("durationMs"),
                    "error": e.get("error"),
                    "createdAt": e.get("createdAt")
                })
        
        # Get total count
        count_result = db.query_raw('SELECT COUNT(*) as total FROM OrchExecution')
        total = count_result[0].get("total", 0) if count_result and isinstance(count_result[0], dict) else 0
        
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
        
        db.execute_raw(
            "UPDATE OrchClient SET token = ? WHERE id = ?",
            new_token,
            client_id
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

