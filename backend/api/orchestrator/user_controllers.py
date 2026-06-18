"""
User Functions Controller.
Endpoints for users to manage their enabled functions and output templates.
"""
import json
import uuid
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from ..decorators import login_required
from ..utils import get_db


@csrf_exempt
@login_required
def user_functions(request):
    """
    User functions management.
    
    GET: List all available functions with user's config
    POST: Enable a function for the user
    PATCH: Update function config (template, etc)
    DELETE: Disable a function
    """
    db = get_db()
    user_id = request.user.id
    
    if request.method == "GET":
        try:
            # Get all enabled OrchFunctions
            all_functions = db.query_raw(
                'SELECT name, displayName, description, pricePerUnit, unitSize, enrichPricePerUnit, requiresAi FROM OrchFunction WHERE enabled = 1 ORDER BY name ASC'
            )
            
            # Get user's function configs
            user_configs = db.query_raw(
                'SELECT id, functionName, enabled, outputTemplate, config FROM UserFunction WHERE userId = ?',
                user_id
            )
            
            user_config_map = {}
            for uc in user_configs:
                if isinstance(uc, dict):
                    user_config_map[uc.get("functionName")] = uc
            
            result = []
            for f in all_functions:
                if isinstance(f, dict):
                    user_config = user_config_map.get(f.get("name"), {})
                    
                    result.append({
                        "name": f.get("name"),
                        "displayName": f.get("displayName"),
                        "description": f.get("description"),
                        "cost": f.get("pricePerUnit", 0.0),
                        "pricePerUnit": f.get("pricePerUnit", 0.0),
                        "requiresAi": bool(f.get("requiresAi")),
                        "enrichPricePerUnit": f.get("enrichPricePerUnit", 0.05) or 0.05,
                        "unitSize": f.get("unitSize", 1000) or 1000,
                        # User-specific config
                        "userEnabled": bool(user_config.get("enabled", False)),
                        "userConfig": {
                            "id": user_config.get("id"),
                            "outputTemplate": user_config.get("outputTemplate"),
                            "config": json.loads(user_config.get("config")) if user_config.get("config") else None
                        } if user_config else None
                    })
            

            return JsonResponse({
                "functions": result,
                "count": len(result)
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({"error": str(e)}, status=500)
    
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            function_name = body.get("functionName")
            output_template = body.get("outputTemplate")
            config = body.get("config")
            
            if not function_name:
                return JsonResponse({"error": "functionName is required"}, status=400)
            
            # Check if function exists and is enabled
            func_check = db.query_raw(
                'SELECT id FROM OrchFunction WHERE name = ? AND enabled = 1',
                function_name
            )
            if not func_check or len(func_check) == 0:
                return JsonResponse({"error": "Function not available"}, status=404)
            
            # Check if user already has this function
            existing = db.query_raw(
                'SELECT id FROM UserFunction WHERE userId = ? AND functionName = ?',
                user_id, function_name
            )
            
            if existing and len(existing) > 0:
                # Update existing
                db.execute_raw('''
                    UPDATE UserFunction 
                    SET enabled = 1, outputTemplate = ?, config = ?, updatedAt = ?
                    WHERE userId = ? AND functionName = ?
                ''',
                    output_template,
                    json.dumps(config) if config else None,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    user_id,
                    function_name
                )
                return JsonResponse({"success": True, "message": "Function updated"})
            else:
                # Create new
                uf_id = str(uuid.uuid4())
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                db.execute_raw('''
                    INSERT INTO UserFunction 
                    (id, userId, functionName, enabled, outputTemplate, config, createdAt, updatedAt)
                    VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                ''',
                    uf_id,
                    user_id,
                    function_name,
                    output_template,
                    json.dumps(config) if config else None,
                    now,
                    now
                )
                return JsonResponse({"success": True, "id": uf_id}, status=201)
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            function_name = body.get("functionName")
            
            if not function_name:
                return JsonResponse({"error": "functionName is required"}, status=400)
            
            updates = []
            params = []
            
            if "enabled" in body:
                updates.append("enabled = ?")
                params.append(1 if body["enabled"] else 0)
            if "outputTemplate" in body:
                updates.append("outputTemplate = ?")
                params.append(body["outputTemplate"])
            if "config" in body:
                updates.append("config = ?")
                params.append(json.dumps(body["config"]) if body["config"] else None)
            
            updates.append("updatedAt = ?")
            params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            params.extend([user_id, function_name])
            
            query = f"UPDATE UserFunction SET {', '.join(updates)} WHERE userId = ? AND functionName = ?"
            db.execute_raw(query, *params)
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            function_name = body.get("functionName")
            
            if not function_name:
                return JsonResponse({"error": "functionName is required"}, status=400)
            
            # Just disable, don't delete (preserve template)
            db.execute_raw(
                "UPDATE UserFunction SET enabled = 0, updatedAt = ? WHERE userId = ? AND functionName = ?",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id, function_name
            )
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required
def user_function_keys(request, function_name):
    """
    Manage extraction keys for a specific function.
    
    GET: List all keys for this function
    POST: Add a new key { "key": "CEP_origem", "description": "..." }
    DELETE: Remove a key { "keyId": "..." }
    """
    db = get_db()
    user_id = request.user.id
    
    if request.method == "GET":
        try:
            keys = db.query_raw(
                'SELECT id, key, description, createdAt FROM UserFunctionKey WHERE userId = ? AND functionName = ? ORDER BY createdAt ASC',
                user_id, function_name
            )
            
            result = []
            for k in keys:
                if isinstance(k, dict):
                    result.append({
                        "id": k.get("id"),
                        "key": k.get("key"),
                        "description": k.get("description"),
                        "createdAt": k.get("createdAt")
                    })
            
            return JsonResponse({"keys": result, "count": len(result)})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            key = body.get("key")
            description = body.get("description")
            
            if not key:
                return JsonResponse({"error": "key is required"}, status=400)
            if not description:
                return JsonResponse({"error": "description is required"}, status=400)
            
            # Check if key already exists
            existing = db.query_raw(
                'SELECT id FROM UserFunctionKey WHERE userId = ? AND functionName = ? AND key = ?',
                user_id, function_name, key
            )
            
            if existing and len(existing) > 0:
                return JsonResponse({"error": "Key already exists"}, status=409)
            
            key_id = str(uuid.uuid4())
            db.execute_raw('''
                INSERT INTO UserFunctionKey (id, userId, functionName, key, description, createdAt)
                VALUES (?, ?, ?, ?, ?, ?)
            ''',
                key_id,
                user_id,
                function_name,
                key,
                description,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            
            return JsonResponse({"success": True, "id": key_id}, status=201)
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            key_id = body.get("keyId")
            
            if not key_id:
                return JsonResponse({"error": "keyId is required"}, status=400)
            
            db.execute_raw(
                'DELETE FROM UserFunctionKey WHERE id = ? AND userId = ?',
                key_id, user_id
            )
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

