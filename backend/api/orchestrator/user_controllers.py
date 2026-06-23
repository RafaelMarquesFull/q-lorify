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
            all_functions = db.orchfunction.find_many(
                where={"enabled": True},
                order={"name": "asc"}
            )
            
            # Get user's function configs
            user_configs = db.userfunction.find_many(
                where={"userId": user_id}
            )
            
            user_config_map = {uc.functionName: uc for uc in user_configs}
            
            result = []
            for f in all_functions:
                user_config = user_config_map.get(f.name)
                
                result.append({
                    "name": f.name,
                    "displayName": f.displayName,
                    "description": f.description,
                    "cost": f.pricePerUnit or 0.0,
                    "pricePerUnit": f.pricePerUnit or 0.0,
                    "requiresAi": f.requiresAi,
                    "enrichPricePerUnit": f.enrichPricePerUnit or 0.05,
                    "unitSize": f.unitSize or 1000,
                    # User-specific config
                    "userEnabled": bool(user_config.enabled) if user_config else False,
                    "userConfig": {
                        "id": user_config.id,
                        "outputTemplate": user_config.outputTemplate,
                        "config": json.loads(user_config.config) if user_config.config else None
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
            func_check = db.orchfunction.find_first(
                where={"name": function_name, "enabled": True}
            )
            if not func_check:
                return JsonResponse({"error": "Function not available"}, status=404)
            
            # Check if user already has this function
            existing = db.userfunction.find_first(
                where={"userId": user_id, "functionName": function_name}
            )
            
            if existing:
                # Update existing
                db.userfunction.update(
                    where={"id": existing.id},
                    data={
                        "enabled": True,
                        "outputTemplate": output_template,
                        "config": json.dumps(config) if config else None
                    }
                )
                return JsonResponse({"success": True, "message": "Function updated"})
            else:
                # Create new
                uf_id = str(uuid.uuid4())
                db.userfunction.create(
                    data={
                        "id": uf_id,
                        "userId": user_id,
                        "functionName": function_name,
                        "enabled": True,
                        "outputTemplate": output_template,
                        "config": json.dumps(config) if config else None
                    }
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
            
            updates = {}
            if "enabled" in body:
                updates["enabled"] = bool(body["enabled"])
            if "outputTemplate" in body:
                updates["outputTemplate"] = body["outputTemplate"]
            if "config" in body:
                updates["config"] = json.dumps(body["config"]) if body["config"] else None
            
            if updates:
                # find existing first because we might not have the id directly (composite unique key userId_functionName)
                existing = db.userfunction.find_first(where={"userId": user_id, "functionName": function_name})
                if existing:
                    db.userfunction.update(where={"id": existing.id}, data=updates)
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            function_name = body.get("functionName")
            
            if not function_name:
                return JsonResponse({"error": "functionName is required"}, status=400)
            
            existing = db.userfunction.find_first(where={"userId": user_id, "functionName": function_name})
            if existing:
                db.userfunction.update(where={"id": existing.id}, data={"enabled": False})
            
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
            keys = db.userfunctionkey.find_many(
                where={"userId": user_id, "functionName": function_name},
                order={"createdAt": "asc"}
            )
            
            result = []
            for k in keys:
                result.append({
                    "id": k.id,
                    "key": k.key,
                    "description": k.description,
                    "createdAt": k.createdAt
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
            existing = db.userfunctionkey.find_first(
                where={"userId": user_id, "functionName": function_name, "key": key}
            )
            
            if existing:
                return JsonResponse({"error": "Key already exists"}, status=409)
            
            key_id = str(uuid.uuid4())
            db.userfunctionkey.create(
                data={
                    "id": key_id,
                    "userId": user_id,
                    "functionName": function_name,
                    "key": key,
                    "description": description
                }
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
            
            db.userfunctionkey.delete_many(
                where={"id": key_id, "userId": user_id}
            )
            
            return JsonResponse({"success": True})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

