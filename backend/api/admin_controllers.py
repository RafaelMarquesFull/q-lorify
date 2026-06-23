import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import login_required, admin_required
from .utils import get_db

@csrf_exempt
@login_required
@admin_required
def providers(request):
    db = get_db()
    if request.method == "GET":
        providers = db.aiprovider.find_many(
            include={
                "models": True,
                "keys": True 
            }
        )
        
        data = []
        for p in providers:
            # Sort keys by createdAt DESC in python since nested sort is tricky in include
            keys_sorted = sorted(p.keys or [], key=lambda k: k.createdAt, reverse=True)
            
            keys_data = []
            for k in keys_sorted:
                api_key_masked = (k.apiKey or "")[:8] + "..."
                keys_data.append({
                    "id": k.id,
                    "label": k.label,
                    "apiKey": api_key_masked,
                    "isActive": k.isActive,
                    "usageCount": k.usageCount,
                    "lastUsedAt": k.lastUsedAt,
                    "createdAt": k.createdAt
                })
            
            data.append({
                "id": p.id,
                "name": p.name,
                "type": p.type,
                "baseUrl": p.baseUrl,
                "hasApiKey": bool(p.apiKey),
                "rotationEnabled": p.rotationEnabled,
                "keys": keys_data,
                "models": [{"id": m.id, "name": m.name} for m in p.models]
            })
        return JsonResponse(data, safe=False)
        
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            provider = db.aiprovider.create(data={
                "name": body["name"],
                "type": body["type"],
                "baseUrl": body.get("baseUrl"),
                "apiKey": body.get("apiKey")
            })
            return JsonResponse({"id": provider.id, "name": provider.name}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            provider_id = body.get("id")
            
            if not provider_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            # Enable/disable rotation
            if "rotationEnabled" in body:
                db.aiprovider.update(
                    where={"id": provider_id},
                    data={"rotationEnabled": body["rotationEnabled"]}
                )
            
            # Handle other fields via ORM (these are known to Prisma client)
            orm_update = {}
            if "apiKey" in body:
                orm_update["apiKey"] = body["apiKey"]
            if "baseUrl" in body:
                orm_update["baseUrl"] = body["baseUrl"]
            if "name" in body:
                orm_update["name"] = body["name"]
            
            if orm_update:
                db.aiprovider.update(
                    where={"id": provider_id},
                    data=orm_update
                )
            
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            provider_id = body.get("id")
            
            if not provider_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            # Find models to handle relationships
            models = db.aimodel.find_many(where={"providerId": provider_id})
            model_ids = [m.id for m in models]
            
            if model_ids:
                # Check if any Agent is using these models
                agents_using = db.agent.find_first(where={"modelId": {"in": model_ids}})
                if agents_using:
                    return JsonResponse({"error": "Não é possível excluir este provedor pois há Agentes de IA configurados para utilizar seus modelos."}, status=400)
                
                # Unlink models from metrics (since modelId is optional in Metric)
                db.metric.update_many(
                    where={"modelId": {"in": model_ids}},
                    data={"modelId": None}
                )
            
            # Cascade delete: manually delete keys and models
            db.providerapikey.delete_many(where={"providerId": provider_id})
            db.aimodel.delete_many(where={"providerId": provider_id})
            db.aiprovider.delete(where={"id": provider_id})
            
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": f"Erro de banco de dados: {str(e)}"}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
@admin_required
def models(request):
    db = get_db()
    
    if request.method == "GET":
        try:
            raw_models = db.aimodel.find_many(
                include={"provider": True},
                order={"name": "asc"}
            )
            
            all_models = {m.id: m.name for m in raw_models}
            
            data = []
            for m in raw_models:
                data.append({
                    "id": m.id,
                    "name": m.name,
                    "providerModelId": m.providerModelId or m.name,
                    "providerId": m.providerId,
                    "provider": m.provider.name if m.provider else "",
                    "costIn": m.costPerInputToken,
                    "costOut": m.costPerOutputToken,
                    "isOrchestrator": m.isOrchestrator,
                    "isSentiment": m.isSentiment,
                    "description": m.description,
                    "rpm": m.rpm,
                    "integrationGuide": m.integrationGuide,
                    "isPublic": m.isPublic,
                    "fallback1Id": m.fallback1Id,
                    "fallback2Id": m.fallback2Id,
                    "fallback3Id": m.fallback3Id,
                    "fallback1Name": all_models.get(m.fallback1Id),
                    "fallback2Name": all_models.get(m.fallback2Id),
                    "fallback3Name": all_models.get(m.fallback3Id)
                })
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            import uuid
            model_id = str(uuid.uuid4())
            
            db.aimodel.create(data={
                "id": model_id,
                "name": body["name"],
                "providerModelId": body.get("providerModelId") or body["name"],
                "providerId": body["providerId"],
                "costPerInputToken": float(body.get("costIn", 0.0)),
                "costPerOutputToken": float(body.get("costOut", 0.0)),
                "fallback1Id": body.get("fallback1Id"),
                "fallback2Id": body.get("fallback2Id"),
                "fallback3Id": body.get("fallback3Id"),
                "isOrchestrator": bool(body.get("isOrchestrator")),
                "isSentiment": bool(body.get("isSentiment")),
                "description": body.get("description"),
                "rpm": int(body.get("rpm", 60)),
                "integrationGuide": body.get("integrationGuide"),
                "isPublic": bool(body.get("isPublic", True))
            })
            return JsonResponse({"id": model_id}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            model_id = body.get("id")
            
            if not model_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            update_data = {}
            if "name" in body: update_data["name"] = body["name"]
            if "providerModelId" in body: update_data["providerModelId"] = body["providerModelId"]
            if "providerId" in body: update_data["providerId"] = body["providerId"]
            if "costIn" in body: update_data["costPerInputToken"] = float(body["costIn"])
            if "costOut" in body: update_data["costPerOutputToken"] = float(body["costOut"])
            if "fallback1Id" in body: update_data["fallback1Id"] = body["fallback1Id"] or None
            if "fallback2Id" in body: update_data["fallback2Id"] = body["fallback2Id"] or None
            if "fallback3Id" in body: update_data["fallback3Id"] = body["fallback3Id"] or None
            if "isOrchestrator" in body: update_data["isOrchestrator"] = bool(body["isOrchestrator"])
            if "description" in body: update_data["description"] = body["description"]
            if "rpm" in body: update_data["rpm"] = int(body["rpm"])
            if "integrationGuide" in body: update_data["integrationGuide"] = body["integrationGuide"]
            if "isPublic" in body: update_data["isPublic"] = bool(body["isPublic"])
            if "isSentiment" in body: update_data["isSentiment"] = bool(body["isSentiment"])
            
            if update_data:
                db.aimodel.update(where={"id": model_id}, data=update_data)
            
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            model_id = body.get("id")
            
            if not model_id:
                return JsonResponse({"error": "id is required"}, status=400)
            
            db.aimodel.delete(where={"id": model_id})
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
@login_required
@admin_required
def users(request):
    db = get_db()
    
    if request.method == "GET":
        users = db.user.find_many(
            order={"createdAt": "desc"}
        )
        return JsonResponse([{
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "balance": u.balance,
            "createdAt": u.createdAt
        } for u in users], safe=False)
        
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            user_id = body.get("userId")
            new_role = body.get("role")
            
            if not user_id or not new_role:
                 return JsonResponse({"error": "userId and role are required"}, status=400)
            
            # Update user
            updated = db.user.update(
                where={"id": user_id},
                data={"role": new_role}
            )
            
            return JsonResponse({"id": updated.id, "role": updated.role})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
@admin_required
def stats(request):
    """Aggregate Admin Stats"""
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
        
    db = get_db()
    
    # Total Users
    total_users = db.user.count()
    
    # Active Subs
    active_subs = db.subscription.count(where={"status": "active"})
    
    try:
        agg = db.metric.aggregate(sum={"cost": True, "inputTokens": True, "outputTokens": True})
        total_cost = agg.get("_sum", {}).get("cost") or 0.0
        total_tokens = (agg.get("_sum", {}).get("inputTokens") or 0) + (agg.get("_sum", {}).get("outputTokens") or 0)
    except Exception:
        total_cost = 0.0
        total_tokens = 0
    
    return JsonResponse({
        "totalUsers": total_users,
        "activeSubs": active_subs,
        "totalCost": total_cost,
        "totalTokens": total_tokens
    })

@csrf_exempt
@login_required
@admin_required
def manage_balance(request):
    """
    Admin endpoint to manually adjust user balance.
    Body: { "userId": "...", "amount": 10.0, "type": "CREDIT" | "DEBIT", "description": "..." }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
        
    try:
        body = json.loads(request.body)
        user_id = body.get("userId")
        amount = float(body.get("amount", 0))
        tx_type = body.get("type", "CREDIT") # CREDIT, DEBIT
        description = body.get("description", "Ajuste Administrativo")
        
        if not user_id or amount <= 0:
             return JsonResponse({"error": "Invalid parameters"}, status=400)
             
        db = get_db()
        
        # Calculate balance delta
        balance_delta = amount if tx_type == "CREDIT" else -amount
        
        # Update User
        user = db.user.update(
            where={"id": user_id},
            data={"balance": {"increment": balance_delta}}
        )
        
        # Create Transaction
        db.transaction.create(data={
            "userId": user_id,
            "type": tx_type,
            "amount": amount,
            "description": description
        })
        
        # If Debit, check auto-recharge (optional, but good for consistency)
        if tx_type == "DEBIT":
            try:
                from .stripe_services import check_and_trigger_auto_recharge
                check_and_trigger_auto_recharge(user_id)
            except Exception as e:
                print(f"Auto-recharge check failed during admin adjustment: {e}")

        return JsonResponse({"balance": user.balance})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
@admin_required
def provider_keys(request, provider_id):
    """
    CRUD for Provider API Keys.
    GET: List keys for provider
    POST: Add new key { "apiKey": "...", "label": "..." }
    DELETE: { "keyId": "..." }
    PATCH: { "keyId": "...", "isActive": bool }
    """
    db = get_db()
    
    # Verify provider exists
    provider = db.aiprovider.find_unique(where={"id": provider_id})
    if not provider:
        return JsonResponse({"error": "Provider not found"}, status=404)
    
    if request.method == "GET":
        try:
            keys = db.providerapikey.find_many(
                where={"providerId": provider_id},
                order={"createdAt": "desc"}
            )
            data = []
            for k in keys:
                data.append({
                    "id": k.id,
                    "label": k.label,
                    "apiKey": (k.apiKey or "")[:8] + "...",
                    "isActive": k.isActive,
                    "usageCount": k.usageCount,
                    "lastUsedAt": k.lastUsedAt,
                    "createdAt": k.createdAt
                })
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            api_key = body.get("apiKey")
            label = body.get("label", "")
            
            if not api_key:
                return JsonResponse({"error": "apiKey is required"}, status=400)
            
            new_key = db.providerapikey.create(
                data={
                    "providerId": provider_id,
                    "apiKey": api_key,
                    "label": label,
                    "isActive": True,
                    "usageCount": 0
                }
            )
            
            return JsonResponse({"id": new_key.id, "label": new_key.label}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "PATCH":
        try:
            body = json.loads(request.body)
            key_id = body.get("keyId")
            
            if not key_id:
                return JsonResponse({"error": "keyId is required"}, status=400)
            
            if "isActive" in body:
                db.providerapikey.update(
                    where={"id": key_id},
                    data={"isActive": body["isActive"]}
                )
            
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    if request.method == "DELETE":
        try:
            body = json.loads(request.body)
            key_id = body.get("keyId")
            
            if not key_id:
                return JsonResponse({"error": "keyId is required"}, status=400)
            
            db.providerapikey.delete(where={"id": key_id})
            
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required
@admin_required
def sync_provider_models(request, provider_id):
    """
    Fetch available models from a provider's API.
    Returns list of models that can be imported.
    """
    import requests
    
    db = get_db()
    
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        # Get provider details
        provider = db.aiprovider.find_unique(where={"id": provider_id})
        
        if not provider:
            return JsonResponse({"error": "Provider not found"}, status=404)
        
        base_url = provider.baseUrl
        if not base_url:
            if provider.type == "openai":
                base_url = "https://api.openai.com/v1"
            elif provider.type == "groq":
                base_url = "https://api.groq.com/openai/v1"
            else:
                return JsonResponse({"error": "Provider has no baseUrl configured and no default exists for this type"}, status=400)
        
        base_url = base_url.rstrip('/')
        
        # Get API key for this provider (use rotation or single key)
        from .key_rotation import get_next_api_key
        api_key = get_next_api_key(provider_id)
        
        if not api_key:
            return JsonResponse({"error": "No API key configured for this provider"}, status=400)
        
        # Fetch models from provider API
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            resp = requests.get(f"{base_url}/models", headers=headers, timeout=30)
            
            if resp.status_code != 200:
                return JsonResponse({
                    "error": f"Provider API returned status {resp.status_code}: {resp.text[:200]}"
                }, status=502)
            
            data = resp.json()
            
        except requests.exceptions.Timeout:
            return JsonResponse({"error": "Provider API timeout"}, status=504)
        except Exception as e:
            return JsonResponse({"error": f"Failed to fetch from provider: {str(e)}"}, status=502)
        
        existing_models = db.aimodel.find_many(where={"providerId": provider_id})
        existing_ids = set()
        for m in existing_models:
            if m.providerModelId:
                existing_ids.add(m.providerModelId)
        
        # Parse and filter models
        available_models = []
        raw_models = data.get("data", data.get("models", []))
        
        for model in raw_models:
            model_id = model.get("id")
            if model_id:
                available_models.append({
                    "id": model_id,
                    "name": model_id,  # Usually the model ID is also the name
                    "object": model.get("object", "model"),
                    "owned_by": model.get("owned_by", ""),
                    "already_imported": model_id in existing_ids
                })
        
        # Sort: not imported first, then alphabetically
        available_models.sort(key=lambda x: (x["already_imported"], x["id"]))
        
        return JsonResponse({
            "provider": {
                "id": provider.id,
                "name": provider.name
            },
            "models": available_models,
            "total": len(available_models),
            "imported_count": len([m for m in available_models if m["already_imported"]])
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
@admin_required
def admin_stats(request):
    """
    Get aggregated dashboard stats for Admin.
    Params: timeRange (24h, 7d, 30d), userId (optional, 'all' for global)
    """
    try:
        db = get_db()
        time_range = request.GET.get('timeRange', '7d')
        filter_user_id = request.GET.get('userId', 'all')
        
        from .dashboard_utils import get_date_range
        now, start_date = get_date_range(time_range)
            
        # Base filters
        metric_filter = {
            "timestamp": {"gte": start_date}
        }
        orch_filter = {
            "createdAt": {"gte": start_date}
        }
        transaction_filter = {
            "createdAt": {"gte": start_date},
            "type": "DEBIT"
        }
        
        # Apply user filter if not 'all'
        if filter_user_id != 'all' and filter_user_id:
            metric_filter["userId"] = filter_user_id
            orch_filter["userId"] = filter_user_id  # Assuming userId is present in OrchExecution
            transaction_filter["userId"] = filter_user_id
        
        # 1. Fetch Metrics
        metrics = db.metric.find_many(
            where=metric_filter,
            include={"model": True}
        )
        
        # 2. Fetch Orchestrator Executions
        # Note: OrchExecution might not have userId populated for API clients?! 
        # But schema has userId.
        # If filtering by user, we might miss API client calls unless linked.
        # For this implementation, we stick to strict userId match.
        
        # Filter manually if OrchExecution doesn't support the complex OR logic in find_many easily with python client
        # actually schema has userId.
        orch_execs = db.orchexecution.find_many(
            where=orch_filter
        )
        
        # Aggregations
        total_requests = len(metrics) + len(orch_execs)
        
        transactions = db.transaction.find_many(where=transaction_filter)
        total_cost_real = sum([t.amount for t in transactions])
        
        # Counts logic
        if filter_user_id != 'all':
            active_agents_count = db.agent.count(where={"userId": filter_user_id})
            api_keys_count = db.apikey.count(where={"userId": filter_user_id})
        else:
            active_agents_count = db.agent.count()
            api_keys_count = db.apikey.count() # This is user api keys, not provider keys
            
        stats = {
            "total_requests": total_requests,
            "total_cost": round(total_cost_real, 2),
            "active_agents": active_agents_count, 
            "api_keys_count": api_keys_count,
            "function_requests": len(orch_execs),
            "input_tokens": sum([m.inputTokens for m in metrics]),
            "output_tokens": sum([m.outputTokens for m in metrics]),
            "sentiment_requests": sum([1 for m in metrics if m.model and m.model.isSentiment]),
            "avg_latency": round(sum([m.requestDurationMs or 0 for m in metrics]) / len(metrics) if len(metrics) > 0 else 0, 0)
        }
        
        return JsonResponse(stats)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
@admin_required
def admin_chart(request):
    """
    Get chart data (tokens/requests over time) for Admin.
    """
    try:
        db = get_db()
        time_range = request.GET.get('timeRange', '7d')
        filter_user_id = request.GET.get('userId', 'all')
        
        from .dashboard_utils import get_date_range, get_iterations_and_format, SP_TZ, WEEKDAYS_PT
        now, start_date = get_date_range(time_range)
        iterations, date_fmt = get_iterations_and_format(time_range)
        
        # Convert now to SP TZ for bucket matching
        now_sp = now.astimezone(SP_TZ)
        
        where_filter = {
            "timestamp": {"gte": start_date}
        }
        if filter_user_id != 'all':
             where_filter["userId"] = filter_user_id
            
        metrics = db.metric.find_many(
            where=where_filter
        )
        
        from datetime import timedelta
        
        final_chart_data = []
        
        for i in range(iterations - 1, -1, -1):
            if time_range == '24h':
                date_obj = now_sp - timedelta(hours=i)
                key = date_obj.strftime("%H:00")
            elif time_range == '30d':
                date_obj = now_sp - timedelta(days=i)
                key = date_obj.strftime("%d/%m")
            else:
                date_obj = now_sp - timedelta(days=i)
                key = WEEKDAYS_PT.get(date_obj.strftime("%a"), date_obj.strftime("%a"))
            
            input_tokens = 0
            output_tokens = 0
            period_cost = 0.0
            requests_count = 0
            
            # Filter metrics for this bucket
            for m in metrics:
                m_local = m.timestamp.astimezone(SP_TZ)
                
                match = False
                if time_range == '24h':
                    match = m_local.strftime("%H:00") == key and m_local.day == date_obj.day
                elif time_range == '30d':
                    match = m_local.strftime("%d/%m") == key
                else:
                    match = WEEKDAYS_PT.get(m_local.strftime("%a"), m_local.strftime("%a")) == key and (now_sp - m_local).days < 8
                
                if match:
                    input_tokens += m.inputTokens
                    output_tokens += m.outputTokens
                    period_cost += m.cost or 0.0
                    requests_count += 1
            
            final_chart_data.append({
                "name": key, 
                "input": input_tokens,
                "output": output_tokens,
                "total": input_tokens + output_tokens,
                "cost": round(period_cost, 6),
                "requests": requests_count
            })

        return JsonResponse(final_chart_data, safe=False)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
@admin_required
def admin_cost_distribution(request):
    """
    Get cost distribution by model for Admin.
    """
    try:
        db = get_db()
        time_range = request.GET.get('timeRange', '7d')
        filter_user_id = request.GET.get('userId', 'all')
        
        from .dashboard_utils import get_date_range
        now, start_date = get_date_range(time_range)
        
        where_filter = {
            "timestamp": {"gte": start_date}
        }
        if filter_user_id != 'all':
            where_filter["userId"] = filter_user_id
            
        metrics = db.metric.find_many(
            where=where_filter,
            include={"model": True}
        )
        
        distribution = {}
        for m in metrics:
            model_name = m.model.name if m.model else "Unknown"
            cost = m.cost or 0.0
            if model_name in distribution:
                distribution[model_name] += cost
            else:
                distribution[model_name] = cost
                
        data = [
            {"name": k, "value": round(v, 6)} 
            for k, v in distribution.items() 
            if v > 0
        ]
        data.sort(key=lambda x: x["value"], reverse=True)
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
@admin_required
def admin_activity(request):
    """
    Get recent activity for Admin.
    """
    try:
        db = get_db()
        limit = int(request.GET.get('limit', 10))
        page = int(request.GET.get('page', 1))
        skip = (page - 1) * limit
        filter_user_id = request.GET.get('userId', 'all')
        
        where_filter = {}
        if filter_user_id != 'all':
            where_filter["userId"] = filter_user_id
            
        metrics = db.metric.find_many(
            where=where_filter,
            include={"model": True, "user": True}, # Include user info for admin view
            order={"timestamp": "desc"},
            skip=skip,
            take=limit
        )
        
        activity = []
        for m in metrics:
            model_name = m.model.name if m.model else "Unknown Model"
            user_email = m.user.email if m.user else "Unknown User"
            
            activity.append({
                "id": m.id,
                "description": f"Requisição: {model_name}",
                "timestamp": m.timestamp.isoformat(),
                "status": "completed",
                "meta": f"{user_email}", # Show user email in meta for admin
                "tokens": m.inputTokens + m.outputTokens
            })
            
        return JsonResponse(activity, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
