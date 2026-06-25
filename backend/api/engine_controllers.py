import json
import re
import requests
import httpx
from asgiref.sync import sync_to_async
import time
import uuid
from datetime import datetime
from django.utils import timezone
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import login_required
from .utils import get_db
from .rate_limiter import check_rate_limit, get_rate_limit_headers

def check_user_balance(request):
    """
    Check if user has positive balance.
    Returns (True, None) if allowed.
    Returns (False, JsonResponse) if blocked.
    """
    # Skip balance check for OrchClient (external API clients like n8n)
    if getattr(request, 'auth_method', None) == 'orch_client':
        return True, None
    if not hasattr(request.user, 'balance') or request.user.balance <= 0:
        return False, JsonResponse({
            "error": {
                "message": "Insufficient funds. Please recharge your account.",
                "type": "payment_error",
                "code": "insufficient_balance"
            }
        }, status=402)
    return True, None

def get_model_with_fallbacks(db, model_id):
    """
    Get a model and its full chain of fallbacks via raw SQL.
    Returns list of model dicts in priority order: [primary, fallback1, fallback2, fallback3]
    """
    try:
        model = db.aimodel.find_unique(
            where={"id": model_id},
            include={"provider": True}
        )
        
        if not model or not model.provider:
            return []
            
        def _to_dict(m):
            return {
                "id": m.id,
                "name": m.name,
                "providerModelId": m.providerModelId,
                "providerId": m.providerId,
                "costPerInputToken": m.costPerInputToken,
                "costPerOutputToken": m.costPerOutputToken,
                "fallback1Id": m.fallback1Id,
                "fallback2Id": m.fallback2Id,
                "fallback3Id": m.fallback3Id,
                "rpm": m.rpm,
                "baseUrl": m.provider.baseUrl,
                "apiKey": m.provider.apiKey
            }
            
        primary = _to_dict(model)
        models = [primary]
        
        # Fetch fallbacks
        for fallback_key in ['fallback1Id', 'fallback2Id', 'fallback3Id']:
            fallback_id = primary.get(fallback_key)
            if fallback_id:
                fb_model = db.aimodel.find_unique(
                    where={"id": fallback_id},
                    include={"provider": True}
                )
                if fb_model and fb_model.provider:
                    models.append(_to_dict(fb_model))
        
        return models
    except Exception as e:
        print(f"Error getting model with fallbacks: {e}")
        return []



def check_orchestrator_model(db, model_id):
    """Check if a model is an extraction orchestrator model."""
    try:
        model = db.aimodel.find_unique(where={"id": model_id})
        return bool(model.isOrchestrator) if model else False
    except Exception:
        return False

def check_sentiment_model(db, model_id):
    """Check if a model is a sentiment analysis model."""
    try:
        model = db.aimodel.find_unique(where={"id": model_id})
        return bool(model.isSentiment) if model else False
    except Exception:
        return False


def parse_key_value_patterns(content, expected_keys):
    """
    Parse key:value patterns from user content.
    
    Supports formats:
    - key: valor
    - key:valor  
    - key : valor
    
    Returns dict of {key: value} for matched keys, empty dict if no matches.
    """
    if not expected_keys:
        return {}
    
    result = {}
    
    for key in expected_keys:
        # Match patterns like "CEP_origem: 01310-100" or "CEP_origem:01310-100"
        # Capture value until comma, newline, or common separators
        pattern = rf'{re.escape(key)}\s*:\s*([^\n,;|]+)'
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                result[key] = value
    
    return result

def execute_orchestrator_request(request, db, messages, model_data, selected_functions=None, output_schema=None, compiled_rules=None):
    """
    Execute orchestrator request with hybrid AI classifier.
    
    Flow:
    1. Get user's enabled functions and their keys
    2. AI Classifier extracts values by user-defined keys
    3. Functions process the classified values
    4. AI Guardrail as fallback if function fails
    """
    from .orchestrator.registry import get_function
    from .key_rotation import get_next_api_key
    
    is_orch_client = getattr(request, 'auth_method', None) == 'orch_client'
    user_id = getattr(request.user, 'id', None)
    
    # Check Balance
    allowed, error_response = check_user_balance(request)
    if not allowed:
        return error_response

    start_time = time.time()
    total_cost = 0.0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    ai_was_called = False
    
    # Get the user content and system prompt from messages
    user_content = ""
    system_prompt = ""
    conversation_context = ""
    
    for msg in messages:
        if msg.get("role") == "system":
            system_prompt = msg.get("content", "")
        elif msg.get("role") in ["user", "assistant"]:
            role_label = "Usuário" if msg.get("role") == "user" else "Assistente"
            conversation_context += f"{role_label}: {msg.get('content', '')}\n"
            
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
            break
    
    if not user_content:
        return JsonResponse({"error": "No user message found"}, status=400)
    
    # Validate selected_functions is provided
    if not selected_functions or len(selected_functions) == 0:
        return JsonResponse({
            "error": {
                "message": "O parâmetro 'functions' é obrigatório para modelos do tipo orchestrator. Especifique quais funções usar, ex: \"functions\": [\"extract_cep\", \"extract_phones\"]",
                "type": "invalid_request_error",
                "code": "missing_functions"
            }
        }, status=400)
    
    # Build IN clause for selected functions
    placeholders = ', '.join(['?' for _ in selected_functions])
    
    if is_orch_client:
        # OrchClient (n8n): use OrchFunction directly, no UserFunction needed
        orch_funcs = db.orchfunction.find_many(
            where={"enabled": True, "name": {"in": list(selected_functions)}}
        )
        
        if not orch_funcs or len(orch_funcs) == 0:
            all_enabled = db.orchfunction.find_many(where={"enabled": True})
            enabled_names = [f.name for f in all_enabled]
            invalid = [f for f in selected_functions if f not in enabled_names]
            return JsonResponse({
                "error": {
                    "message": f"Funções não encontradas ou não habilitadas: {', '.join(invalid)}. Funções disponíveis: {', '.join(enabled_names) if enabled_names else 'nenhuma'}",
                    "type": "invalid_request_error",
                    "code": "invalid_functions"
                }
            }, status=400)
            
        uf_list = []
        for of in orch_funcs:
            uf_list.append({
                "func_name": of.name,
                "displayName": of.displayName,
                "description": of.description,
                "pricePerUnit": of.pricePerUnit,
                "unitSize": of.unitSize,
                "enrichPricePerUnit": of.enrichPricePerUnit,
                "requiresAi": of.requiresAi,
                "defaultModelId": of.defaultModelId,
                "functionName": of.name,
                "enabled": 1,
                "outputTemplate": None,
                "config": None
            })
        user_functions = uf_list
    else:
        # Regular user: fetch UserFunctions then OrchFunctions
        user_funcs = db.userfunction.find_many(
            where={"userId": user_id, "enabled": True, "functionName": {"in": list(selected_functions)}}
        )
        
        uf_names = [uf.functionName for uf in user_funcs]
        orch_funcs = db.orchfunction.find_many(
            where={"enabled": True, "name": {"in": uf_names}}
        )
        orch_dict = {of.name: of for of in orch_funcs}
        
        uf_list = []
        for uf in user_funcs:
            of = orch_dict.get(uf.functionName)
            if of:
                uf_list.append({
                    "id": uf.id,
                    "functionName": uf.functionName,
                    "enabled": uf.enabled,
                    "outputTemplate": uf.outputTemplate,
                    "config": uf.config,
                    "func_name": of.name,
                    "displayName": of.displayName,
                    "description": of.description,
                    "pricePerUnit": of.pricePerUnit,
                    "unitSize": of.unitSize,
                    "enrichPricePerUnit": of.enrichPricePerUnit,
                    "requiresAi": of.requiresAi,
                    "defaultModelId": of.defaultModelId
                })
        user_functions = uf_list
        
        if not user_functions or len(user_functions) == 0:
            all_user_funcs = db.userfunction.find_many(where={"userId": user_id, "enabled": True})
            enabled_names = [uf.functionName for uf in all_user_funcs]
            invalid = [f for f in selected_functions if f not in enabled_names]
            
            return JsonResponse({
                "error": {
                    "message": f"Funções não encontradas ou não habilitadas: {', '.join(invalid)}. Funções disponíveis: {', '.join(enabled_names) if enabled_names else 'nenhuma'}",
                    "type": "invalid_request_error",
                    "code": "invalid_functions"
                }
            }, status=400)
    
    # Get all user keys for enabled functions
    func_keys = {}
    all_key_names = []
    for uf in user_functions:
        if isinstance(uf, dict):
            func_name = uf.get("func_name") or uf.get("functionName")
            if is_orch_client:
                # OrchClient: no UserFunctionKey, keys come from OrchFunction defaults
                keys = db.userfunctionkey.find_many(
                    where={"functionName": func_name},
                    take=50
                )
            else:
                keys = db.userfunctionkey.find_many(
                    where={"userId": user_id, "functionName": func_name}
                )
            if keys:
                key_list = [{"key": k.key, "description": k.description} for k in keys]
                func_keys[func_name] = key_list
                all_key_names.extend([k["key"] for k in key_list])
    
    # Step 1: Try to detect key:value patterns in user content
    pattern_result = parse_key_value_patterns(user_content, all_key_names)
    
    # Step 2: If patterns found, use them; otherwise use AI Classifier
    classifier_result = {}
    if pattern_result:
        # Map pattern results to functions
        for func_name, keys in func_keys.items():
            classifier_result[func_name] = {}
            for k in keys:
                if k["key"] in pattern_result:
                    classifier_result[func_name][k["key"]] = pattern_result[k["key"]]
    elif func_keys:
        classifier_result, usage = run_ai_classifier(db, model_data, user_content, func_keys, system_prompt=system_prompt, conversation_context=conversation_context)
        
        # Accumulate usage
        if usage:
            total_prompt_tokens += usage.get("prompt_tokens", 0)
            total_completion_tokens += usage.get("completion_tokens", 0)
            if usage.get("completion_tokens", 0) > 0:
                ai_was_called = True
    
    # Step 2: Execute functions with classified data
    results = {}
    print(f'[Orchestrator] Starting with selected_functions={selected_functions}, output_schema={output_schema}')
    
    for uf in user_functions:
        if not isinstance(uf, dict):
            continue
        
        func_name = uf.get("func_name") or uf.get("functionName")
        price_per_unit = uf.get("pricePerUnit", 0) or 0
        unit_size = uf.get("unitSize", 1000) or 1000
        requires_ai = bool(uf.get("requiresAi"))
        default_model_id = uf.get("defaultModelId")
        
        # Parse user config for this function
        func_config = {}
        raw_config = uf.get("config")
        if raw_config:
            try:
                func_config = json.loads(raw_config) if isinstance(raw_config, str) else raw_config
            except (json.JSONDecodeError, TypeError):
                func_config = {}
        
        enrich_enabled = bool(func_config.get("enrich", False))
        
        # Enrichment cost from admin config: R$ enrichPricePerUnit per unitSize requests
        enrich_price_per_unit = float(uf.get("enrichPricePerUnit", 0.05) or 0.05)
        enrich_cost_per_request = enrich_price_per_unit / unit_size if unit_size > 0 else 0
        
        # Get classified values for this function
        classified_values = classifier_result.get(func_name, {})
        
        # Load function
        func = get_function(func_name)
        if not func:
            continue
        
        # Absence markers from AI classifier
        ABSENCE_MARKERS = {
            "", "não fornecido", "nao fornecido", "não informado", "nao informado",
            "ausente", "n/a", "na", "none", "null", "vazio", "-", "não consta",
            "nao consta", "não disponível", "nao disponivel"
        }
        
        # ══════════════════════════════════════════════════════════════
        # DIRECT BYPASS: Functions that run directly against full text
        # — they don't need AI classification or per-key execution.
        # Includes: converters (convert_units, convert_mass) and
        # transformers (normalize_text).
        # ══════════════════════════════════════════════════════════════
        BYPASS_FUNCTIONS = {'convert_units', 'convert_mass', 'normalize_text'}
        
        if func_name in BYPASS_FUNCTIONS:
            # Execute function directly on full user content
            func_result = {}
            try:
                if func_name == 'convert_units':
                    target_unit = func_config.get("target_unit", "m")
                    raw_result = func(user_content, target_unit=target_unit)
                elif func_name == 'convert_mass':
                    target_unit = func_config.get("target_unit", "kg")
                    raw_result = func(user_content, target_unit=target_unit)
                elif func_name == 'normalize_text':
                    raw_result = func(user_content)
                    # normalize_text always produces output — mark as found
                    if isinstance(raw_result, dict) and raw_result.get("normalized"):
                        raw_result["found"] = True
                        raw_result["count"] = 1
                
                if isinstance(raw_result, dict) and (raw_result.get("found", False) or raw_result.get("count", 0) > 0):
                    func_result = raw_result  # Direct result, not nested under _raw
            except Exception as e:
                print(f"[Orchestrator] Bypass function {func_name} failed: {e}")
            
            if func_result:
                results[func_name] = func_result
                if price_per_unit > 0:
                    cost = price_per_unit / unit_size
                    total_cost += cost
            continue  # Skip the general per-key execution below
        
        # ══════════════════════════════════════════════════════════════
        # GENERAL PATH: Execute function with classified values per key
        # ══════════════════════════════════════════════════════════════
        func_result = {}
        
        # Se nenhuma chave foi classificada (ex: output_schema vazio), executa no texto completo
        if not classified_values:
            classified_values = {"content": user_content}
            
        for key_name, value in classified_values.items():
            str_value = str(value).strip() if value else ""
            
            # Check if classifier marked this as absent
            if not str_value or str_value.lower() in ABSENCE_MARKERS:
                func_result[key_name] = "ausente"
                continue
            
            try:
                # Pass enrich flag for functions that support it
                if enrich_enabled and func_name in ('extract_cep', 'extract_cpfcnpj'):
                    result = func(str_value, enrich=True)
                else:
                    result = func(str_value)
                if isinstance(result, dict):
                    if result.get("found", False) or result.get("count", 0) > 0:
                        func_result[key_name] = result
                    elif result.get("status") == "ausente":
                        # Function validated and determined value is invalid
                        func_result[key_name] = "ausente"
                    else:
                        func_result[key_name] = "ausente"
            except Exception as e:
                print(f"[Orchestrator] Function {func_name} failed for key {key_name}: {e}")
                func_result[key_name] = "ausente"
        
        # Always try raw content to find additional valid data the classifier missed
        try:
            if enrich_enabled and func_name in ('extract_cep', 'extract_cpfcnpj'):
                raw_result = func(user_content, enrich=True)
            else:
                raw_result = func(user_content)
            if isinstance(raw_result, dict) and (raw_result.get("found", False) or raw_result.get("count", 0) > 0):
                func_result["_raw"] = raw_result
                
                # Add enrichment cost based on admin config
                if enrich_enabled and func_name == 'extract_cep':
                    enriched_count = raw_result.get("count", 0)
                    if enriched_count > 0:
                        total_cost += enrich_cost_per_request * enriched_count
                
                # Add enrichment cost for CNPJ (count only CNPJs, not CPFs)
                if enrich_enabled and func_name == 'extract_cpfcnpj':
                    cnpjs = raw_result.get("cnpjs", [])
                    enriched_cnpj_count = sum(1 for c in cnpjs if isinstance(c, dict) and c.get("enriched"))
                    if enriched_cnpj_count > 0:
                        total_cost += enrich_cost_per_request * enriched_cnpj_count
        except Exception as e:
            print(f"[Orchestrator] Raw function {func_name} failed: {e}")
        
        # Fallback: if all keys are absent and no raw, use AI guardrail
        has_real_data = any(v != "ausente" for k, v in func_result.items() if k != "_raw")
        if not has_real_data and requires_ai and default_model_id:
            ai_result, usage = run_ai_guardrail(db, default_model_id, user_content, func_name, func_keys.get(func_name, []), system_prompt=system_prompt)
            
            # Accumulate usage
            if usage:
                total_prompt_tokens += usage.get("prompt_tokens", 0)
                total_completion_tokens += usage.get("completion_tokens", 0)
                if usage.get("completion_tokens", 0) > 0:
                    ai_was_called = True

            if ai_result:
                func_result.update(ai_result)
        
        # Promote _raw data: when all user-defined keys are "ausente" but _raw found data,
        # use _raw as the primary result so the user sees the extracted values
        raw_data = func_result.get("_raw")
        if raw_data and isinstance(raw_data, dict) and raw_data.get("found"):
            non_raw_keys = {k: v for k, v in func_result.items() if k != "_raw"}
            all_absent = all(v == "ausente" for v in non_raw_keys.values()) if non_raw_keys else True
            if all_absent:
                # Replace absent keys with _raw data and remove _raw
                func_result = {"_resultado": raw_data}
        
        if func_result:
            results[func_name] = func_result
            if price_per_unit > 0:
                cost = price_per_unit / unit_size
                total_cost += cost
    
    # Calculate Token Cost
    # If no AI was called, charge for system prompt + user content (Base Cost)
    if total_prompt_tokens == 0:
        # Estimate tokens using len/4 (standard approximation when tiktoken not available)
        base_text = (system_prompt or "") + (user_content or "")
        base_tokens = int(len(base_text) / 4)
        total_prompt_tokens += base_tokens
    
    # Calculate cost using model pricing (per million tokens)
    cost_in = model_data.get("costPerInputToken", 0) or 0
    cost_out = model_data.get("costPerOutputToken", 0) or 0
    
    token_cost = (total_prompt_tokens / 1_000_000 * cost_in) + (total_completion_tokens / 1_000_000 * cost_out)
    total_cost += token_cost
    
    duration = int((time.time() - start_time) * 1000)
    
    # Deduct balance & log (only for real users, not OrchClient)
    if not is_orch_client:
        if total_cost > 0:
            db.user.update(where={"id": user_id}, data={"balance": {"decrement": total_cost}})
            db.transaction.create(data={
                "userId": user_id,
                "type": "DEBIT",
                "amount": total_cost,
                "description": f"Orchestrator: {len(results)} funções"
            })
    
    # Log execution
    db.orchexecution.create(
        data={
            "id": str(uuid.uuid4()),
            "userId": user_id if not is_orch_client else None,
            "clientId": user_id if is_orch_client else None,
            "functionName": ','.join(results.keys()),
            "input": user_content[:500],
            "output": json.dumps(results, ensure_ascii=False),
            "success": True,
            "usedAi": ai_was_called,
            "durationMs": duration
        }
    )
    
    # Log Metric for Dashboard
    if not is_orch_client:
        try:
            db.metric.create(data={
                "userId": user_id,
                "modelId": model_data.get("id"),
                "inputTokens": total_prompt_tokens,
                "outputTokens": total_completion_tokens,
                "cost": total_cost,
                "requestDurationMs": duration,
                "timestamp": timezone.now()
            })
        except Exception as e:
            print(f"[Orchestrator] Error logging metric: {e}")
            try:
                with open("/tmp/metrics_debug.log", "a") as f:
                    f.write(f"[{datetime.now()}] Metric Error: {e}\n")
            except:
                 pass
    
    # Format response
    raw_extractions = results
    
    # If output_schema is provided and NOT empty, use AI to restructure the output
    if output_schema and isinstance(output_schema, dict) and len(output_schema) == 0:
        # Ignore completely empty dicts {}
        output_schema = None
        
    if output_schema and results:
        structured = format_output_with_schema(
            db, model_data, results, output_schema, user_content, system_prompt=system_prompt, compiled_rules=compiled_rules
        )
        if structured:
            response_content = json.dumps(structured, ensure_ascii=False, indent=2)
        else:
            response_content = json.dumps({
                "extractions": results,
                "total_cost": total_cost,
                "duration_ms": duration
            }, ensure_ascii=False, indent=2)
    else:
        response_content = json.dumps({
            "extractions": results,
            "total_cost": total_cost,
            "duration_ms": duration
        }, ensure_ascii=False, indent=2)
    
    return JsonResponse({
        "id": f"orch-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "model": model_data.get("name", "orchestrator"),
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response_content},
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens
        }
    })


def run_ai_classifier(db, model_data, user_content, func_keys, system_prompt="", conversation_context=""):
    """
    Run AI to classify/extract values based on user-defined keys with contextual understanding.
    NOTE: system_prompt is accepted for signature compatibility but NOT sent to the LLM.
    The classifier only needs the extraction rules + user text — business rules are irrelevant here.
    Returns: (result_dict, usage_dict)
    """
    from .key_rotation import get_next_api_key
    
    # Build prompt with all keys from all functions
    keys_description = []
    for func_name, keys in func_keys.items():
        for k in keys:
            keys_description.append(f"- **{k['key']}**: {k['description']}")
    
    if not keys_description:
        return {}, {"prompt_tokens": 0, "completion_tokens": 0}
    
    # Lightweight classifier intro — NO system prompt injected (saves ~2000+ tokens per request)
    context_intro = "Você é um especialista em extração de dados de cotações de frete e documentos comerciais."
    
    prompt = f"""{context_intro}

TAREFA: Analise o texto abaixo (que pode ser formal, informal, ou transcrição de áudio) e extraia os valores para cada chave especificada.

## REGRAS DE INFERÊNCIA CONTEXTUAL (MUITO IMPORTANTE):
1. **Contexto de Remetente/Origem**: 
   - CEP, CNPJ, CPF ou endereço que aparecem PRÓXIMOS a palavras como "Remetente", "Emitente", "Origem", "Pagador", "Coleta", "sai de", "pegar em" → são dados de ORIGEM.
   - Exemplo: "sai de SP capital 01310-100" → 01310-100 é CEP de origem.

2. **Contexto de Destinatário/Destino**:
   - CEP, CNPJ, CPF ou endereço que aparecem PRÓXIMOS a palavras como "Destinatário", "Destino", "Entrega", "vai pra", "entregar em" → são dados de DESTINO.
   - Exemplo: "vai entregar lá em 88100-001" → 88100-001 é CEP de destino.

3. **Múltiplos CEPs/CNPJs**: 
   - Se houver dois CEPs e nenhum contexto verbal claro, o PRIMEIRO geralmente é origem e o SEGUNDO é destino.

4. **Variabilidade Linguística**:
   - Considere jargões logísticos e erros de digitação comuns em WhatsApp (ex: "vols", "cx", "kilos", "kg").
   - Se um valor for mencionado por extenso (ex: "vinte quilos", "duas caixas"), extraia o valor numérico.

5. **Normalização obrigatória**:
   - CEP: retornar APENAS 8 dígitos numéricos (ex: "01310-100" → "01310100")
   - CNPJ: retornar APENAS 14 dígitos numéricos (ex: "12.345.678/0001-90" → "12345678000190")
   - CPF: retornar APENAS 11 dígitos numéricos (ex: "123.456.789-00" → "12345678900")
   - Valores monetários: retornar apenas números com ponto decimal (ex: "R$ 5.908,96" → "5908.96")
   - Peso/Volume: retornar apenas número (ex: "165 Kg" → "165")

5. **FORMATO ESTRUTURADO PARA ENDEREÇOS**:
   Quando a chave for de endereço, retorne um OBJETO com:
   {{
     "logradouro": "nome da rua/avenida",
     "numero": "número",
     "complemento": "apartamento/sala/etc ou null",
     "bairro": "nome do bairro ou null",
     "cidade": "cidade",
     "uf": "sigla do estado",
     "cep": "8 dígitos"
   }}

6. **FORMATO ESTRUTURADO PARA TELEFONES**:
   Quando a chave for de telefone/contato, retorne um OBJETO com:
   {{
     "ddd": "2 dígitos do DDD",
     "numero": "número sem DDD",
     "codigo_pais": "código do país ou null se Brasil"
   }}

7. **FORMATO ESTRUTURADO PARA VALORES MONETÁRIOS**:
   Quando a chave for de valor/preço, retorne um OBJETO com:
   {{
     "valor": numero decimal (ex: 5908.96),
     "moeda": "BRL" ou outra moeda se especificada
   }}

8. **FORMATO ESTRUTURADO PARA DIMENSÕES**:
   Quando a chave for de dimensão/cubagem/medidas, retorne um OBJETO com:
   {{
     "largura": numero em metros,
     "altura": numero em metros,
     "comprimento": numero em metros,
     "cubagem_total": numero em m³ (calcular se não fornecido),
     "unidade": "m" ou "cm"
   }}
   Obs: Converter cm para metros quando necessário.

9. **FORMATO ESTRUTURADO PARA QUANTIDADES/PESO**:
   Quando a chave for de quantidade/volume/peso, retorne um OBJETO com:
   {{
     "quantidade": numero inteiro de volumes,
     "peso": numero em kg,
     "tipo_volume": "caixa", "pallet", "fardo", etc.
   }}

10. Se um campo NÃO existir no texto, retorne null.

## CHAVES A EXTRAIR:
{chr(10).join(keys_description)}

## HISTÓRICO DA CONVERSA (Contexto):
\"\"\"
{conversation_context}
\"\"\"

## MENSAGEM ATUAL PARA ANÁLISE:
\"\"\"
{user_content}
\"\"\"

## RESPOSTA:
Responda APENAS com JSON válido, sem explicações ou markdown:
{{"chave1": "valor_ou_objeto", "chave2": "valor_ou_objeto"}}"""
    
    model_info = db.aimodel.find_unique(
        where={"id": model_data.get("id")},
        include={"provider": True}
    )
    
    if not model_info or not model_info.provider:
        return {}, {"prompt_tokens": 0, "completion_tokens": 0}
    
    m = {
        "providerModelId": model_info.providerModelId,
        "baseUrl": model_info.provider.baseUrl,
        "apiKey": model_info.provider.apiKey,
        "providerId": model_info.providerId
    }
    api_key = get_next_api_key(m.get("providerId")) or m.get("apiKey")
    
    try:
        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json={
                "model": m.get("providerModelId"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            # Parse JSON from response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1].replace("json", "").strip()
            
            classified = json.loads(content)
            
            # Map results back to functions
            result = {}
            for func_name, keys in func_keys.items():
                result[func_name] = {}
                for k in keys:
                    if k["key"] in classified and classified[k["key"]]:
                        result[func_name][k["key"]] = classified[k["key"]]
            
            # Extract usage
            usage = data.get("usage", {})
            usage_data = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0)
            }
            
            return result, usage_data
    except Exception as e:
        print(f"[AI Classifier] Error: {e}")
    
    return {}, {"prompt_tokens": 0, "completion_tokens": 0}


def run_ai_guardrail(db, model_id, user_content, func_name, keys, system_prompt=""):
    """
    AI fallback to extract data when function fails.
    Uses the client's system_prompt for business context when available.
    Returns: (result_dict, usage_dict)
    """
    from .key_rotation import get_next_api_key
    
    if not keys:
        return {}, {"prompt_tokens": 0, "completion_tokens": 0}
    
    keys_str = "\n".join([f"- {k['key']}: {k['description']}" for k in keys])
    
    context_intro = system_prompt + "\n\n" if system_prompt else ""
    prompt = f"""{context_intro}Extraia os seguintes dados do texto:

{keys_str}

Texto: "{user_content}"

Responda APENAS no formato JSON:
{{"key1": "valor1", "key2": "valor2"}}"""
    
    model_info = db.aimodel.find_unique(
        where={"id": model_id},
        include={"provider": True}
    )
    
    if not model_info or not model_info.provider:
        return {}, {"prompt_tokens": 0, "completion_tokens": 0}
    
    m = {
        "providerModelId": model_info.providerModelId,
        "baseUrl": model_info.provider.baseUrl,
        "apiKey": model_info.provider.apiKey,
        "providerId": model_info.providerId
    }
    api_key = get_next_api_key(m.get("providerId")) or m.get("apiKey")
    
    try:
        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json={
                "model": m.get("providerModelId"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1].replace("json", "").strip()
            
            # Extract usage
            usage = data.get("usage", {})
            usage_data = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0)
            }
            
            return json.loads(content), usage_data
    except Exception as e:
        print(f"[AI Guardrail] Error: {e}")
    
    return {}, {"prompt_tokens": 0, "completion_tokens": 0}


def _build_extraction_summary(extraction_results):
    """
    Pre-process raw extraction results into a clean, structured text summary.
    Returns (summary_text, enrichment_dict, deterministic_overrides) — much easier for AI to parse than raw JSON.
    The deterministic_overrides dict contains field values that MUST override AI output.
    """
    sections = []
    enrichment = {}
    overrides = {}

    for func_name, func_result in extraction_results.items():
        if not isinstance(func_result, dict):
            continue
        if func_name == "normalize_text":
            continue

        # --- extract_cpfcnpj ---
        if func_name == "extract_cpfcnpj":
            lines = ["### DOCUMENTOS (CPF/CNPJ):"]
            # Resolve the actual data source — may be under _raw, _resultado, or direct keys
            raw = func_result.get("_raw", {})
            resultado = func_result.get("_resultado", {})
            # Collect documents per role for pagador classification
            doc_remetente = None
            doc_destinatario = None
            doc_pagador = None
            for key, val in sorted(func_result.items()):
                if not key.startswith("_"):
                    lines.append(f"- {key}: {val}")
                    key_lower = key.lower()
                    # Extract the raw numeric CNPJ/CPF from nested result dict
                    doc_num = None
                    if isinstance(val, dict):
                        for c in val.get("cnpjs", []):
                            doc_num = str(c.get("raw", "")).strip()
                            break
                        if not doc_num:
                            for c in val.get("cpfs", []):
                                doc_num = str(c.get("raw", "")).strip()
                                break
                    elif val and val != "ausente":
                        doc_num = str(val).replace(".", "").replace("-", "").replace("/", "").strip()
                    if doc_num:
                        if "remetente" in key_lower:
                            doc_remetente = doc_num
                        elif "destinat" in key_lower:
                            doc_destinatario = doc_num
                        elif "pagador" in key_lower:
                            doc_pagador = doc_num
            # When all keys were "ausente" and data was promoted to _resultado or _raw,
            # extract CNPJs from the raw extraction and match them to user text context
            raw_source = resultado if resultado else raw
            cnpjs = raw_source.get("cnpjs", [])
            all_raw_cnpjs = [str(c.get("raw", "")).strip() for c in cnpjs if isinstance(c, dict)]
            for cnpj_data in cnpjs:
                cd = cnpj_data.get("company_data")
                if cd:
                    label = f"empresa_{cnpj_data.get('raw', '')}"
                    enrichment[label] = cd
                    lines.append(f"  → {cnpj_data.get('formatted','')}: {cd.get('razao_social','')} ({cd.get('situacao_cadastral','')})")
                    addr = cd.get("endereco", {})
                    if addr:
                        enrichment[f"endereco_empresa_{cnpj_data.get('raw','')}"] = addr
            # If we didn't get doc roles from classified keys, try to match from user text context
            if (not doc_remetente or not doc_destinatario or not doc_pagador) and len(all_raw_cnpjs) >= 2:
                for cnpj_data in cnpjs:
                    ctx = cnpj_data.get("context", "").lower()
                    raw_num = str(cnpj_data.get("raw", "")).strip()
                    if not doc_remetente and "remetente" in ctx:
                        doc_remetente = raw_num
                    elif not doc_destinatario and "destinat" in ctx:
                        doc_destinatario = raw_num
                    elif not doc_pagador and "pagador" in ctx:
                        doc_pagador = raw_num
            if all_raw_cnpjs:
                lines.append(f"- CNPJs encontrados: {', '.join(all_raw_cnpjs)}")
            # Deterministic pagador classification
            if doc_pagador and doc_remetente and doc_destinatario:
                if doc_pagador == doc_remetente:
                    pagador_class = "cif"
                elif doc_pagador == doc_destinatario:
                    pagador_class = "fob"
                else:
                    pagador_class = "terceiro"
                lines.append(f"- PAGADOR CLASSIFICADO: {pagador_class}")
                overrides["pagador"] = pagador_class
            elif doc_pagador:
                lines.append(f"- PAGADOR: documento {doc_pagador} (sem remetente/destinatário para classificar cif/fob)")
            sections.append("\n".join(lines))

        # --- extract_cep ---
        elif func_name == "extract_cep":
            lines = ["### CEPs:"]
            raw = func_result.get("_raw", {})
            ceps_list = raw.get("ceps", [])
            for key, val in sorted(func_result.items()):
                if key.startswith("_"):
                    continue
                cep_num = str(val).replace("-", "").replace(".", "").strip()
                cep_info = ""
                for c in ceps_list:
                    if c.get("cep") == cep_num:
                        addr = c.get("address", {})
                        city = addr.get("cidade", "")
                        state = addr.get("estado", "")
                        street = addr.get("logradouro", "")
                        if city:
                            cep_info = f" → {street}, {city}/{state}"
                        if addr:
                            enrichment[f"endereco_{cep_num}"] = addr
                lines.append(f"- {key}: {cep_num}{cep_info}")
            lines.append("CONTEXTO: Remetente = quem ENVIA = ORIGEM. Destinatário = quem RECEBE = DESTINO.")
            sections.append("\n".join(lines))

        # --- convert_mass ---
        elif func_name == "convert_mass":
            lines = ["### PESO (convert_mass):"]
            mass_data = None
            for key, val in func_result.items():
                if key.startswith("_"):
                    continue
                if isinstance(val, dict) and val.get("found"):
                    mass_data = val
                    break
            if not mass_data and func_result.get("found"):
                mass_data = func_result
            if mass_data:
                for m in mass_data.get("measurements", []):
                    lines.append(f"- Original: \"{m.get('original','')}\"")
                    lines.append(f"- Valor numérico: {m.get('converted_value','')} {m.get('target_unit','')}")
                    if m.get("extenso"):
                        lines.append(f"- Por extenso: \"{m.get('extenso','')}\"")
                peso_num = mass_data.get("peso_numerico", [])
                peso_ext = mass_data.get("peso_extenso", [])
                if peso_num:
                    lines.append(f"- peso_numerico: {peso_num}")
                if peso_ext:
                    lines.append(f"- peso_extenso: {peso_ext}")
                lines.append("IMPORTANTE: Inclua AMBOS os valores (numérico E por extenso) no JSON de saída.")
            sections.append("\n".join(lines))

        # --- convert_units ---
        elif func_name == "convert_units":
            lines = ["### DIMENSÕES (convert_units) — JÁ CONVERTIDAS PARA METROS:"]
            units_data = func_result
            for check_key in ("_resultado", "_raw"):
                if check_key in func_result and isinstance(func_result[check_key], dict):
                    units_data = func_result[check_key]
                    break
            dim_groups = units_data.get("dimension_groups", [])
            fmt_dims = units_data.get("formatted_dimensions", [])
            # Build extenso from the CONVERTED formatted dimensions (already in meters)
            dims_extenso = []
            for fd in fmt_dims:
                # Handle quantity prefix (e.g. "20=0.2x0.3x0.4")
                qty_prefix = ""
                dim_part = str(fd)
                if "=" in dim_part:
                    qty_str, dim_part = dim_part.split("=", 1)
                    qty_prefix = f"{qty_str} unidades de "
                parts = dim_part.split("x")
                if len(parts) == 3:
                    dims_extenso.append(f"{qty_prefix}{parts[0]}m x {parts[1]}m x {parts[2]}m (Altura x Largura x Comprimento)")
                else:
                    dims_extenso.append(f"{qty_prefix}{dim_part}m")
            # Present only the final converted values — no original text to avoid confusion
            lines.append(f"- Total de conjuntos AxLxC: {len(fmt_dims)}")
            lines.append(f"- USAR PARA dimensoes_formatadas: {json.dumps(fmt_dims)}")
            if dims_extenso:
                lines.append(f"- USAR PARA dimensoes_extenso: {json.dumps(dims_extenso, ensure_ascii=False)}")
            lines.append("ATENÇÃO: Os valores acima JÁ estão em metros (convertidos de cm/mm/pol). Use-os EXATAMENTE como estão. NÃO use os valores originais do texto do usuário.")
            sections.append("\n".join(lines))

        # --- other functions ---
        else:
            lines = [f"### {func_name.upper()}:"]
            for key, val in func_result.items():
                if key.startswith("_"):
                    continue
                if isinstance(val, (dict, list)):
                    lines.append(f"- {key}: {json.dumps(val, ensure_ascii=False)}")
                else:
                    lines.append(f"- {key}: {val}")
            sections.append("\n".join(lines))

    return "\n\n".join(sections), enrichment, overrides


def _legacy_fallback_status(result, user_content="", extraction_results=None):
    """
    Fallback for agents WITHOUT compiled rules.
    Delegates to apply_compiled_rules using a minimal built-in ruleset
    so all status logic lives in one place (rules_compiler.py).
    """
    if not isinstance(result, dict):
        return
    from .rules_compiler import apply_compiled_rules
    _BUILTIN_RULES = json.dumps({
        "version": 1,
        "priority_order": ["completeness_audit"],
        "rules": [{
            "id": "completeness_audit", "type": "field_audit", "priority": 0,
            "required_fields": [
                "documento_remetente", "documento_destinatario",
                "cep_origem", "cep_destino",
                "volumes", "peso", "valor", "tipo_mercadoria"
            ],
            "on_complete": {"set_field": "status_cotacao", "value": "confirmar"},
            "on_incomplete": {"set_field": "status_cotacao", "value": "dado_faltante", "list_missing_in": "campos_faltantes"}
        }],
        "dynamic_variables": []
    }, ensure_ascii=False)
    apply_compiled_rules(result, _BUILTIN_RULES, user_content=user_content,
                         extraction_results=extraction_results or {}, system_prompt="")


def _apply_overrides(result, overrides):
    """
    Recursively walk a dict and replace values for keys that match the overrides.
    E.g. overrides={"pagador": "terceiro"} will set result[...]["pagador"] = "terceiro"
    at any nesting level.
    """
    if not isinstance(result, dict):
        return
    for key in result:
        if key in overrides:
            result[key] = overrides[key]
        elif isinstance(result[key], dict):
            _apply_overrides(result[key], overrides)


def _safe_json_loads(text):
    """
    Robust JSON parser that handles common LLM output issues:
    - Single quotes instead of double quotes
    - Trailing commas before } or ]
    - Markdown code blocks
    """
    import ast
    text = text.strip()
    # Remove markdown fences if still present
    if text.startswith("```"):
        text = text.split("```")[1].replace("json", "").strip()
    # 1. Try standard json.loads first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 2. Fix trailing commas (e.g. "value",\n} or "value",\n])
    import re
    fixed = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    # 3. Try ast.literal_eval (handles single quotes)
    try:
        result = ast.literal_eval(fixed)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass
    # 4. Replace single quotes with double quotes (naive but effective for simple cases)
    try:
        sq_fixed = fixed.replace("'", '"')
        return json.loads(sq_fixed)
    except json.JSONDecodeError:
        pass
    # 5. Give up — raise the original error
    return json.loads(text)


def _sanitize_schema(schema):
    """
    Strip all example values from the output schema, keeping only structure and key names.
    This prevents the AI from copying example values instead of deriving them.
    Replaces leaf values with null and lists with empty [].
    """
    if isinstance(schema, dict):
        return {k: _sanitize_schema(v) for k, v in schema.items()}
    elif isinstance(schema, list):
        return []
    else:
        return None


def format_output_with_schema(db, model_data, extraction_results, output_schema, user_content, system_prompt="", compiled_rules=None):
    """
    Use AI to restructure extraction results according to user-defined output schema.
    If compiled_rules are available, the AI only handles data formatting;
    business rules are applied deterministically via apply_compiled_rules().
    """
    from .key_rotation import get_next_api_key

    # Sanitize the schema: remove example values, keep only structure + keys
    if isinstance(output_schema, dict):
        sanitized = _sanitize_schema(output_schema)
        schema_str = json.dumps(sanitized, ensure_ascii=False, indent=2)
    else:
        schema_str = str(output_schema)

    # Pre-process extraction results into clean summary
    data_summary, enrichment, det_overrides = _build_extraction_summary(extraction_results)

    # Add _enrichment hint to schema if enrichment data exists
    enrichment_section = ""
    if enrichment:
        if isinstance(output_schema, dict):
            try:
                sanitized["_enrichment"] = {}
                schema_str = json.dumps(sanitized, ensure_ascii=False, indent=2)
            except:
                pass
        enrichment_section = f"""
### DADOS DE ENRIQUECIMENTO (empresa/endereço):
Inclua em '_enrichment' no JSON de saída com chaves descritivas (empresa_remetente, empresa_destinatario, endereco_origem, endereco_destino):
{json.dumps(enrichment, ensure_ascii=False, indent=2)}"""

    # System message: if compiled rules exist, AI only formats data (lighter prompt)
    if compiled_rules:
        system_message = "Você é um formatador de dados JSON. Sua ÚNICA tarefa é extrair e organizar dados no schema solicitado. NÃO defina status_cotacao, campos_faltantes ou count_erros_interacao — deixe-os null."
    elif system_prompt:
        system_message = system_prompt
    else:
        system_message = "Você é um formatador de dados JSON especializado em reorganizar dados extraídos no formato de schema solicitado."

    # Build user message — if compiled rules exist, AI only formats data (no business rules)
    if compiled_rules:
        user_message = f"""## TAREFA
Preencha APENAS os campos de DADOS do schema abaixo com valores REAIS derivados dos DADOS DAS FUNCTIONS.
Os campos de status (status_cotacao, campos_faltantes, count_erros_interacao) serão definidos por pós-processamento — deixe-os null.

NÃO invente valores. Se um dado não existe na mensagem ou nos resultados das functions, coloque null.

## REGRAS DE FORMATAÇÃO:
- CEPs: 8 dígitos SEM hífen (ex: 04206000)
- CNPJs: 14 dígitos SEM pontuação
- Dimensões: use as "Dimensões formatadas" das functions (já em metros, sem unidade)
- Responda APENAS com JSON válido, sem explicações, sem markdown, sem ```

## SCHEMA DE SAÍDA (preencha os nulls dos dados):
{schema_str}

## DADOS EXTRAÍDOS PELAS FUNCTIONS:
{data_summary}
{enrichment_section}

## TEXTO ORIGINAL DO USUÁRIO:
{user_content}

## RESPOSTA (JSON):"""
    else:
        user_message = f"""## TAREFA
Preencha TODOS os campos null do schema abaixo com valores REAIS derivados de:
1. DADOS DAS FUNCTIONS (seção abaixo) → documentos, CEPs, peso, dimensões, valor, volumes, mercadoria
2. REGRAS DO SEU SYSTEM PROMPT → status, tipo_dimensoes, pagador, campos_faltantes, count_erros, etc.

ATENÇÃO: O schema abaixo tem todos os valores como null. Você DEVE derivar cada valor.
NÃO invente valores. NÃO copie exemplos. Cada campo deve ser preenchido com base nos dados extraídos ou nas regras do system prompt.

## REGRAS DE FORMATAÇÃO:
- CEPs: 8 dígitos SEM hífen (ex: 04206000)
- CNPJs: 14 dígitos SEM pontuação
- Dimensões: use as "Dimensões formatadas" das functions (já em metros, sem unidade)
- campos_faltantes: lista dos campos da auditoria de completude que estão AUSENTES (lista vazia se tudo preenchido)
- Responda APENAS com JSON válido, sem explicações, sem markdown, sem ```

## SCHEMA DE SAÍDA (preencha os nulls):
{schema_str}

## DADOS EXTRAÍDOS PELAS FUNCTIONS:
{data_summary}
{enrichment_section}

## TEXTO ORIGINAL DO USUÁRIO:
{user_content}

## RESPOSTA (JSON):"""

    model_info = db.aimodel.find_unique(
        where={"id": model_data.get("id")},
        include={"provider": True}
    )
    
    if not model_info or not model_info.provider:
        return None
    
    m = {
        "providerModelId": model_info.providerModelId,
        "baseUrl": model_info.provider.baseUrl,
        "apiKey": model_info.provider.apiKey,
        "providerId": model_info.providerId
    }
    api_key = get_next_api_key(m.get("providerId")) or m.get("apiKey")
    
    # Debug log: what we're sending to the formatter
    has_sp = bool(system_prompt)
    print(f"[Formatter] Model: {m.get('providerModelId')} | system_prompt present: {has_sp} | system_msg length: {len(system_message)} | user_msg length: {len(user_message)}")
    
    try:
        payload = {
            "model": m.get("providerModelId"),
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.1
        }
        
        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            content = content.strip()
            
            # Debug log: raw formatter response
            print(f"[Formatter] Raw response ({len(content)} chars): {content[:500]}...")
            
            if content.startswith("```"):
                content = content.split("```")[1].replace("json", "").strip()
            
            result = _safe_json_loads(content)
            print(f"[Formatter] Parsed OK. Top-level keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            
            # Apply deterministic overrides (values AI cannot be trusted to produce)
            if det_overrides and isinstance(result, dict):
                print(f"[Formatter] Applying overrides: {det_overrides}")
                _apply_overrides(result, det_overrides)
            
            # Apply compiled rules OR legacy hardcoded post-processing
            if compiled_rules and isinstance(result, dict):
                from .rules_compiler import apply_compiled_rules
                print(f"[Formatter] Applying compiled rules")
                result = apply_compiled_rules(
                    result,
                    compiled_rules,
                    user_content=user_content,
                    extraction_results=extraction_results,
                    system_prompt=system_prompt
                )
            elif isinstance(result, dict):
                # Legacy fallback: delegates to apply_compiled_rules with built-in minimal ruleset
                _legacy_fallback_status(result, user_content, extraction_results)
            
            return result
        else:
            print(f"[Formatter] API error: status={resp.status_code} body={resp.text[:300]}")
    except json.JSONDecodeError as je:
        print(f"[Formatter] JSON parse error: {je} | raw content: {content[:300]}")
    except Exception as e:
        print(f"[Formatter] Error: {e}")
    
    return None

async def execute_completion(db, model_data, messages, stream):
    """
    Execute an async chat completion request to a specific model/provider.
    Returns (success, response_data_or_error)
    """
    from .key_rotation import get_next_api_key
    
    provider_id = model_data.get("providerId")
    base_url = model_data.get("baseUrl")
    provider_model_id = model_data.get("providerModelId") or model_data.get("name")
    
    api_key = await sync_to_async(get_next_api_key)(provider_id)
    if not api_key:
        api_key = model_data.get("apiKey")
    
    if not api_key:
        return False, "No API key available"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": provider_model_id,
        "messages": messages,
        "stream": stream
    }
    
    try:
        if stream:
            client = httpx.AsyncClient(timeout=60.0)
            req = client.build_request("POST", f"{base_url}/chat/completions", json=payload, headers=headers)
            resp = await client.send(req, stream=True)
            if resp.status_code == 200:
                return True, (client, resp)
            else:
                await resp.aread()
                err = resp.text[:200]
                await resp.aclose()
                await client.aclose()
                return False, f"Status {resp.status_code}: {err}"
        else:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                if resp.status_code == 200:
                    return True, resp.json()
                else:
                    return False, f"Status {resp.status_code}: {resp.text[:200]}"
    except httpx.TimeoutException:
        return False, "Request timeout"
    except Exception as e:
        return False, str(e)

def execute_sentiment_request(request, db, messages, model_data):
    """
    Execute sentiment analysis request pretending to be a model.
    """
    from .sentiment_controller import process_sentiment_analysis, parse_sentiment_input
    
    user_id = getattr(request.user, 'id', None)
    start_time = time.time()
    
    # Get user content
    user_content = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            user_content = msg.get("content", "")
            break
            
    if not user_content:
        return JsonResponse({"error": "No user message found"}, status=400)
    
    # Parse input (assume standard format: intent ``` context ``` status)
    parsed = parse_sentiment_input(user_content)
    
    intent = parsed["intent"]
    context = parsed["context"]
    status = parsed["status"]
    
    # Process
    # We pass the model_id itself as the fallback model for AI analysis
    result = process_sentiment_analysis(
        db,
        domain="transport",
        intent=intent,
        context=context,
        status=status,
        categories=[], # defaults
        exceptions=[], # defaults
        model_id=model_data.get("id"),
        system_prompt=None # Can extract from system messages if needed
    )
    
    # Format as JSON string for the content, as a model would return text/json
    response_content = json.dumps(result, ensure_ascii=False)
    
    # Log Metric for Sentiment Analysis
    try:
        duration = int((time.time() - start_time) * 1000)
        db.metric.create(data={
            "userId": request.user.id,
            "modelId": model_data.get("id"),
            "inputTokens": len(user_content.split()),
            "outputTokens": len(response_content.split()),
            "requestDurationMs": duration,
            "cost": 0.0 # Sentiment might be free or calculated differently
        })
    except Exception as e:
        print(f"Error logging sentiment metric: {e}")

    return JsonResponse({
        "id": f"sent-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "model": model_data.get("name", "sentiment-model"),
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": response_content},
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": len(user_content.split()),
            "completion_tokens": len(response_content.split()),
            "total_tokens": len(user_content.split()) + len(response_content.split())
        }
    })

@csrf_exempt
@login_required
async def chat_completions(request):
    """
    Standard OpenAI-compatible Chat Completions Endpoint with Fallback Support.
    """
    import json, time, uuid
    from datetime import datetime
    from django.http import JsonResponse, StreamingHttpResponse
    
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body)
        target_id = body.get("model")
        messages = body.get("messages", [])
        stream = body.get("stream", False)
        
        # Check Balance FIRST
        allowed, error_response = await sync_to_async(check_user_balance)(request)
        if not allowed:
            return error_response
        
        from .utils import get_db
        db = get_db()
        
        # 1. Resolve Target (Agent or Model)
        target_id_clean = target_id.strip() if target_id else ""
        try:
            agent = await sync_to_async(db.agent.find_unique)(where={"id": target_id_clean}, include={"model": True})
        except:
            agent = None
            
        if not agent:
            agent = await sync_to_async(db.agent.find_first)(where={"name": target_id_clean}, include={"model": True})
            
        model_id = None
        system_prompt = None
        
        if agent:
            model_id = agent.modelId
            system_prompt = agent.systemPrompt
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
        else:
            model_obj = await sync_to_async(db.aimodel.find_first)(where={"name": target_id_clean})
            if model_obj:
                model_id = model_obj.id
            else:
                model_id = target_id_clean
            
            # ── Auto-register agent from system message ──
            sys_msgs = [m for m in messages if m.get("role") == "system"]
            if sys_msgs:
                incoming_prompt = sys_msgs[0].get("content", "")
                if incoming_prompt and len(incoming_prompt) > 50:
                    from api.rules_compiler import compute_prompt_hash
                    prompt_hash = compute_prompt_hash(incoming_prompt)
                    existing = await sync_to_async(db.agent.find_first)(where={"promptHash": prompt_hash, "modelId": model_id})
                    if existing:
                        agent = existing
                    else:
                        model_obj = await sync_to_async(db.aimodel.find_unique)(where={"id": model_id})
                        agent_name = f"Auto: {model_obj.name}" if model_obj else f"Auto: {model_id[:12]}"
                        try:
                            agent = await sync_to_async(db.agent.create)(data={
                                "name": agent_name,
                                "systemPrompt": incoming_prompt,
                                "modelId": model_id,
                                "promptHash": prompt_hash,
                            })
                            print(f"[AgentAutoReg] Created agent '{agent_name}' ({agent.id})")
                        except Exception as e:
                            print(f"[AgentAutoReg] Failed: {e}")
                            agent = None
        
        # 2. Get model with fallback chain
        model_chain = await sync_to_async(get_model_with_fallbacks)(db, model_id)
        
        if not model_chain:
            return JsonResponse({"error": "Model or Agent not found"}, status=404)
        
        # 2.5 Check if this is an Orchestrator model
        primary_model = model_chain[0]
        is_orchestrator = await sync_to_async(check_orchestrator_model)(db, model_id)
        
        # 2.6 Rate Limit Check
        rpm_limit = primary_model.get("rpm", 0) or 0
        if rpm_limit > 0:
            user_id = getattr(request.user, 'id', 'orch_client')
            allowed, remaining = await sync_to_async(check_rate_limit)(model_id, user_id, rpm_limit)
            if not allowed:
                headers = await sync_to_async(get_rate_limit_headers)(model_id, user_id, rpm_limit)
                response = JsonResponse({
                    "error": {
                        "message": f"Rate limit exceeded. Limit: {rpm_limit} requests per minute.",
                        "type": "rate_limit_error",
                        "code": "rate_limit_exceeded"
                    }
                }, status=429)
                for key, value in headers.items():
                    response[key] = value
                return response
        
        if is_orchestrator:
            selected_functions = body.get("functions", [])
            output_schema = body.get("output_schema", None)
            compiled_rules = getattr(agent, 'compiledRules', None) if agent else None

            if agent and system_prompt and compiled_rules:
                from api.rules_compiler import check_prompt_changed, compute_prompt_hash
                stored_hash = getattr(agent, 'promptHash', None)
                if check_prompt_changed(system_prompt, stored_hash):
                    print(f"[RulesHash] Prompt changed for agent {agent.id}, triggering async recompilation")
                    rules_model_id = getattr(agent, 'rulesModelId', None)
                    if rules_model_id:
                        import threading
                        def _recompile():
                            try:
                                from api.rules_compiler import compile_prompt_rules
                                _db = get_db()
                                ok, new_rules, err = compile_prompt_rules(_db, system_prompt, rules_model_id)
                                if ok:
                                    new_hash = compute_prompt_hash(system_prompt)
                                    _db.agent.update(
                                        where={"id": agent.id},
                                        data={
                                            "compiledRules": json.dumps(new_rules, ensure_ascii=False),
                                            "rulesCompiledAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "rulesVersion": {"increment": 1},
                                            "promptHash": new_hash
                                        }
                                    )
                                    print(f"[RulesHash] Recompilation done for agent {agent.id}")
                                else:
                                    print(f"[RulesHash] Recompilation failed: {err}")
                            except Exception as e:
                                print(f"[RulesHash] Recompilation error: {e}")
                        threading.Thread(target=_recompile, daemon=True).start()

            # Execute orchestrator synchronously on a background thread
            return await sync_to_async(execute_orchestrator_request)(request, db, messages, primary_model, selected_functions=selected_functions, output_schema=output_schema, compiled_rules=compiled_rules)
            
        # 2.7 Check if Sentiment Model
        is_sentiment = await sync_to_async(check_sentiment_model)(db, model_id)
        if is_sentiment:
            # Execute sentiment synchronously on a background thread
            return await sync_to_async(execute_sentiment_request)(request, db, messages, primary_model)
        
        # 3. Try each model in chain until success
        start_time = time.time()
        last_error = None
        used_model = None
        
        for i, model_data in enumerate(model_chain):
            model_name = model_data.get("name", "Unknown")
            
            if i > 0:
                print(f"[Fallback] Trying model {i}: {model_name}")
            
            success, result = await execute_completion(db, model_data, messages, stream)
            
            if success:
                used_model = model_data
                
                if stream:
                    async def stream_and_log():
                        full_content = ""
                        usage_data = {}
                        client, resp = result
                        try:
                            async for chunk in resp.aiter_lines():
                                if chunk:
                                    decoded = chunk
                                    yield f"{decoded}\n\n"
                                    if decoded.startswith("data: ") and decoded != "data: [DONE]":
                                        try:
                                            chunk_json = json.loads(decoded[6:])
                                            delta = chunk_json.get("choices", [{}])[0].get("delta", {})
                                            if delta.get("content"):
                                                full_content += delta["content"]
                                            if chunk_json.get("usage"):
                                                usage_data = chunk_json["usage"]
                                        except:
                                            pass
                            yield "data: [DONE]\n\n"
                        except Exception as e:
                            print(f"[Stream] Error during streaming: {e}")
                        finally:
                            await resp.aclose()
                            await client.aclose()
                            
                            # Log metrics after stream completes
                            try:
                                is_orch = getattr(request, 'auth_method', None) == 'orch_client'
                                if not is_orch:
                                    input_tokens = usage_data.get("prompt_tokens", len(str(messages)) // 4)
                                    output_tokens = usage_data.get("completion_tokens", len(full_content) // 4)
                                    duration = int((time.time() - start_time) * 1000)
                                    cost_in = model_data.get("costPerInputToken", 0) or 0
                                    cost_out = model_data.get("costPerOutputToken", 0) or 0
                                    cost = (input_tokens * cost_in / 1_000_000) + (output_tokens * cost_out / 1_000_000)
                                    
                                    await sync_to_async(db.metric.create)(data={
                                        "userId": request.user.id,
                                        "modelId": model_data.get("id"),
                                        "inputTokens": input_tokens,
                                        "outputTokens": output_tokens,
                                        "requestDurationMs": duration,
                                        "cost": cost
                                    })
                                    if cost > 0:
                                        await sync_to_async(db.user.update)(
                                            where={"id": request.user.id},
                                            data={"balance": {"decrement": cost}}
                                        )
                                        fallback_note = f" (fallback {i})" if i > 0 else ""
                                        await sync_to_async(db.transaction.create)(data={
                                            "userId": request.user.id,
                                            "type": "DEBIT",
                                            "amount": cost,
                                            "description": f"Uso IA: {model_name}{fallback_note}"
                                        })
                                        try:
                                            from .stripe_services import check_and_trigger_auto_recharge
                                            await sync_to_async(check_and_trigger_auto_recharge)(request.user.id)
                                        except Exception as e:
                                            print(f"Auto-recharge check failed: {e}")
                            except Exception as e:
                                print(f"[Stream] Error logging metrics: {e}")
                    
                    response = StreamingHttpResponse(
                        stream_and_log(),
                        content_type='text/event-stream'
                    )
                    response['Cache-Control'] = 'no-cache'
                    response['X-Accel-Buffering'] = 'no'
                    return response
                
                # Handle normal response
                data = result
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                duration = int((time.time() - start_time) * 1000)
                
                cost_in = model_data.get("costPerInputToken", 0) or 0
                cost_out = model_data.get("costPerOutputToken", 0) or 0
                cost = (input_tokens * cost_in / 1_000_000) + (output_tokens * cost_out / 1_000_000)
                
                is_orch = getattr(request, 'auth_method', None) == 'orch_client'
                if not is_orch:
                    await sync_to_async(db.metric.create)(data={
                        "userId": request.user.id,
                        "modelId": model_data.get("id"),
                        "inputTokens": input_tokens,
                        "outputTokens": output_tokens,
                        "requestDurationMs": duration,
                        "cost": cost
                    })
                    
                    if cost > 0:
                        await sync_to_async(db.user.update)(
                            where={"id": request.user.id},
                            data={"balance": {"decrement": cost}}
                        )
                        
                        fallback_note = f" (fallback {i})" if i > 0 else ""
                        await sync_to_async(db.transaction.create)(data={
                            "userId": request.user.id,
                            "type": "DEBIT",
                            "amount": cost,
                            "description": f"Uso IA: {model_name}{fallback_note}"
                        })
                        
                        try:
                            from .stripe_services import check_and_trigger_auto_recharge
                            await sync_to_async(check_and_trigger_auto_recharge)(request.user.id)
                        except Exception as e:
                            print(f"Auto-recharge check failed: {e}")
                
                if i > 0:
                    data["_fallback_used"] = True
                    data["_actual_model"] = model_name
                
                return JsonResponse(data)
            
            else:
                last_error = result
                print(f"[Fallback] Model {model_name} failed: {result}")
        
        return JsonResponse({
            "error": f"All models failed. Last error: {last_error}"
        }, status=502)

    except Exception as e:
        import traceback
        print(f"[chat_completions] ERROR: {e}\n{traceback.format_exc()}")
        return JsonResponse({"error": str(e)}, status=400)
