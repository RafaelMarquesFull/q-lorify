from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import login_required
from .utils import get_db
from datetime import datetime, timedelta, timezone
from django.utils import timezone as django_timezone
import json
import pytz

SP_TZ = pytz.timezone('America/Sao_Paulo')

WEEKDAYS_PT = {
    "Mon": "Seg", "Tue": "Ter", "Wed": "Qua", "Thu": "Qui", "Fri": "Sex", "Sat": "Sáb", "Sun": "Dom"
}

@csrf_exempt
@login_required
def get_overview_stats(request):
    """
    Get aggregated dashboard stats.
    Params: timeRange (24h, 7d, 30d), apiKey (optional)
    """
    try:
        db = get_db()
        user_id = request.user.id
        
        time_range = request.GET.get('timeRange', '7d')
        api_key_id = request.GET.get('apiKey', 'all')
        
        # Calculate date filter
        now = django_timezone.now()
        start_date = now - timedelta(days=7) # default
        
        if time_range == '24h':
            start_date = now - timedelta(hours=24)
        elif time_range == '30d':
            start_date = now - timedelta(days=30)
            
        # Base filters
        metric_filter = {
            "userId": user_id,
            "timestamp": {"gte": start_date}
        }
        
        orch_filter = {
            "OR": [
                {"userId": user_id},
                # If checking by API Key, might need to link OrchClient? 
                # For now assume userId is primary
            ],
            "createdAt": {"gte": start_date}
        }

        # TODO: API Key filtering logic would go here
        # Currently Metric doesn't store API Key ID, only user.
        # Ideally we'd add apiKeyId to Metric table. 
        # For now, we filter by User only.

        # 1. Fetch Metrics
        metrics = db.metric.find_many(
            where=metric_filter,
            include={"model": True}
        )
        
        # 2. Fetch Orchestrator Executions
        orch_execs = db.orchexecution.find_many(
            where=orch_filter
        )
        
        # Aggregations
        # Prevent double counting: Subtract orchestrator metrics from total if we add orch_execs
        # (Newer orchestrator calls are in BOTH tables)
        orch_metrics_count = sum(1 for m in metrics if m.model and m.model.isOrchestrator)
        unique_orch_execs = max(0, len(orch_execs) - orch_metrics_count)
        
        total_requests = len(metrics) + unique_orch_execs
        total_cost = sum([m.cost for m in metrics])
        # Add orchestrator cost (stored as string "low"?! schema says cost String @default("low"))
        # Wait, looked at schema, OrchExecution cost is String. 
        # We need check Transaction for actual cost.
        
        transactions = db.transaction.find_many(
            where={
                "userId": user_id,
                "createdAt": {"gte": start_date},
                "type": "DEBIT"
            }
        )
        total_cost_real = sum([t.amount for t in transactions])
        
        stats = {
            "total_requests": total_requests,
            "total_requests": total_requests,
            "total_cost": round(total_cost_real, 2),
            "active_agents": db.agent.count(where={"userId": user_id}), 
            "api_keys_count": db.apikey.count(where={"userId": user_id}),
            "function_requests": len(orch_execs),
            "input_tokens": sum([m.inputTokens for m in metrics]),
            "output_tokens": sum([m.outputTokens for m in metrics]),
            "sentiment_requests": sum([1 for m in metrics if m.model and m.model.isSentiment]),
            "avg_latency": round(sum([m.requestDurationMs for m in metrics]) / len(metrics) if len(metrics) > 0 else 0, 0)
        }
        
        return JsonResponse(stats)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def get_usage_chart(request):
    """
    Get chart data (tokens/requests over time).
    """
    try:
        db = get_db()
        user_id = request.user.id
        time_range = request.GET.get('timeRange', '7d')
        
        # Convert to SP Time
        now = django_timezone.now().astimezone(SP_TZ)
        start_date = now - timedelta(days=7)
        iterations = 7
        
        if time_range == '24h':
            start_date = now - timedelta(hours=24)
            iterations = 24
        elif time_range == '30d':
            start_date = now - timedelta(days=30)
            iterations = 30
            
        metrics = db.metric.find_many(
            where={
                "userId": user_id,
                "timestamp": {"gte": start_date}
            }
        )
        
        # Group by date
        data_map = {}
        
        # Initialize map with 0s
        for i in range(iterations):
            date_iter = now - timedelta(days=i)
            d = WEEKDAYS_PT.get(date_iter.strftime("%a"), date_iter.strftime("%a"))
            
            if time_range == '24h':
                 date_iter = now - timedelta(hours=i)
                 d = date_iter.strftime("%H:00")
            elif time_range == '30d':
                 date_iter = now - timedelta(days=i)
                 d = date_iter.strftime("%d/%m")

            if d not in data_map:
                data_map[d] = 0
                
        # Fill data
        for m in metrics:
            # Convert metric timestamp to SP time
            m_local = m.timestamp.astimezone(SP_TZ)
            
            d_str = WEEKDAYS_PT.get(m_local.strftime("%a"), m_local.strftime("%a"))
            if time_range == '24h':
                d_str = m_local.strftime("%H:00")
            elif time_range == '30d':
                d_str = m_local.strftime("%d/%m")
                
            if d_str in data_map:
                data_map[d_str] += (m.inputTokens + m.outputTokens)
            else:
                data_map[d_str] = (m.inputTokens + m.outputTokens)
                
        # Format for Recharts
        chart_data = [{"name": k, "tokens": v} for k, v in reversed(list(data_map.items()))] 
        # Reversed usage of dict is risky in older python, but fine here for key insertion order if we did it right.
        # Better to sort by date. 
        # Re-doing logic to ensure correct sort order.
        
        final_chart_data = []
        for i in range(iterations - 1, -1, -1):
            if time_range == '24h':
                date_obj = now - timedelta(hours=i)
                key = date_obj.strftime("%H:00")
            elif time_range == '30d':
                date_obj = now - timedelta(days=i)
                key = date_obj.strftime("%d/%m")
            else:
                date_obj = now - timedelta(days=i)
                key = WEEKDAYS_PT.get(date_obj.strftime("%a"), date_obj.strftime("%a"))
            
            input_tokens = 0
            input_tokens = 0
            output_tokens = 0
            period_cost = 0.0
            requests_count = 0
            output_tokens = 0
            period_cost = 0.0
            # Filter metrics for this bucket
            # This is O(N*M), inefficient but fine for small dashboard data
            for m in metrics:
                # Convert metric to SP
                m_local = m.timestamp.astimezone(SP_TZ)
                
                if time_range == '24h':
                    match = m_local.strftime("%H:00") == key and m_local.day == date_obj.day
                elif time_range == '30d':
                    match = m_local.strftime("%d/%m") == key
                else:
                    match = WEEKDAYS_PT.get(m_local.strftime("%a"), m_local.strftime("%a")) == key and (now - m_local).days < 8
                
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
def get_recent_activity(request):
    """
    Get recent activity (metrics/transactions).
    """
    try:
        db = get_db()
        user_id = request.user.id
        
        limit = int(request.GET.get('limit', 10))
        page = int(request.GET.get('page', 1))
        skip = (page - 1) * limit
        
        # Get recent metrics with pagination
        metrics = db.metric.find_many(
            where={"userId": user_id},
            include={"model": True},
            order={"timestamp": "desc"},
            skip=skip,
            take=limit
        )
        
        activity = []
        for m in metrics:
            model_name = m.model.name if m.model else "Unknown Model"
            # Format timestamp to ISO
            activity.append({
                "id": m.id,
                "description": f"Requisição para {model_name}",
                "timestamp": m.timestamp.isoformat(),
                "status": "completed",
                "meta": f"{m.inputTokens + m.outputTokens} tokens"
            })
            
        return JsonResponse(activity, safe=False)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def get_cost_distribution(request):
    """
    Get cost distribution by model.
    """
    try:
        db = get_db()
        user_id = request.user.id
        time_range = request.GET.get('timeRange', '7d')
        
        now = django_timezone.now()
        start_date = now - timedelta(days=7)
        
        if time_range == '24h':
            start_date = now - timedelta(hours=24)
        elif time_range == '30d':
            start_date = now - timedelta(days=30)
            
        metrics = db.metric.find_many(
            where={
                "userId": user_id,
                "timestamp": {"gte": start_date}
            },
            include={"model": True}
        )
        
        # Aggregate by model
        distribution = {}
        
        for m in metrics:
            model_name = m.model.name if m.model else "Unknown"
            cost = m.cost or 0.0
            
            if model_name in distribution:
                distribution[model_name] += cost
            else:
                distribution[model_name] = cost
                
        # Format for chart [{"name": "Model A", "value": 1.23}, ...]
        data = [
            {"name": k, "value": round(v, 6)} 
            for k, v in distribution.items() 
            if v > 0
        ]
        
        # Sort by value descending
        data.sort(key=lambda x: x["value"], reverse=True)
        
        return JsonResponse(data, safe=False)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def get_performance_stats(request):
    """
    Get detailed performance metrics for Sentiment Analysis (Cache vs ML vs AI).
    GET /api/ai/sentiment/stats/performance?domain=transport&days=7
    """
    try:
        db = get_db()
        domain = request.GET.get('domain', 'transport')
        days = int(request.GET.get('days', 7))
        start_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Aggregation Query (Prisma groupby not fully supported in all modes, using raw or manual agg)
        # Fetching logs roughly (limit 1000 to avoid heavy load, ideally use COUNT)
        
        # 1. Total Requests
        total_count = db.sentimentlog.count(
            where={
                "domain": domain, 
                "timestamp": {"gte": start_date}
            }
        )
        
        if total_count == 0:
             return JsonResponse({
                "hit_rates": {"cache": 0, "model": 0, "ai": 0, "rule": 0},
                "latency_avg": 0,
                "contradictions": 0,
                "total": 0
             })

        # 2. Source Distribution (Cache vs ML vs AI)
        sources = db.sentimentlog.group_by(
            by=["source"],
            where={
                "domain": domain,
                "timestamp": {"gte": start_date}
            },
            count={"_all": True},
            avg={"executionTimeMs": True}
        )
        print(f"[DEBUG STATS] Sources GroupBy: {sources}")
        
        stats_map = {
            "learned_cache": 0,
            "local_model": 0,
            "ai_classifier": 0,
            "rule_match": 0,
            "logic_guardrail": 0,
            "heuristic": 0 # sticky/exception
        }
        
        latency_map = {}
        
        for row in sources:
            src = row.get('source')
            cnt = row.get('_count', {}).get('_all', 0)
            lat = row.get('_avg', {}).get('executionTimeMs', 0) or 0
            
            # Normalize sources
            if 'cache' in src: key = "learned_cache"
            elif 'local_model' in src: key = "local_model"
            elif 'ai_' in src: key = "ai_classifier"
            elif 'rule' in src: key = "rule_match"
            elif 'guardrail' in src: key = "logic_guardrail"
            else: key = "heuristic"
            
            stats_map[key] = stats_map.get(key, 0) + cnt
            latency_map[key] = lat

        # Calculate Percentages
        hit_rates = {
            "cache": round((stats_map["learned_cache"] / total_count) * 100, 1),
            "model": round((stats_map["local_model"] / total_count) * 100, 1),
            "ai": round((stats_map["ai_classifier"] / total_count) * 100, 1),
            "rule": round((stats_map["rule_match"] / total_count) * 100, 1),
            "guardrail": round((stats_map["logic_guardrail"] / total_count) * 100, 1) # Contradictions
        }
        
        return JsonResponse({
            "hit_rates": hit_rates,
            "distribution": stats_map,
            "latency_by_source": latency_map,
            "total_requests": total_count
        })

    except Exception as e:
        print(f"[STATS ERROR] {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def get_financial_stats(request):
    """
    Estimate financial savings from Cache/ML interception.
    GET /api/ai/sentiment/stats/financial?domain=transport
    """
    try:
        db = get_db()
        domain = request.GET.get('domain', 'transport')
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        
        # 1. Count Cache/ML hits (which saved tokens)
        avoided_ai_logs = db.sentimentlog.find_many(
            where={
                "domain": domain,
                "timestamp": {"gte": start_date},
                "source": {"in": ["learned_cache", "local_model", "rule_match", "sticky_session"]}
            }
        )
        avoided_count = len(avoided_ai_logs)
        
        # 2. Estimate tokens per request (avg from AI hits)
        # Fetch a sample of AI logs to get avg tokens
        ai_logs = db.sentimentlog.find_many(
            where={
                "domain": domain,
                "source": {"contains": "ai_"},
                "tokenUsage": {"gt": 0}
            },
            take=50
        )
        
        avg_tokens = 0
        if ai_logs:
            avg_tokens = sum([l.tokenUsage for l in ai_logs]) / len(ai_logs)
        else:
            avg_tokens = 150 # Default conservative estimate (input + output)
            
        # 3. Calculate Savings
        # Assume GPT-4o-mini price approx: $0.15/1M input, $0.60/1M output -> Avg $0.40/1M ($0.0000004 per token)
        # Or GPT-4o: $2.50/1M In, $10/1M Out -> Avg $6.00/1M
        # Let's assume a blended cost or use a configured cost per 1k tokens.
        COST_PER_1K_TOKENS = 0.002 # $2.00 per 1M (Generic estimate)
        
        tokens_saved = avoided_count * avg_tokens
        money_saved = (tokens_saved / 1000) * COST_PER_1K_TOKENS
        
        return JsonResponse({
            "requests_deflected": avoided_count,
            "tokens_saved_est": int(tokens_saved),
            "money_saved_usd": round(money_saved, 4),
            "avg_tokens_per_req": int(avg_tokens)
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
