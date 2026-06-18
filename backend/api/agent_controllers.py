import json
import threading
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import login_required
from .utils import get_db
from .rules_compiler import compile_prompt_rules, save_compiled_rules

@csrf_exempt
@login_required
def admin_settings_rules_model(request):
    """
    GET  /admin/settings/rules-model — get the global rules extraction model
    POST /admin/settings/rules-model — set the global rules extraction model
    """
    db = get_db()

    if request.method == "GET":
        rows = db.query_raw("SELECT value FROM SystemSetting WHERE key = 'rulesModelId'")
        model_id = rows[0]["value"] if rows else None
        model_name = None
        if model_id:
            m = db.aimodel.find_unique(where={"id": model_id})
            model_name = m.name if m else None
        return JsonResponse({"rulesModelId": model_id, "modelName": model_name})

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            model_id = body.get("rulesModelId")
            if not model_id:
                return JsonResponse({"error": "rulesModelId is required"}, status=400)
            m = db.aimodel.find_unique(where={"id": model_id})
            if not m:
                return JsonResponse({"error": "Model not found"}, status=404)
            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute_raw(
                "INSERT INTO SystemSetting (key, value, updatedAt) VALUES ('rulesModelId', ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = ?, updatedAt = ?",
                model_id, now, model_id, now
            )
            return JsonResponse({"success": True, "rulesModelId": model_id, "modelName": m.name})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required
def list_create_agents(request):
    db = get_db()
    
    if request.method == "GET":
        # List personal agents + public/system agents (where userId is null)
        # Note: Prisma OR filter might need raw query or multiple queries if complex.
        # For simple sqlite: user.id OR userId is null
        
        # We fetch user agents
        my_agents = db.agent.find_many(where={"userId": request.user.id}, include={"model": True})
        
        # We could also fetch system agents
        # system_agents = db.agent.find_many(where={"userId": None}) 
        
        data = []
        for a in my_agents:
            data.append({
                "id": a.id,
                "name": a.name,
                "systemPrompt": a.systemPrompt,
                "model": a.model.name,
                "createdAt": a.createdAt
            })
            
        return JsonResponse(data, safe=False)

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            create_data = {
                "name": body["name"],
                "systemPrompt": body["systemPrompt"],
                "modelId": body["modelId"],
                "userId": request.user.id,
                "config": json.dumps(body.get("config", {}))
            }
            if body.get("rulesModelId"):
                create_data["rulesModelId"] = body["rulesModelId"]
            agent = db.agent.create(data=create_data)

            # Trigger async rules compilation if rulesModelId is set
            if agent.rulesModelId and agent.systemPrompt:
                _trigger_compilation_async(agent.id, agent.systemPrompt, agent.rulesModelId)

            return JsonResponse({"id": agent.id, "name": agent.name}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
def admin_agents(request):
    """
    GET  /admin/agents — list all agents with rules metadata
    POST /admin/agents — create agent (admin)
    PATCH /admin/agents — update agent fields (rulesModelId, systemPrompt, name)
    """
    db = get_db()

    if request.method == "GET":
        agents = db.agent.find_many(include={"model": True})
        data = []
        for a in agents:
            data.append({
                "id": a.id,
                "name": a.name,
                "systemPrompt": a.systemPrompt[:200] + "..." if len(a.systemPrompt or "") > 200 else a.systemPrompt,
                "systemPromptFull": a.systemPrompt,
                "modelId": a.modelId,
                "modelName": a.model.name if a.model else None,
                "rulesModelId": a.rulesModelId,
                "rulesVersion": a.rulesVersion,
                "rulesCompiledAt": str(a.rulesCompiledAt) if a.rulesCompiledAt else None,
                "hasRules": a.compiledRules is not None and a.compiledRules != "",
                "promptHash": a.promptHash,
                "createdAt": str(a.createdAt),
            })
        return JsonResponse(data, safe=False)

    if request.method == "POST":
        try:
            body = json.loads(request.body)
            create_data = {
                "name": body["name"],
                "systemPrompt": body["systemPrompt"],
                "modelId": body["modelId"],
                "userId": request.user.id,
                "config": json.dumps(body.get("config", {}))
            }
            if body.get("rulesModelId"):
                create_data["rulesModelId"] = body["rulesModelId"]
            agent = db.agent.create(data=create_data)
            if agent.rulesModelId and agent.systemPrompt:
                _trigger_compilation_async(agent.id, agent.systemPrompt, agent.rulesModelId)
            return JsonResponse({"id": agent.id, "name": agent.name}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            agent_id = body.get("id")
            if not agent_id:
                return JsonResponse({"error": "id is required"}, status=400)

            update_data = {}
            if "name" in body:
                update_data["name"] = body["name"]
            if "systemPrompt" in body:
                update_data["systemPrompt"] = body["systemPrompt"]
            if "modelId" in body:
                update_data["modelId"] = body["modelId"]
            if "rulesModelId" in body:
                update_data["rulesModelId"] = body["rulesModelId"] or None

            if not update_data:
                return JsonResponse({"error": "No fields to update"}, status=400)

            db.agent.update(where={"id": agent_id}, data=update_data)
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            agent_id = body.get("id")
            if not agent_id:
                return JsonResponse({"error": "id is required"}, status=400)
            db.agent.delete(where={"id": agent_id})
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required
def compile_agent_rules(request, agent_id):
    """
    POST /admin/agents/<id>/compile-rules
    Trigger rule compilation for an agent. Can also be used to recompile.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    db = get_db()
    agent = db.agent.find_unique(where={"id": agent_id})
    if not agent:
        return JsonResponse({"error": "Agent not found"}, status=404)

    # Use global rulesModelId from SystemSetting
    rows = db.query_raw("SELECT value FROM SystemSetting WHERE key = 'rulesModelId'")
    rules_model_id = rows[0]["value"] if rows else None
    if not rules_model_id:
        return JsonResponse({"error": "Modelo robusto não configurado. Selecione um modelo na aba Agentes & Rules."}, status=400)

    # Run compilation synchronously (admin can wait)
    success, compiled, error = compile_prompt_rules(db, agent.systemPrompt, rules_model_id)
    if not success:
        return JsonResponse({"error": error, "success": False}, status=500)

    saved = save_compiled_rules(db, agent_id, compiled)
    if not saved:
        return JsonResponse({"error": "Failed to save compiled rules", "success": False}, status=500)

    return JsonResponse({
        "success": True,
        "rules_count": len(compiled.get("rules", [])),
        "rule_types": list(set(r.get("type") for r in compiled.get("rules", []))),
        "version": agent.rulesVersion + 1
    })


@csrf_exempt
@login_required
def get_agent_rules(request, agent_id):
    """
    GET /admin/agents/<id>/rules
    View compiled rules for an agent.
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    db = get_db()
    agent = db.agent.find_unique(where={"id": agent_id})
    if not agent:
        return JsonResponse({"error": "Agent not found"}, status=404)

    compiled = None
    if agent.compiledRules:
        try:
            compiled = json.loads(agent.compiledRules)
        except json.JSONDecodeError:
            compiled = None

    return JsonResponse({
        "agent_id": agent.id,
        "agent_name": agent.name,
        "rules_model_id": agent.rulesModelId,
        "rules_version": agent.rulesVersion,
        "rules_compiled_at": str(agent.rulesCompiledAt) if agent.rulesCompiledAt else None,
        "compiled_rules": compiled,
        "has_rules": compiled is not None
    })


def _trigger_compilation_async(agent_id: str, system_prompt: str, rules_model_id: str):
    """Trigger rules compilation in a background thread."""
    def _compile():
        try:
            db = get_db()
            success, compiled, error = compile_prompt_rules(db, system_prompt, rules_model_id)
            if success:
                save_compiled_rules(db, agent_id, compiled)
            else:
                print(f"[RulesCompiler] Async compilation failed for agent {agent_id}: {error}")
        except Exception as e:
            print(f"[RulesCompiler] Async compilation error: {e}")

    thread = threading.Thread(target=_compile, daemon=True)
    thread.start()
    print(f"[RulesCompiler] Triggered async compilation for agent {agent_id}")


@csrf_exempt
def list_models_public(request):
    """Return all public models with detailed info for client page"""
    db = get_db()
    if request.method == "GET":
        models = db.query_raw('''
            SELECT m.*, p.name as providerName 
            FROM AIModel m 
            JOIN AIProvider p ON m.providerId = p.id
            WHERE m.isPublic = 1
            ORDER BY m.name ASC
        ''')
        
        result = []
        for m in models:
            if isinstance(m, dict):
                result.append({
                    "id": m.get("id"),
                    "name": m.get("name"),
                    "providerModelId": m.get("providerModelId"),
                    "provider": "QLORIFY", # White-label masking
                    "costIn": m.get("costPerInputToken", 0),
                    "costOut": m.get("costPerOutputToken", 0),
                    "description": m.get("description"),
                    "rpm": m.get("rpm", 60),
                    "integrationGuide": m.get("integrationGuide"),
                    "isOrchestrator": bool(m.get("isOrchestrator")),
                    "isSentiment": bool(m.get("isSentiment"))
                })
        
        return JsonResponse(result, safe=False)

@csrf_exempt
def list_functions_public(request):
    """Return all enabled orchestrator functions (no auth required)"""
    db = get_db()
    if request.method == "GET":
        try:
            functions = db.query_raw(
                'SELECT name, displayName, description FROM OrchFunction WHERE enabled = 1 ORDER BY name ASC'
            )
            
            result = []
            for f in functions:
                if isinstance(f, dict):
                    result.append({
                        "name": f.get("name"),
                        "displayName": f.get("displayName"),
                        "description": f.get("description"),
                    })
            
            return JsonResponse(result, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
