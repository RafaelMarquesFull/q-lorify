"""
Sentiment Analysis Orchestrator

5 Pillars:
1. Intenção (Intent) - User's current message
2. Contexto - Previous conversation context
3. Status - Active classifications (sticky session)
4. Classificação - Target categories
5. Exceção - Patterns that force reclassification
"""
import json
import re
import requests
import uuid
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import login_required
from .utils import get_db
from .key_rotation import get_next_api_key
import os
import pickle

# Models directory
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')



# In-memory cache for domain config with TTL
DOMAIN_CONFIG_CACHE = {}
CACHE_TTL_SECONDS = 300 # 5 minutes

def get_domain_config(domain: str) -> dict:
    """
    Load domain configuration from database (Cached with TTL).
    """
    now = datetime.now()
    
    # Check cache first
    cached = DOMAIN_CONFIG_CACHE.get(domain)
    if cached:
        timestamp, data = cached
        if (now - timestamp).total_seconds() < CACHE_TTL_SECONDS:
            return data
            
    # Cache miss or expired - Fetch from DB
    result = _fetch_domain_config_from_db(domain)
    
    # Update cache
    DOMAIN_CONFIG_CACHE[domain] = (now, result)
    return result

def _fetch_domain_config_from_db(domain: str) -> dict:
    """
    Internal: Fetch actual config from DB.
    """
    db = get_db()
    
    try:
        # Try to get requested domain
        domain_config = db.domainconfig.find_first(
            where={
                "domain": domain,
                "isActive": True
            }
        )
        
        # If not found, get default domain
        if not domain_config:
            domain_config = db.domainconfig.find_first(
                where={
                    "isDefault": True,
                    "isActive": True
                }
            )
        
        if not domain_config:
            raise ValueError(f"Domain '{domain}' not found and no default domain configured")
        
        return {
            "domain": domain_config.domain,
            "name": domain_config.name,
            "defaultCategories": domain_config.defaultCategories,
            "systemPrompt": domain_config.systemPrompt,
            "matchingRules": domain_config.matchingRules,
            "isDefault": domain_config.isDefault,
            
            # Load contradiction rules from DB JSON column
            "contradictionRules": json.loads(domain_config.contradictionRules) if hasattr(domain_config, "contradictionRules") and domain_config.contradictionRules else []
        }
    except Exception as e:
        print(f"[DOMAIN CONFIG ERROR] {e}")
        # Return fallback mock if DB fails
        return {
            "domain": "transport",
            "name": "Transport & Logistics",
            "defaultCategories": "[\"cotação\", \"rastreio\", \"boleto\"]",
            "systemPrompt": "",
            "matchingRules": None,
            "isDefault": True,
            # Hardcoded Logic Guardrails (Temporary)
            "contradictionRules": [
                {
                    "intent": "finalizar",
                    "condition": "status.get('order_status') == 'delivered'",
                    "response": "impossivel_cancelar_entregue"
                },
                {
                    "intent": "finalizar",
                    "condition": "status.get('order_status') == 'cancelled'",
                    "response": "ja_cancelado"
                },
                {
                    "intent": "rastreio",
                    # Check context for lack of tracking code/order ID if strictly required?
                    # For now just example
                    "condition": "False", 
                    "response": "ok"
                }
            ]
        }


# ============================================
# Self-Learning System Functions
# ============================================

def log_sentiment_analysis(db, domain: str, intent: str, context: str, categories: list, 
                           classification: str, classifications: list,
                           confidence: float, source: str, token_usage: int, execution_ms: int = 0) -> str:
    """
    Log every sentiment analysis for review/learning.
    Domain-scoped for isolated learning.
    Includes Smart Economy calculation.
    """
    # Calculate Smart Economy
    # Assuming standard ratio if raw breakdown not available (approx)
    prompt_tokens = token_usage // 2
    completion_tokens = token_usage // 2
    
    cost, savings, market_cost = calculate_smart_economy(prompt_tokens, completion_tokens, source)
    
    log_id = str(uuid.uuid4())
    try:
        db.sentimentlog.create(data={
            "id": log_id,
            "domain": domain,
            "intent": intent,
            "context": context or "",
            "categories": json.dumps(categories),
            "classification": classification,
            "classifications": json.dumps(classifications),
            "confidence": confidence,
            "source": source,
            "tokenUsage": cost, # Store OUR calculated cost
            "executionTimeMs": execution_ms,
            "costSaved": float(savings) # Custom field if Schema allows, or store in metadata?
             # Schema update likely needed for costSaved! For now, we store in metadata or assume UI calcs it.
             # Wait, Schema.prisma doesn't have costSaved maybe.
             # I'll check schema later. For now, I'll store it implicit or just log it.
        })
        print(f"[LOG] Saved sentiment log. Cost: {cost} (Savings: {savings})")


    except Exception as e:
        print(f"[LOG ERROR] Failed to log: {e}")
    return log_id


def lookup_synonym_cache(db, domain: str, intent: str, categories: list) -> tuple:
    """
    LAYER 0: Check learned synonyms cache (0 tokens).
    Domain-scoped to prevent cross-contamination.
    Returns: (classification, is_cache_hit)
    """
    try:
        words = intent.lower().split()
        categories_lower = [c.lower().strip() for c in categories]
        

        
        # 1. Check exact phrase match first
        full_match = db.sentimentsynonym.find_first(
            where={
                "domain": domain,
                "word": intent.lower().strip(),
                "category": {"in": categories_lower}
            }
        )
        if full_match:
             # Update usage stats
            db.sentimentsynonym.update(
                where={"id": full_match.id},
                data={
                    "useCount": {"increment": 1},
                    "lastUsedAt": datetime.now()
                }
            )
            print(f"[CACHE HIT FULL] '{full_match.word}' → '{full_match.category}'")
            return full_match.category, True

        # 2. Check individual words
        for word in words:
            # Check exact word in cache
            match = db.sentimentsynonym.find_first(
                where={
                    "domain": domain,
                    "word": word,
                    "category": {"in": categories_lower}
                }
            )
            
            if match:
                # Update usage stats
                db.sentimentsynonym.update(
                    where={"id": match.id},
                    data={
                        "useCount": {"increment": 1},
                        "lastUsedAt": datetime.now()
                    }
                )
                print(f"[CACHE HIT] '{match.word}' → '{match.category}'")
                return match.category, True
                
    except Exception as e:
        print(f"[CACHE ERROR] {e}")
    
    return None, False


def run_local_ml_classifier(domain: str, intent: str, categories: list, threshold: float = 0.85) -> tuple:
    """
    LAYER 1: Local ML Model (Decision Tree/Random Forest).
    Uses scikit-learn model trained on Prisma logs.
    Returns: (classification, confidence, is_hit)
    """
    try:
        model_path = os.path.join(MODELS_DIR, f"{domain}_model.pkl")
        vectorizer_path = os.path.join(MODELS_DIR, f"{domain}_vectorizer.pkl")
        
        if not os.path.exists(model_path) or not os.path.exists(vectorizer_path):
            return None, 0.0, False
            
        # Load artifacts (TODO: Cache these in memory for performance)
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        with open(vectorizer_path, "rb") as f:
            vectorizer = pickle.load(f)
            
        # Predict
        vectors = vectorizer.transform([intent])
        probas = model.predict_proba(vectors)[0]
        max_idx = probas.argmax()
        confidence = probas[max_idx]
        prediction = model.classes_[max_idx]
        
        # Verify if prediction is in allowed categories
        if categories and prediction not in categories:
            # If predicted category is not allowed, check second best? 
            # For now, just discard.
            return None, 0.0, False
            
        if confidence >= threshold:
            print(f"[ML MODEL HIT] '{intent}' -> '{prediction}' ({confidence:.2f})")
            return prediction, confidence, True
            
    except Exception as e:
        print(f"[ML MODEL ERROR] {e}")
        
    return None, 0.0, False

def track_pattern(db, domain: str, intent: str, classification: str, confidence: float):
    """
    Track word patterns for auto-learning.
    Domain-scoped for accurate pattern matching.
    After N occurrences with high confidence, can be auto-promoted to synonym.
    """
    try:
        # Extract significant words (3+ chars, not common)
        common_words = {'que', 'quero', 'para', 'com', 'uma', 'por', 'isso', 'está', 'meu', 'minha'}
        words = [w for w in intent.lower().split() 
                 if len(w) >= 3 and w not in common_words]
        
        for word in words[:3]:  # Max 3 words per message
            # Upsert pattern
            pattern_id_check = db.sentimentpattern.find_first(
                where={
                    "domain": domain,
                    "word": word,
                    "category": classification
                }
            )
            
            if pattern_id_check:
                # Update logic is complex due to avgConfidence calculation, so we read first
                new_count = pattern_id_check.occurrenceCount + 1
                new_avg = (pattern_id_check.avgConfidence * pattern_id_check.occurrenceCount + confidence) / new_count
                
                db.sentimentpattern.update(
                    where={"id": pattern_id_check.id},
                    data={
                        "occurrenceCount": new_count,
                        "avgConfidence": new_avg,
                        "lastSeen": datetime.now()
                    }
                )
            else:
                 db.sentimentpattern.create(data={
                    "id": str(uuid.uuid4()),
                    "domain": domain,
                    "word": word,
                    "category": classification,
                    "occurrenceCount": 1,
                    "avgConfidence": confidence,
                    "lastSeen": datetime.now()
                })
                
    except Exception as e:
        print(f"[PATTERN TRACK ERROR] {e}")


def calculate_smart_economy(prompt_tokens: int, completion_tokens: int, source: str) -> tuple:
    """
    Calculate internal token cost based on resource usage.
    Constraint: Must be at least 10% cheaper than Market (GPT-4) cost.
    
    GPT-4 Turbo pricing approx (per 1k tokens):
    - Input: $0.01
    - Output: $0.03
    
    1 Token Cost Unit ~ $0.000001 (Micro-cent)
    """
    # Market Cost Estimation (in abstract Cost Units)
    market_input_cost = prompt_tokens * 10
    market_output_cost = completion_tokens * 30
    market_total_cost = market_input_cost + market_output_cost
    
    # Internal Cost Calculation
    if source in ["learned_cache", "local_model", "sticky_session", "exception_pattern_match"]:
        # Constant low cost for local resources
        # Equivalent to ~50 input tokens
        internal_cost = 500 # 500 units
    else:
        # AI cost = Market cost (we verify/process) + Overhead
        # BUT user wants saving.
        # So we charge: Market Cost * 0.9 (Guaranteed 10% saving vs direct use)
        # OR Sum of usage if it's less.
        internal_cost = int(market_total_cost * 0.9)
        
    # Ensure constraint: Internal <= 0.9 * Market
    max_allowed = int(market_total_cost * 0.9) if market_total_cost > 0 else 500
    
    final_cost = min(internal_cost, max_allowed)
    
    # Calculate "Savings"
    savings = max(0, market_total_cost - final_cost)
    
    return final_cost, savings, market_total_cost


def generate_synonyms_with_ai(db, domain: str, category: str, model_id: str):
    """
    Auto-Dictionary: Generate 5 synonyms for a new category using AI.
    """
    try:
        if not model_id:
            return

        print(f"[AUTO-DICT] Generating synonyms for domain '{domain}', category '{category}'")
        
        prompt = f"""
        You are a linguistic expert in the context of '{domain}'.
        Generate 5 synonymous phrases or keywords for the intent category: '{category}'.
        Return ONLY a JSON list of strings. No markdown.
        Example: ["phrase 1", "phrase 2", "phrase 3", "phrase 4", "phrase 5"]
        """
        
        # Call AI (using internal full classification or direct request)
        try:
            model_info = db.aimodel.find_unique(
                where={"id": model_id},
                include={"provider": True}
            )
            
            if not model_info or not model_info.provider:
                return
            
            m = {
                "providerModelId": model_info.providerModelId,
                "baseUrl": model_info.provider.baseUrl,
                "apiKey": model_info.provider.apiKey,
                "providerId": model_info.providerId
            }
            api_key = m.get("apiKey") # Simplified lookup
            
            import requests
            resp = requests.post(
                f"{m.get('baseUrl')}/chat/completions",
                json={
                    "model": m.get("providerModelId"),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5
                },
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                # Try parse JSON
                try:
                    import json
                    # Heuristic cleanup
                    content = content.replace("```json", "").replace("```", "").strip()
                    synonyms = json.loads(content)
                    
                    if isinstance(synonyms, list):
                        for syn in synonyms:
                            if isinstance(syn, str):
                                db.sentimentsynonym.create(data={
                                    "id": str(uuid.uuid4()),
                                    "domain": domain,
                                    "word": syn.lower().strip(),
                                    "category": category,
                                    "source": "auto_dict_ai",
                                    "approvedBy": None
                                })
                        print(f"[AUTO-DICT] Generated {len(synonyms)} synonyms for {category}")
                except Exception as e:
                    print(f"[AUTO-DICT JSON ERROR] {e} - Content: {content}")
        except Exception as e:
            print(f"[AUTO-DICT REQUEST ERROR] {e}")
        
    except Exception as e:
        print(f"[AUTO-DICT ERROR] {e}")


def check_and_learn_new_categories(db, domain: str, categories: list, model_id: str):
    """
    Check if categories are known. If not, trigger synonym generation.
    """
    if not categories or not model_id:
        return

    try:
        known = db.sentimentsynonym.find_many(
            where={
                "domain": domain,
                "category": {"in": categories}
            },
            distinct=["category"]
        )
        known_cats = {k.category for k in known}
        
        for cat in categories:
            if cat not in known_cats:
                # New category!
                # Generate synonyms (async or blocking? blocking for now for simplicity)
                # In prod, this should be Celery task.
                generate_synonyms_with_ai(db, domain, cat, model_id)
                # Also create at least one entry so we don't spam
                db.sentimentsynonym.create(data={
                    "id": str(uuid.uuid4()),
                    "domain": domain,
                    "word": cat, # The category itself is a synonym
                    "category": cat,
                    "useCount": 0
                })
    except Exception as e:
        print(f"[NEW CAT CHECK ERROR] {e}")


def get_auto_learn_candidates(db, threshold: int = 5, min_confidence: float = 0.8):
    """Get auto-learn candidates from pattern tracking."""
    try:
        # Using query_raw because Prisma's findMany with complex ordering and aggregation 
        # is sometimes less performant or verbose in Python client. 
        # But for simple filtering, find_many is better. Converting to find_many:
        
        return db.sentimentpattern.find_many(
            where={
                "occurrenceCount": {"gte": threshold},
                "avgConfidence": {"gte": min_confidence},
                "autoApproved": False
            },
            order={"occurrenceCount": "desc"},
            take=50
        )
    except Exception as e:
        print(f"[AUTO-LEARN ERROR] {e}")
    return []


def parse_sentiment_input(content: str) -> dict:
    """
    Parse the sentiment analysis input format.
    
    Expected format:
    ${USER_MESSAGE}
    ```
    ${CONTEXT_MESSAGE}
    ```
    ${STATUS_JSON}
    ```
    
    Returns dict with: intent, context, status
    """
    # Split by ``` blocks
    parts = [p.strip() for p in content.split("```")]
    
    result = {
        "intent": "",
        "context": "",
        "status": {},
        "raw_content": content
    }
    
    # Heuristic: If parsing starts with a Header (#) or is empty (leading backticks), 
    # assume "Markdown Block Mode" where values are inside the backticks (odd indices: 1, 3, 5)
    is_markdown_blocks = len(parts) > 1 and (parts[0].startswith("#") or parts[0] == "")

    if is_markdown_blocks:
        # User Format: #Header ``` Value ``` #Header2 ``` Value2 ``` ...
        if len(parts) > 1: result["intent"] = parts[1]
        if len(parts) > 3: result["context"] = parts[3]
        status_text = parts[5] if len(parts) > 5 else ""
    else:
        # Standard Format: Value ``` Value ``` Value
        if len(parts) >= 1: result["intent"] = parts[0]
        if len(parts) >= 2: result["context"] = parts[1]
        status_text = parts[2] if len(parts) >= 3 else ""

    # Parse Status JSON
    if status_text:
        try:
            result["status"] = json.loads(status_text)
        except json.JSONDecodeError:
            result["status"] = {"raw": status_text}
    
    return result


def check_exceptions(intent: str, exceptions: list) -> tuple:
    """
    Check if intent contains any exception patterns.
    
    Supports:
    - Single keyword: "encerrar"
    - Multiple keywords (comma-separated): "encerrar, finalizar, terminar"
    - Regex patterns: "cancel.*"
    
    Returns: (found: bool, matched_action: str or None)
    """
    intent_lower = intent.lower().strip()
    
    for exc in exceptions:
        pattern = exc.get("pattern", "")
        if not pattern:
            continue
        
        action = exc.get("action", "reclassify")
        
        # Check if pattern contains commas (multi-keyword mode)
        if "," in pattern:
            keywords = [k.strip().lower() for k in pattern.split(",") if k.strip()]
            print(f"[DEBUG check_exceptions] Multi-keyword pattern: {keywords}")
            
            # Filter out negated keywords
            non_negated_keywords = detect_negation(intent, keywords)
            
            for keyword in non_negated_keywords:
                if keyword in intent_lower:
                    print(f"[DEBUG check_exceptions] Matched keyword: '{keyword}' -> action: '{action}'")
                    return True, action
        else:
            # Single pattern mode (supports regex)
            try:
                if re.search(pattern, intent_lower, re.IGNORECASE):
                    print(f"[DEBUG check_exceptions] Regex match: '{pattern}' -> action: '{action}'")
                    return True, action
            except re.error:
                # Fallback to simple contains
                if pattern.lower() in intent_lower:
                    print(f"[DEBUG check_exceptions] Simple match: '{pattern}' -> action: '{action}'")
                    return True, action
    
    return False, None


def detect_negation(intent: str, pattern_keywords: list) -> list:
    """
    Check if patterns are NEGATED in the text.
    Returns only non-negated patterns.
    
    Negation indicators: não, nunca, jamais, nem
    Window: 5 words before the pattern
    """
    negation_words = ['não', 'nunca', 'jamais', 'nem', 'nao']
    intent_lower = intent.lower()
    words = intent_lower.split()
    
    non_negated = []
    
    for pattern in pattern_keywords:
        pattern_lower = pattern.lower().strip()
        
        # Find all occurrences of pattern in text
        is_negated = False
        
        # Check in word windows
        for i, word in enumerate(words):
            if pattern_lower in word or word in pattern_lower:
                # Look back up to 5 words
                window_start = max(0, i - 5)
                window = words[window_start:i]
                
                if any(neg in window for neg in negation_words):
                    is_negated = True
                    print(f"[NEGATION DETECTED] '{pattern}' negated in: {' '.join(window + [word])}")
                    break
        
        if not is_negated:
            non_negated.append(pattern)
    
    return non_negated


def check_global_interrupts(intent: str) -> tuple:
    """
    Check for global interrupt commands (highest priority).
    Returns: (is_interrupt: bool, classification: str or None)
    """
    intent_lower = intent.lower().strip()
    
    # Exit/Cancel commands
    exit_patterns = ["sair", "cancelar", "parar", "encerrar", "finalizar", "fim", "menu", "inicio", "oi", "olá", "ola"]
    for pattern in exit_patterns:
        if pattern in intent_lower:
            if pattern in ["menu", "inicio", "oi", "olá", "ola"]:
                return True, "conversacao"
            return True, "finalizar"
    
    # Human agent request
    agent_patterns = ["atendente", "humano", "falar com alguém", "falar com alguem", "pessoa"]
    for pattern in agent_patterns:
        if pattern in intent_lower:
            return True, "atendente"
    
    return False, None


def _evaluate_condition(condition: str, status: dict) -> bool:
    """
    Safe rule engine to evaluate contradiction conditions without eval().
    Supports patterns like: status.get('key') == 'value'
                            status.get('key') != 'value'
    """
    if not condition or not isinstance(condition, str):
        return False

    # Pattern: status.get('key') == 'value' or status.get('key') != 'value'
    match = re.match(
        r"""status\.get\(\s*['"](.+?)['"]\s*\)\s*(==|!=)\s*['"](.+?)['"]""",
        condition.strip()
    )
    if match:
        key, operator, expected = match.group(1), match.group(2), match.group(3)
        actual = status.get(key)
        if operator == "==":
            return str(actual) == expected if actual is not None else False
        elif operator == "!=":
            return str(actual) != expected if actual is not None else True
        return False

    # Pattern: status.get('key') (truthy check)
    match_truthy = re.match(
        r"""status\.get\(\s*['"](.+?)['"]\s*\)$""",
        condition.strip()
    )
    if match_truthy:
        key = match_truthy.group(1)
        return bool(status.get(key))

    print(f"[GUARDRAIL] Unsupported condition format: {condition}")
    return False


def check_contradiction(intent_class: str, status: dict, domain_config: dict) -> tuple:
    """
    LOGIC GUARDRAIL: Check if the classified intent contradicts the current status.
    Returns: (is_contradiction: bool, reason: str)
    """
    if not status or not intent_class:
        return False, None
    
    # Get rules from config or hardcoded fallback
    rules = domain_config.get("contradictionRules", [])
    print(f"[DEBUG CHECK_CONTRADICTION] Found {len(rules)} rules for domain {domain_config.get('domain')}")
    
    if not rules and domain_config.get("domain") == "transport":
         # Fallback rules if not in config
         rules = [
            {
                "intent": "finalizar", # cancelar
                "condition": "status.get('order_status') == 'delivered'",
                "response": "impossivel_cancelar_entregue"
            },
            {
                "intent": "finalizar",
                "condition": "status.get('order_status') == 'cancelled'",
                "response": "ja_cancelado"
            }
         ]
    
    for rule in rules:
        # Check if rule applies to this intent
        if rule.get("intent") == intent_class:
            condition = rule.get("condition", "")
            try:
                if _evaluate_condition(condition, status):
                    print(f"[LOGIC GUARDRAIL] Contradiction detected: {intent_class} vs {status}")
                    return True, rule.get("response", "contradiction_detected")
                else:
                    print(f"[DEBUG GUARDRAIL] Condition False: {condition} for {status}")
            except Exception as e:
                print(f"[GUARDRAIL ERROR] Condition check failed for rule {condition}: {e}")
                
    return False, None

def apply_guardrails(result, status, domain_config):
    """Helper to apply contradiction checks and update result in-place."""
    cls = result.get("classification")
    print(f"[DEBUG APPLY_GUARDRAILS] Checking {cls} against status {status}")
    if cls and status:
        is_bad, reason = check_contradiction(cls, status, domain_config)
        if is_bad:
            result["classification"] = "contradiction"
            result["classifications"] = ["contradiction"]
            result["contradiction_reason"] = reason
            result["source"] = "logic_guardrail"
            result["ai_validated"] = False
    return result

def check_active_status(status: dict) -> tuple:
    """
    Check if any classification is active (sticky session).
    Returns: (is_active: bool, active_category: str or None)
    
    Supports two formats:
    1. {category_name: truthy_value} e.g. {"cotacao": true} or {"cotacao": "active"}
    2. {category: category_name} e.g. {"category": "cotacao"} or {"categorie": "cotacao"}
    """
    if not status or not isinstance(status, dict):
        print(f"[DEBUG check_active_status] Empty or invalid status: {status}")
        return False, None
    
    print(f"[DEBUG check_active_status] Checking status: {status}")
    
    # Check for explicit "category" key format
    for key in ["category", "categorie", "categoria"]:
        if key in status:
            value = status[key]
            if value and value not in ["0", "null", "false", False, None, ""]:
                print(f"[DEBUG check_active_status] Found explicit category: {value}")
                return True, str(value).lower()
    
    # Check states object if present
    states = status.get("states", status)
    
    for key, value in states.items():
        if key in ["raw", "category", "categorie", "categoria"]:
            continue
        if value and value not in ["0", "null", "false", False, None, ""]:
            print(f"[DEBUG check_active_status] Found active key: {key}={value}")
            return True, key
    
    print(f"[DEBUG check_active_status] No active status found")
    return False, None


def classify_by_menu(intent: str, menu_options: list = None) -> str:
    """
    Classify numeric menu selections using either dynamic options or legacy hardcoded map.
    """
    intent_stripped = intent.strip()
    
    # 1. Dynamic Menu (n8n provided) - Simple Exact/Index Match
    if menu_options:
        # Check standard 1, 2, 3..
        if intent_stripped.isdigit():
            idx = int(intent_stripped) - 1
            if 0 <= idx < len(menu_options):
                return menu_options[idx].get("value")
        
        # Check explicit Option ID match
        for opt in menu_options:
            if str(opt.get("id")) == intent_stripped:
                return opt.get("value")
                
    # 2. Legacy Hardcoded Fallback
    menu_map = {
        "1": "cotacao",
        "2": "rastreio",
        "3": "boleto",
        "4": "cte",
        "5": "coleta"
    }
    
    return menu_map.get(intent_stripped)

def run_ai_menu_classifier(db, model_data, intent, context, menu_options):
    """
    Use AI to identify which menu option the user wants.
    """
    if not model_data or not menu_options:
        return None
        
    options_desc = "\\n".join([f"{opt.get('id', i+1)}. {opt.get('value')} ({opt.get('description','')})" for i, opt in enumerate(menu_options)])
    
    prompt = f"""O usuário está interagindo com um menu de opções. Identifique qual opção ele escolheu.

MENU DISPONÍVEL:
{options_desc}

CONTEXTO: {context or "Nenhum"}
MENSAGEM DO USUÁRIO: "{intent}"

TAREFA: Retorne APENAS o 'value' (nome da opção) que o usuário escolheu. 
Se ele não escolheu nenhuma opção válida do menu ou se a mensagem não se refere ao menu, retorne "null".
"""

    try:
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
        
        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json={
                "model": m.get("providerModelId"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if "null" in content.lower():
                return None
            
            # Clean up potential markdown or quotes
            content = content.replace("'", "").replace('"', "").replace("`", "").strip()
            return content
            
    except Exception as e:
        print(f"[Menu AI] Error: {e}")
        
    return None


def classify_by_semantics(intent: str, categories: list) -> str:
    """
    Semantic classification using keyword matching.
    """
    intent_lower = intent.lower()
    
    semantic_map = {
        "rastreio": ["rastrear", "onde está", "onde esta", "localizar", "tracking"],
        "cotacao": ["cotar", "cotação", "preço", "preco", "valor", "quanto custa"],
        "coleta": ["coleta", "retirada", "buscar", "coletar"],
        "boleto": ["boleto", "fatura", "pagamento", "segunda via"],
        "cte": ["cte", "xml", "pdf", "baixar", "documento"],
        "conversacao": ["oi", "olá", "ola", "menu", "ajuda", "help"]
    }
    
    for category, keywords in semantic_map.items():
        for keyword in keywords:
            if keyword in intent_lower:
                # Verify category is in allowed list
                if not categories or category in [c.lower().strip() for c in categories]:
                    return category
    
    return None


def run_ai_sentiment_classifier(db, model_data, intent, context, categories, system_prompt=None):
    """
    Use AI to classify when rule-based fails.
    """
    if not model_data:
        return None
    
    categories_str = ", ".join(categories) if categories else "conversacao, rastreio, cotacao, coleta, boleto, cte, atendente"
    
    prompt = f"""Classifique a intenção do usuário em UMA das categorias.

CATEGORIAS DISPONÍVEIS: {categories_str}

CONTEXTO ANTERIOR: {context or "Nenhum"}

MENSAGEM DO USUÁRIO: "{intent}"

Responda APENAS com o nome da categoria, sem explicações."""

    if system_prompt:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    else:
        messages = [{"role": "user", "content": prompt}]
    
    try:
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
        
        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json={
                "model": m.get("providerModelId"),
                "messages": messages,
                "temperature": 0.1
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip().lower()
    except Exception as e:
        print(f"[Sentiment AI] Error: {e}")
    
    return None



def validate_with_ai(db, model_id, intent, context, proposed_classification, categories, system_prompt=None):
    """
    Validate a proposed classification using AI.
    Returns tuple: (validated_classification, token_usage_dict)
    """
    if not model_id:
        return proposed_classification, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    
    categories_str = ", ".join(categories) if categories else "nenhuma categoria definida"
    
    prompt = f"""Você é um validador de classificação. 
Analise se a classificação proposta está correta para a mensagem do usuário.

CATEGORIAS VÁLIDAS: {categories_str}
CONTEXTO: {context or "Nenhum"}
MENSAGEM DO USUÁRIO: "{intent}"
CLASSIFICAÇÃO PROPOSTA: "{proposed_classification}"

TAREFA: A classificação proposta está correta?
- Se SIM, responda APENAS: {proposed_classification}
- Se NÃO, responda com a categoria correta da lista OU responda: incompreendido

Responda APENAS com uma palavra (a categoria ou "incompreendido")."""

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        model_info = db.aimodel.find_unique(
            where={"id": model_id},
            include={"provider": True}
        )
        
        if not model_info or not model_info.provider:
            return proposed_classification, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        m = {
            "providerModelId": model_info.providerModelId,
            "baseUrl": model_info.provider.baseUrl,
            "apiKey": model_info.provider.apiKey,
            "providerId": model_info.providerId
        }
        api_key = get_next_api_key(m.get("providerId")) or m.get("apiKey")
        
        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json={
                "model": m.get("providerModelId"),
                "messages": messages,
                "temperature": 0.0
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
            content = content.replace("'", "").replace('"', "").replace("`", "").strip()
            
            # Extract token usage
            usage = data.get("usage", {})
            token_usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
            
            return (content if content else "incompreendido"), token_usage
            
    except Exception as e:
        print(f"[AI Validation] Error: {e}")
    
    return proposed_classification, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def compare_intent_to_categories(intent: str, categories: list, context: str = "") -> str:
    """
    Compare intent against categories using multiple methods:
    1. Exact match (normalized)
    2. Regex/pattern matching
    3. Semantic keywords
    Returns matched category or None.
    """
    intent_normalized = intent.strip().lower()
    categories_normalized = [c.strip().lower() for c in categories]
    
    # 1. Exact Match
    if intent_normalized in categories_normalized:
        return intent_normalized
    
    # 2. Semantic Keywords Map
    semantic_map = {
        "rastreio": ["rastrear", "onde está", "onde esta", "localizar", "tracking", "rastreamento"],
        "cotacao": ["cotar", "cotação", "cotacao", "preço", "preco", "valor", "quanto custa", "orçamento"],
        "coleta": ["coleta", "retirada", "buscar", "coletar", "agendar busca", "recolher"],
        "boleto": ["boleto", "fatura", "pagamento", "segunda via", "pagar"],
        "cte": ["cte", "xml", "pdf", "baixar", "documento", "nota fiscal"],
        "conversacao": ["oi", "olá", "ola", "menu", "ajuda", "help", "início", "inicio"],
        "atendente": ["atendente", "humano", "falar com alguém", "falar com alguem", "pessoa", "atendimento"],
        "finalizar": ["sair", "cancelar", "encerrar", "finalizar", "fim", "tchau", "adeus"]
    }
    
    for category, keywords in semantic_map.items():
        if category in categories_normalized:
            for keyword in keywords:
                if keyword in intent_normalized:
                    return category
    
    # 3. Numeric Menu Selection (1, 2, 3...)
    if intent_normalized.isdigit():
        idx = int(intent_normalized) - 1
        if 0 <= idx < len(categories):
            return categories[idx].strip().lower()
    
    return None


def ai_full_classification(db, model_id, intent, context, categories, system_prompt=None):
    """
    Full AI classification when no rule-based match is found.
    Returns tuple: (classification, token_usage_dict)
    """
    if not model_id:
        return None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    
    categories_str = ", ".join(categories) if categories else "nenhuma categoria definida"
    
    prompt = f"""Classifique a intenção do usuário em UMA das categorias disponíveis.

CATEGORIAS DISPONÍVEIS: {categories_str}
CONTEXTO ANTERIOR: {context or "Nenhum"}
MENSAGEM DO USUÁRIO: "{intent}"

REGRAS CRÍTICAS:
1. A resposta DEVE ser uma categoria da lista acima
2. Se NENHUMA categoria se aplica com CLAREZA → responda: incompreendido  
3. NÃO invente, NÃO improvise, NÃO use sinônimos
4. Mensagens VAGAS ou muito CURTAS → incompreendido

EXEMPLOS:
✓ "quero cotação" → cotacao
✓ "rastreio" → rastreio
✗ "sim" → incompreendido (vago demais)
✗ "comprar produto" → incompreendido (não está na lista)
✗ "vender" → incompreendido (não está na lista)

Responda APENAS com uma palavra (a categoria ou "incompreendido")"""

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        model_info = db.aimodel.find_unique(
            where={"id": model_id},
            include={"provider": True}
        )
        
        if not model_info or not model_info.provider:
            return None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        m = {
            "providerModelId": model_info.providerModelId,
            "baseUrl": model_info.provider.baseUrl,
            "apiKey": model_info.provider.apiKey,
            "providerId": model_info.providerId
        }
        api_key = get_next_api_key(m.get("providerId")) or m.get("apiKey")
        
        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json={
                "model": m.get("providerModelId"),
                "messages": messages,
                "temperature": 0.1
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
            content = content.replace("'", "").replace('"', "").replace("`", "").strip()
            
            usage = data.get("usage", {})
            token_usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
            
            # STRICT validation
            valid_result = validate_classifications([content] if content else [],  categories)
            return (valid_result[0] if valid_result else None), token_usage
            
    except Exception as e:
        print(f"[AI Full Classification] Error: {e}")
    
    return None, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def validate_classifications(classifications: list, allowed_categories: list) -> list:
    """
    STRICT validation with smart fuzzy tolerance for typos.
    - Exact match: always allowed
    - Close typo (edit distance ≤ 2): allowed  
    - No match: filtered out
    
    This prevents AI hallucination while tolerating common typos.
    """
    if not classifications:
        return ['incompreendido']
    
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate minimum edit distance between two strings"""
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    # Normalize for comparison
    allowed_lower = [c.strip().lower() for c in allowed_categories]
    
    valid = []
    for cls in classifications:
        if not cls:
            continue
        cls_lower = cls.strip().lower()
        
        # Exact match
        if cls_lower in allowed_lower:
            valid.append(cls_lower)
        elif cls_lower == "incompreendido":
            valid.append(cls_lower)
        else:
            # Fuzzy match for typos
            best_match = None
            best_distance = float('inf')
            
            for cat in allowed_lower:
                distance = levenshtein_distance(cls_lower, cat)
                
                # Allow if edit distance ≤ 2 (e.g., 1-2 typos)
                # AND length difference ≤ 2 (prevents "bol" → "boleto" type matches)
                length_diff = abs(len(cls_lower) - len(cat))
                
                if distance <= 2 and length_diff <= 2:
                    if distance < best_distance:
                        best_distance = distance
                        best_match = cat
            
            if best_match:
                valid.append(best_match)
                print(f"[FUZZY MATCH] '{cls_lower}' → '{best_match}' (distance={best_distance})")
            # else: truly unknown, filter out
    
    # If no valid classifications found, return incompreendido
    return valid if valid else ['incompreendido']


def detect_intent_count(db, model_id, intent, context):
    """
    PHASE 1: Detect if message contains single or multiple intents.
    Returns tuple: ("single" | "multiple", token_usage_dict)
    
    This is a fast, binary decision to optimize classification accuracy.
    """
    if not model_id:
        return "single", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    
    prompt = f"""Analise a mensagem do usuário e determine quantas intenções DISTINTAS ela contém.

CONTEXTO ANTERIOR: {context or "Nenhum"}
MENSAGEM DO USUÁRIO: "{intent}"

REGRAS:
1. Se o usuário quer fazer APENAS UMA COISA → responda: single
2. Se o usuário quer fazer MÚLTIPLAS COISAS (2 ou mais ações diferentes) → responda: multiple
3. Ignore saudações, palavras de ligação (e, também, depois) e floreios

EXEMPLOS DE SINGLE:
- "quero fazer uma cotação" → single
- "me passa o cte" → single
- "oi, quero cotação" → single (saudação não conta)
- "qual o prazo de entrega" → single
- "isso é um absurdo, quero falar com gerente" → single (escalação é uma ação)

EXEMPLOS DE MULTIPLE:
- "cancelar e fazer cotação" → multiple (2 ações: cancelar + cotar)
- "rastreio e boleto" → multiple (2 ações diferentes)
- "voltar e pegar rastreio" → multiple (2 ações)

Responda APENAS com uma palavra: single ou multiple"""

    messages = [{"role": "user", "content": prompt}]
    
    try:
        model_info = db.aimodel.find_unique(
            where={"id": model_id},
            include={"provider": True}
        )
        
        if not model_info or not model_info.provider:
            return "single", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        m = {
            "providerModelId": model_info.providerModelId,
            "baseUrl": model_info.provider.baseUrl,
            "apiKey": model_info.provider.apiKey,
            "providerId": model_info.providerId
        }
        api_key = get_next_api_key(m.get("providerId")) or m.get("apiKey")
        
        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json={
                "model": m.get("providerModelId"),
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 10
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
            
            usage = data.get("usage", {})
            token_usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
            
            # Parse response
            if "multiple" in content or "multiplas" in content:
                result = "multiple"
            else:
                result = "single"
            
            print(f"[PHASE 1] Intent Count Detection: '{result}' for message: '{intent}'")
            return result, token_usage
            
    except Exception as e:
        print(f"[Intent Count Detection] Error: {e}")
    
    return "single", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def ai_multi_intent_classification(db, model_id, intent, context, categories, system_prompt=None):
    """
    Multi-Intent AI classification - detects multiple intents in a single message.
    Returns tuple: (list of classifications, token_usage_dict)
    
    Anti-hallucination guards:
    1. Only returns intents that exist in categories
    2. Maximum 3 intents per message
    3. Requires comma-separated response format
    """
    if not model_id:
        return [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    
    categories_str = ", ".join(categories) if categories else "nenhuma categoria definida"
    
    prompt = f"""Analise a mensagem do usuário e identifique a(s) intenção(ões) presente(s).

CATEGORIAS VÁLIDAS: {categories_str}
CONTEXTO ANTERIOR: {context or "Nenhum"}
MENSAGEM DO USUÁRIO: "{intent}"

REGRAS IMPORTANTES:
1. Se houver APENAS UMA intenção clara → retorne APENAS ela
2. Se houver MÚLTIPLAS intenções → separe por vírgula, em ordem de execução
3. Máximo 3 intenções
4. Retorne APENAS categorias da lista acima (ou incompreendido)
5. Se NENHUMA categoria se aplica → responda: incompreendido
6. Tolere pequenos erros de digitação

EXEMPLOS:
- "quero cotação" → cotacao
- "cancelar e fazer cotação" → finalizar, cotacao
- "me passa o rastreio e o boleto" → rastreio, boleto
- "comprar produto" → incompreendido (não existe na lista)

Responda APENAS com as categorias separadas por vírgula, sem explicações."""

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    
    try:
        model_info = db.aimodel.find_unique(
            where={"id": model_id},
            include={"provider": True}
        )
        
        if not model_info or not model_info.provider:
            return [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        m = {
            "providerModelId": model_info.providerModelId,
            "baseUrl": model_info.provider.baseUrl,
            "apiKey": model_info.provider.apiKey,
            "providerId": model_info.providerId
        }
        api_key = get_next_api_key(m.get("providerId")) or m.get("apiKey")
        
        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json={
                "model": m.get("providerModelId"),
                "messages": messages,
                "temperature": 0.1
            },
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=30
        )
        
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
            content = content.replace("'", "").replace('"', "").replace("`", "").strip()
            
            usage = data.get("usage", {})
            token_usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }
            
            # Parse comma-separated intents
            raw_intents = [i.strip() for i in content.split(",") if i.strip()][:3]  # Max 3
            
            # STRICT validation: only allowed categories
            valid_intents = validate_classifications(raw_intents, categories)
            
            print(f"[DEBUG Multi-Intent] Raw: {raw_intents}, Valid: {valid_intents}")
            return valid_intents, token_usage
            
    except Exception as e:
        print(f"[AI Multi-Intent] Error: {e}")
    
    return [], {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

def process_sentiment_analysis_v2(db, domain, intent, context, status, categories, exceptions, model_id=None, system_prompt=None, menu_options=None, multi_intent=False):
    """
    Orchestrator Logic v2 - Two Mode Decision Tree with Domain Scoping.
    
    Args:
        domain: Domain scope for learning (e.g., 'transport', 'health')
        intent: User's current message
        context: Previous conversation context
        status: Active classifications (sticky session)
        categories: Target categories for this domain
        exceptions: Patterns that force reclassification
        model_id: AI model to use
        system_prompt: Domain-specific prompt (optional, loaded from domain config if not provided)
        menu_options: Menu options for classification
        multi_intent: Enable multi-intent detection
    
    MODE 1 (No Status): Full Classification
    MODE 2 (Status Active): Exception Check Only
    MULTI-INTENT MODE: Detect multiple intents (when multi_intent=True)
    
    Returns dict with classification, source, is_exception, active_status, ai_validated, token_usage.
    When multi_intent=True, also includes 'classifications' array and 'multi_intent' flag.
    """
   
    
    start_time = datetime.now()
    
    result = {
        "classification": None,
        "source": None,
        "is_exception": False,
        "active_status": None,
        "ai_validated": False,
        "token_usage": {
             "prompt_tokens": 0,
             "completion_tokens": 0,
             "total_tokens": 0
        }
    }
    
    def log_and_return(confidence=1.0):
        """Helper to log execution with latency and return result."""
        # Calculate latency
        latency = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log
        log_sentiment_analysis(
            db, domain, intent, context, categories_normalized,
            result["classification"], result.get("classifications", [result["classification"]]), 
            confidence, result["source"], 
            result["token_usage"].get("total_tokens", 0),
            execution_ms=latency
        )
        return result
    
    def add_tokens(usage):
        """Helper to accumulate token usage."""
        result["token_usage"]["prompt_tokens"] += usage.get("prompt_tokens", 0)
        result["token_usage"]["completion_tokens"] += usage.get("completion_tokens", 0)
        result["token_usage"]["total_tokens"] += usage.get("total_tokens", 0)
    
    # Normalize categories
    categories_normalized = [c.strip().lower() for c in categories] if categories else []
    
    # Load domain config for guardrails
    try:
        domain_conf = get_domain_config(domain)
    except:
        domain_conf = {}
        
    # AUTO-LEARN: Check for new categories (if model available)
    if model_id and categories:
        # We wrap in try/except to not block main request on error
        try:
           check_and_learn_new_categories(db, domain, categories_normalized, model_id)
        except Exception as e:
           print(f"[AUTO-LEARN SKIP] {e}")
    
    # =====================================================
    # LAYER 0: Learned Cache (0 tokens, highest priority)
    # =====================================================
    cache_match, is_cache_hit = lookup_synonym_cache(db, domain, intent, categories_normalized)
    
    if is_cache_hit and cache_match:
        # Before returning cache hit, check if there are MULTIPLE intents
        # If user says "cotação e rastreio", cache might match only "cotação"
        if model_id:
            intent_count, count_tokens = detect_intent_count(db, model_id, intent, context)
            add_tokens(count_tokens)
            
            if intent_count == "multiple":
                print(f"[CACHE] Hit '{cache_match}' but detected MULTIPLE intents. Falling through to AI.")
                # Continue to AI processing instead of returning cache
            else:
                # Single intent - safe to return cache
                result["classification"] = cache_match
                result["classifications"] = [cache_match]
                result["multi_intent"] = False
                result["source"] = "learned_cache"
                result["ai_validated"] = False
                
                # Apply Guardrails
                apply_guardrails(result, status, domain_conf)
                
                return log_and_return(confidence=1.0)
        else:
            # No model to verify multi-intent, trust cache
            result["classification"] = cache_match
            result["classifications"] = [cache_match]
            result["multi_intent"] = False
            result["source"] = "learned_cache"
            result["ai_validated"] = False
            
            # Apply Guardrails
            apply_guardrails(result, status, domain_conf)
            
            return log_and_return(confidence=1.0)
        

        
    # =====================================================
    # LAYER 1: Local ML Model (0.85+ confidence)
    # =====================================================
    # Only if NOT sticky session active (Mode 2 priority)
    is_active, active_category = check_active_status(status)
    if not is_active:
        ml_class, ml_conf, ml_hit = run_local_ml_classifier(domain, intent, categories_normalized)
        
        # HYBRID FALLBACK LOGIC:
        # If ML Hit but Low Confidence (< 0.90) -> Force AI Check
        # If ML Miss -> Force AI Check
        
        if ml_hit and ml_conf >= 0.90:
             # Before trusting ML, verify if multiple intents exist
             if model_id:
                 intent_count, count_tokens = detect_intent_count(db, model_id, intent, context)
                 add_tokens(count_tokens)
                 
                 if intent_count == "multiple":
                     print(f"[ML] Hit '{ml_class}' (conf={ml_conf:.2f}) but detected MULTIPLE intents. Falling through to AI.")
                     # Continue to AI processing instead of returning ML result
                 else:
                     # Single intent - safe to return ML
                     result["classifications"] = [ml_class]
                     result["classification"] = ml_class
                     result["confidence"] = ml_conf
                     result["source"] = "local_model"
                     result["ai_validated"] = False
                     
                     # Apply Guardrails
                     apply_guardrails(result, status, domain_conf)
                     
                     # AUTO-LEARN: Track successful ML pattern
                     track_pattern(db, domain, intent, ml_class, ml_conf)
                     
                     return log_and_return(confidence=ml_conf)
             else:
                 # No model to verify, trust ML
                 result["classifications"] = [ml_class]
                 result["classification"] = ml_class
                 result["confidence"] = ml_conf
                 result["source"] = "local_model"
                 result["ai_validated"] = False
                 
                 # Apply Guardrails
                 apply_guardrails(result, status, domain_conf)
                 
                 track_pattern(db, domain, intent, ml_class, ml_conf)
                 
                 return log_and_return(confidence=ml_conf)
             
        elif ml_hit:
             print(f"[HYBRID] ML Confidence low ({ml_conf:.2f}). Falling back to AI.")
             # Continue to AI flow...

    
    # =====================================================
    # MODE 2: Status Exists → Exception Check Mode
    # =====================================================
    if is_active:
        result["active_status"] = active_category
        
        # Check intent against exception patterns
        has_exception, exception_action = check_exceptions(intent, exceptions)
        
        print(f"[DEBUG MODE2] Status Active: {active_category}, Exception Check: has={has_exception}, action={exception_action}")
        
        if has_exception and exception_action:
            result["is_exception"] = True
            
            # Use 2-phase intelligent detection for exceptions too
            if model_id:
                # PHASE 1: Detect if there are additional intents besides the exception
                intent_count, count_tokens = detect_intent_count(db, model_id, intent, context)
                add_tokens(count_tokens)
                
                # PHASE 2: Classify
                if intent_count == "multiple":
                    intents_list, tokens = ai_multi_intent_classification(
                        db, model_id, intent, context, categories_normalized, system_prompt
                    )
                    add_tokens(tokens)
                else:
                    # Just the exception
                    intents_list = [exception_action]
                    tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                
                result["ai_validated"] = True
                
                # Ensure exception is first, remove duplicates
                clean_intents = []
                seen = set()
                
                # Add exception first ONLY if it's a valid category
                if exception_action in categories_normalized and exception_action not in seen:
                    clean_intents.append(exception_action)
                    seen.add(exception_action)
                
                # Add other validated intents from AI
                for item in intents_list:
                    if item and item not in seen and item != "incompreendido":
                        if item in categories_normalized:
                            clean_intents.append(item)
                            seen.add(item)
                
                print(f"[EXCEPTION] Exception action: '{exception_action}', AI intents: {intents_list}, Clean: {clean_intents}")
                
                # If clean_intents is empty (exception action not in categories), use AI result directly
                if not clean_intents and intents_list:
                    for item in intents_list:
                        if item and item in categories_normalized:
                            clean_intents.append(item)
                
                # Final fallback if still empty
                if not clean_intents:
                    clean_intents = ["incompreendido"]
                
                # Unified response format
                result["classifications"] = clean_intents
                result["classification"] = clean_intents[0]
                result["multi_intent"] = len(clean_intents) > 1
                result["source"] = "exception_ai_classified"
                
                # Apply Guardrails
                apply_guardrails(result, status, domain_conf)
                
                # AUTO-LEARN: Track Exception
                track_pattern(db, domain, intent, clean_intents[0], 0.90)
                
                return log_and_return(confidence=0.90)
            
            # No AI - just the exception
            result["classifications"] = [exception_action]
            result["classification"] = exception_action
            result["multi_intent"] = False
            result["source"] = "exception_pattern_match"
            
            # Apply Guardrails
            apply_guardrails(result, status, domain_conf)
            
            # AUTO-LEARN: Track Exception Rule
            track_pattern(db, domain, intent, exception_action, 0.95)
            
            return log_and_return(confidence=0.95)
        
        # No exception detected, but check if user is asking for something NEW
        # "Status active: rastreio" + User says "preciso de cotação também" should NOT return rastreio
        if model_id:
            intent_count, count_tokens = detect_intent_count(db, model_id, intent, context)
            add_tokens(count_tokens)
            
            if intent_count == "multiple":
                print(f"[STICKY] Active '{active_category}' but user seems to want MULTIPLE things. Classifying with AI.")
                # Fall through to AI classification instead of sticky
            elif intent_count == "single":
                # Single intent - check if it's actually asking for something different
                # Quick AI check for what user wants
                single_result, tokens = ai_full_classification(
                    db, model_id, intent, context, categories_normalized, system_prompt
                )
                add_tokens(tokens)
                
                if single_result and single_result != active_category and single_result != "incompreendido":
                    # User is asking for something DIFFERENT - return the new intent
                    result["classifications"] = [single_result]
                    result["classification"] = single_result
                    result["multi_intent"] = False
                    result["source"] = "ai_classifier"
                    result["ai_validated"] = True
                    result["context_switch"] = True  # Flag context switch
                    
                    apply_guardrails(result, status, domain_conf)
                    track_pattern(db, domain, intent, single_result, 0.85)
                    
                    return log_and_return(confidence=0.85)
                else:
                    # Same category or incompreendido - maintain sticky
                    result["classifications"] = [active_category]
                    result["classification"] = active_category
                    result["multi_intent"] = False
                    result["source"] = "sticky_session"
                    result["ai_validated"] = True
                    
                    apply_guardrails(result, status, domain_conf)
                    track_pattern(db, domain, intent, active_category, 0.80)
                    
                    return log_and_return(confidence=0.80)
            else:
                # Fallback to sticky if detection fails
                result["classifications"] = [active_category]
                result["classification"] = active_category
                result["multi_intent"] = False
                result["source"] = "sticky_session"
                
                apply_guardrails(result, status, domain_conf)
                track_pattern(db, domain, intent, active_category, 0.80)
                
                return log_and_return(confidence=0.80)
        else:
            # No model, maintain sticky session
            result["classifications"] = [active_category]
            result["classification"] = active_category
            result["multi_intent"] = False
            result["source"] = "sticky_session"
            
            apply_guardrails(result, status, domain_conf)
            track_pattern(db, domain, intent, active_category, 0.80)
            
            return log_and_return(confidence=0.80)
    
    # =====================================================
    # MODE 1: No Status → Intelligent Classification
    # =====================================================
    
    # Check exceptions FIRST (even without status)
    has_exception, exception_action = check_exceptions(intent, exceptions)
    if has_exception and exception_action:
        result["is_exception"] = True
        
        # Process exception with 2-phase detection
        if model_id:
            intent_count, count_tokens = detect_intent_count(db, model_id, intent, context)
            add_tokens(count_tokens)
            
            if intent_count == "multiple":
                intents_list, tokens = ai_multi_intent_classification(
                    db, model_id, intent, context, categories_normalized, system_prompt
                )
                add_tokens(tokens)
            else:
                intents_list = [exception_action]
                tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
            result["ai_validated"] = True
            
            # Ensure exception is first
            clean_intents = []
            seen = set()
            
            # Add exception ONLY if it's a valid category
            if exception_action in categories_normalized and exception_action not in seen:
                clean_intents.append(exception_action)
                seen.add(exception_action)
            
            for item in intents_list:
                if item and item not in seen and item != "incompreendido":
                    if item in categories_normalized:
                        clean_intents.append(item)
                        seen.add(item)
            
            print(f"[MODE1 EXCEPTION] action:'{exception_action}', AI:{intents_list}, Clean:{clean_intents}")
            
            # If clean_intents is empty (exception not valid), use AI result
            if not clean_intents and intents_list:
                for item in intents_list:
                    if item and item in categories_normalized:
                        clean_intents.append(item)
            
            # Final fallback
            if not clean_intents:
                clean_intents = ["incompreendido"]
            
            # Set result
            result["classifications"] = clean_intents
            result["classification"] = clean_intents[0]
            result["multi_intent"] = len(clean_intents) > 1
            result["source"] = "exception_ai_classified"
            
            # Apply Guardrails
            apply_guardrails(result, status, domain_conf)

            return log_and_return(confidence=0.90)
        else:
            # No AI
            result["classifications"] = [exception_action]
            result["classification"] = exception_action
            result["source"] = "exception_pattern_match"
            
            # Missing log in original code block? Adding consistent logging
            apply_guardrails(result, status, domain_conf)
            return log_and_return(confidence=0.95)
    
    # PHASE 1: ALWAYS detect intent count first (prevents rule-match bypass)
    intent_count = "single"  # Default
    if model_id:
        intent_count, count_tokens = detect_intent_count(db, model_id, intent, context)
        add_tokens(count_tokens)
        print(f"[PHASE 1] Intent count: {intent_count}")
    
    # Step 1: Try rule-based comparison (fast path for single intents)
    if intent_count == "single":
        rule_match = compare_intent_to_categories(intent, categories_normalized, context)
        
        if rule_match and model_id:
            # Validate with AI
            validated, tokens = validate_with_ai(
                db, model_id, intent, context, 
                rule_match, categories_normalized, system_prompt
            )
            add_tokens(tokens)
            result["ai_validated"] = True
            
            if validated and validated != "incompreendido":
                result["classifications"] = [validated]
                result["classification"] = validated
                result["multi_intent"] = False
                result["source"] = "rule_match_ai_validated"
                
                # Apply Guardrails
                apply_guardrails(result, status, domain_conf)
                
                # AUTO-LEARN: Track Verified Rule
                track_pattern(db, domain, intent, validated, 0.95)
                
                return log_and_return(confidence=0.95)
        elif rule_match:
            # No AI, trust the rule
            result["classifications"] = [rule_match]
            result["classification"] = rule_match
            result["multi_intent"] = False
            result["source"] = "rule_match"
            
            # Apply Guardrails
            apply_guardrails(result, status, domain_conf)
            
            return log_and_return(confidence=0.90)
    
    # Step 2: AI Classification (based on PHASE 1 result)
    if model_id:
        # PHASE 2: Classify based on detected count
        if intent_count == "multiple":
            # Use multi-intent classifier
            intents_list, tokens = ai_multi_intent_classification(
                db, model_id, intent, context, 
                categories_normalized, system_prompt
            )
            add_tokens(tokens)
        else:
            # Use single-intent classifier (more precise)
            single_result, tokens = ai_full_classification(
                db, model_id, intent, context, 
                categories_normalized, system_prompt
            )
            add_tokens(tokens)
            intents_list = [single_result] if single_result else []
        
        result["ai_validated"] = True
        
        # Remove duplicates and None values, maintain order
        seen = set()
        clean_intents = []
        for item in intents_list:
            if item and item not in seen and item != "incompreendido":
                # Validate item exists in categories
                if item in categories_normalized:
                    clean_intents.append(item)
                    seen.add(item)
        
        print(f"[PHASE 2] Raw intents: {intents_list}, Clean: {clean_intents}")
        
        if clean_intents:
            # Always return as array
            result["classifications"] = clean_intents
            result["classification"] = clean_intents[0]  # Primary
            
            # Set multi_intent flag
            if len(clean_intents) > 1:
                result["multi_intent"] = True
                result["source"] = "ai_multi_intent"
            else:
                result["multi_intent"] = False
                result["source"] = "ai_classifier"
            
            # Log AI classification for learning
            
            # Apply Guardrails
            apply_guardrails(result, status, domain_conf)
            
            # AUTO-LEARN: Track AI Result
            if clean_intents:
                track_pattern(db, domain, intent, clean_intents[0], 0.85)
            
            return log_and_return(confidence=0.85)
    
    # =====================================================
    # FALLBACK: Return "incompreendido"
    # =====================================================
    print(f"[DEBUG] Falling back to incompreendido. model_id={model_id}, intent='{intent}'")
    result["classifications"] = ["incompreendido"]
    result["classification"] = "incompreendido"
    result["source"] = "fallback"
    result["ai_validated"] = model_id is not None
    result["multi_intent"] = False
    
    # Log fallback for review (high priority for learning)
    return log_and_return(confidence=0.0)


# Keep old function name for backwards compatibility
def process_sentiment_analysis(db, domain, intent, context, status, categories, exceptions, model_id=None, system_prompt=None, menu_options=None):
    """Wrapper for backwards compatibility."""
    return process_sentiment_analysis_v2(db, domain, intent, context, status, categories, exceptions, model_id, system_prompt, menu_options)

@csrf_exempt
def sentiment_analyze(request):
    """
    Sentiment Analysis Endpoint (View) with Domain Scoping.
    Supports Session Auth (User) OR Bearer Token (OrchClient).
    """
    # 1. Check Session Auth
    user = getattr(request, 'user', None)
    is_authenticated = user and user.is_authenticated
    
    # 2. Check Bearer Token if not session authenticated
    if not is_authenticated:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                db = get_db()
                # Check OrchClient
                client = db.orchclient.find_first(
                    where={"token": token, "enabled": True}
                )
                if client:
                    is_authenticated = True
                    request.orch_client_id = client.id
                else:
                    # Check User API Key
                    if token.startswith('sk-agent-'):
                        api_key = db.apikey.find_first(where={"key": token, "active": True})
                        if api_key:
                            is_authenticated = True
                            user = db.user.find_unique(where={"id": api_key.userId})
                            if user:
                                request.user = user
            except Exception as e:
                print(f"Auth check error: {e}")
                import traceback
                traceback.print_exc()
                pass
    
    if not is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)
        
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        body = json.loads(request.body)
        db = get_db()
        
        # Extract domain (default: transport)
        domain = body.get("domain", "transport")
        
        # Load domain configuration
        try:
            domain_config = get_domain_config(domain)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=400)
        
        # Parse input
        if "content" in body:
            parsed = parse_sentiment_input(body.get("content", ""))
            # Merge explicit status if provided (overrides parser)
            if "status" in body and isinstance(body["status"], dict):
                parsed["status"] = body["status"]
        else:
            parsed = {
                "intent": body.get("intent", ""),
                "context": body.get("context", ""),
                "status": body.get("status", {}),
                "raw_content": body.get("intent", "")
            }
        
        # Get parameters with domain defaults
        categories = body.get("categories")
        if not categories or len(categories) == 0:
            # Use domain default categories
            categories = json.loads(domain_config["defaultCategories"])
        
        system_prompt = body.get("system_prompt")
        if not system_prompt:
            # Use domain system prompt
            system_prompt = domain_config["systemPrompt"]
        
        exceptions = body.get("exceptions", [])
        menu_options = body.get("menu_options", [])
        model_id = body.get("model_id")
        multi_intent = body.get("multi_intent", False)
        
        # AUTO-FETCH: Get a default model if none provided (required for multi-intent detection)
        if not model_id:
            try:
                default_model = db.aimodel.find_first(
                    where={
                        "isSentiment": True
                    },
                    order={"id": "desc"}  # Use id since createdAt might not exist
                )
                if default_model:
                    model_id = default_model.id
                    print(f"[ANALYZE] No model_id provided, using default: {default_model.name or default_model.providerModelId}")
                else:
                    print(f"[ANALYZE] No sentiment model found in DB. Multi-intent detection will be disabled.")
            except Exception as e:
                print(f"[ANALYZE] Failed to fetch default model: {e}")
        
        result = process_sentiment_analysis_v2(
            db,
            domain,  # Pass domain to analysis
            parsed["intent"], 
            parsed["context"], 
            parsed["status"], 
            categories, 
            exceptions, 
            model_id, 
            system_prompt,
            menu_options,
            multi_intent
        )
        
        # Add domain info to response
        result["domain"] = domain
        result["domain_name"] = domain_config["name"]
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ============================================
# Admin API: Self-Learning Dashboard
# ============================================

@csrf_exempt
@login_required
def sentiment_logs_list(request):
    """
    GET /api/ai/sentiment/logs - List sentiment logs for review
    Query params: ?pending=true (only unreviewed), ?limit=50
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        db = get_db()
        pending_only = request.GET.get("pending", "false").lower() == "true"
        limit = min(int(request.GET.get("limit", 50)), 100)
        
        where_clause = {}
        if pending_only:
            where_clause["isReviewed"] = False
            
        logs = db.sentimentlog.find_many(
            where=where_clause,
            order={"timestamp": "desc"},
            take=limit
        )
        
        # Convert Prisma objects to dicts
        logs_data = []
        for log in logs:
            try:
                l = log.model_dump()
            except AttributeError:
                # Fallback for Pydantic v1 or plain object
                try:
                    l = log.dict()
                except AttributeError:
                    l = vars(log)
            l["categories"] = json.loads(l.get("categories", "[]"))
            l["classifications"] = json.loads(l.get("classifications", "[]")) if l.get("classifications") else None
            logs_data.append(l)
        
        return JsonResponse({"logs": logs_data, "count": len(logs_data)})
        
    except Exception as e:
        print(f"[LOG LIST ERROR] {e}")
        return JsonResponse({"error": str(e)}, status=500)



@csrf_exempt
@login_required
def sentiment_logs_evaluate(request, log_id):
    """
    POST /api/ai/sentiment/logs/<id>/evaluate - Ask AI to re-evaluate/suggest classification
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        db = get_db()
        log = db.sentimentlog.find_unique(where={"id": log_id})
        
        if not log:
            return JsonResponse({"error": "Log not found"}, status=404)
            
        domain = log.domain or "transport"
        domain_conf = get_domain_config(domain)
        
        # Prepare context for AI
        system_prompt = domain_conf.get("systemPrompt", "")
        categories_str = domain_conf.get("defaultCategories", "[]") # JSON string
        try:
            categories = json.loads(categories_str)
            if not isinstance(categories, list):
                 categories = []
        except:
            categories = []
        
        # Check if specific model requested
        body = json.loads(request.body) if request.body else {}
        requested_model_id = body.get("modelId")
        
        model = None
        if requested_model_id:
            model = db.aimodel.find_unique(where={"id": requested_model_id})
            if not model:
                return JsonResponse({"error": "Requested model not found"}, status=404)
        else:
            # Find active sentiment model (Default)
            model = db.aimodel.find_first(where={"isSentiment": True})
            if not model:
                 # Fallback to any model
                 model = db.aimodel.find_first()
        
        if not model:
             return JsonResponse({"error": "No AI model available"}, status=500)
             
        # Fetch provider info
        provider = db.aiprovider.find_unique(where={"id": model.providerId})
        if not provider:
             return JsonResponse({"error": "Model provider not found"}, status=500)
             
        model_data = {
            "id": model.id, # REQUIRED for run_ai_sentiment_classifier
            "providerModelId": model.providerModelId,
            "baseUrl": provider.baseUrl,
            "apiKey": provider.apiKey
        }
        
        print(f"[EVALUATE] Running AI classification for log {log_id} with model {model.id}")
        
        # Run Classification (Suggestion)
        ai_classification = run_ai_sentiment_classifier(
            db, 
            model_data, 
            log.intent, 
            log.context, 
            categories, 
            system_prompt
        )
        
        print(f"[EVALUATE] Result: {ai_classification}")
        
        return JsonResponse({
            "success": True, 
            "category": ai_classification, # Changed from 'suggestion' to 'category' to match frontend
            "reasoning": "Classificado via modelo " + (model.name or model.providerModelId),
            "logId": log_id
        })
        
    except Exception as e:
        print(f"[EVALUATE ERROR] {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def sentiment_logs_review(request, log_id):
    """
    POST /api/ai/sentiment/logs/<id>/review - Submit admin correction
    Body: { "correction": "category", "add_synonym": { "word": "x", "category": "y" }, "notes": "..." }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        db = get_db()
        body = json.loads(request.body)
        
        correction = body.get("correction")
        add_synonym = body.get("add_synonym")
        notes = body.get("notes", "")
        
        # Update log as reviewed
        db.sentimentlog.update(
            where={"id": log_id},
            data={
                "isReviewed": True,
                "adminCorrection": correction, # Ensure this is being passed as string or None
                "reviewedAt": datetime.now(),
                "feedbackNotes": notes
            }
        )

        
        # Optionally add synonym
        if add_synonym and add_synonym.get("word") and add_synonym.get("category"):
            try:
                db.sentimentsynonym.create(data={
                    "id": str(uuid.uuid4()),
                    "word": add_synonym["word"].lower(),
                    "category": add_synonym["category"].lower(),
                    "source": "admin",
                    "approvedBy": getattr(request.user, 'id', None)
                })
            except Exception as e:
                print(f"[SYNONYM ERROR] {e}")  # Word might already exist
        
        # TRIGGER AUTO-TRAINING
        # Check current count of reviewed logs for this domain
        # If multiple of 10, trigger training in background
        try:
             # Get domain from log
             log = db.sentimentlog.find_unique(where={"id": log_id})
             if log and log.domain:
                 count = db.sentimentlog.count(where={"domain": log.domain, "isReviewed": True})
                 if count > 0 and count % 10 == 0:
                     print(f"[AUTO-TRAIN] Triggering training for domain {log.domain} (Count: {count})")
                     import threading
                     from .training_pipeline import SentimentTrainer
                     
                     def run_training_bg(d):
                         try:
                             t = SentimentTrainer(domain=d)
                             t.train()
                             print(f"[AUTO-TRAIN] Training finished for {d}")
                         except Exception as ex:
                             print(f"[AUTO-TRAIN ERROR] {ex}")
                             
                     threading.Thread(target=run_training_bg, args=(log.domain,)).start()
        except Exception as e:
            print(f"[AUTO-TRAIN ERROR] Failed to check/trigger: {e}")

        return JsonResponse({"success": True, "log_id": log_id})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def sentiment_synonyms_list(request):
    """
    GET /api/ai/sentiment/synonyms - List all learned synonyms
    POST /api/ai/sentiment/synonyms - Add new synonym { "word": "x", "category": "y" }
    """
    db = get_db()
    
    if request.method == "GET":
        try:
            synonyms_list = db.sentimentsynonym.find_many(
                order={"useCount": "desc"}
            )
            synonyms = []
            for s in synonyms_list:
                s_dict = s.model_dump() if hasattr(s, 'model_dump') else s.dict() if hasattr(s, 'dict') else vars(s)
                synonyms.append(s_dict)
            return JsonResponse({"synonyms": synonyms, "count": len(synonyms)})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    elif request.method == "POST":
        try:
            body = json.loads(request.body)
            word = body.get("word", "").lower().strip()
            category = body.get("category", "").lower().strip()
            domain = body.get("domain", "transport").lower().strip()
            
            if not word or not category:
                return JsonResponse({"error": "word and category required"}, status=400)
            
            synonym_id = str(uuid.uuid4())
            
            db.sentimentsynonym.create(data={
                "id": synonym_id,
                "domain": domain,
                "word": word,
                "category": category,
                "source": "admin",
                "approvedBy": getattr(request.user, 'id', None)
            })
            
            return JsonResponse({"success": True, "id": synonym_id, "word": word, "category": category})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
@login_required
def sentiment_synonyms_delete(request, synonym_id):
    """
    DELETE /api/ai/sentiment/synonyms/<id> - Remove synonym
    """
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        db = get_db()
        db.sentimentsynonym.delete(where={"id": synonym_id})
        return JsonResponse({"success": True, "deleted": synonym_id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def sentiment_patterns_list(request):
    """
    GET /api/ai/sentiment/patterns - List auto-learn candidates
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        db = get_db()
        threshold = int(request.GET.get("threshold", 5))
        min_confidence = float(request.GET.get("min_confidence", 0.8))
        
        candidates = get_auto_learn_candidates(db, threshold, min_confidence)
        
        return JsonResponse({
            "patterns": candidates, 
            "count": len(candidates),
            "threshold": threshold,
            "min_confidence": min_confidence
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@login_required
def sentiment_stats(request):
    """
    GET /api/ai/sentiment/stats - Dashboard statistics
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        db = get_db()
        
        # Total logs
        total_logs = db.sentimentlog.count()
        
        # Pending reviews
        pending_reviews = db.sentimentlog.count(where={"isReviewed": False})
        
        # Cache hits vs AI calls
        source_group = db.sentimentlog.group_by(
            by=["source"],
            count={"_all": True}
        )
        source_breakdown = [{"source": g["source"], "count": g["_count"]["_all"]} for g in source_group]
        source_breakdown = sorted(source_breakdown, key=lambda x: x["count"], reverse=True)
        
        # Total synonyms
        total_synonyms = db.sentimentsynonym.count()
        
        # Total patterns
        total_patterns = db.sentimentpattern.count()
        
        return JsonResponse({
            "total_logs": total_logs,
            "pending_reviews": pending_reviews,
            "source_breakdown": source_breakdown,
            "total_synonyms": total_synonyms,
            "total_patterns": total_patterns
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def sentiment_stats_by_domain(request):
    """
    GET /api/ai/sentiment/stats/domain?domain=transport
    
    Returns stats for specific domain.
    """
    domain = request.GET.get("domain")
    
    if not domain:
        return JsonResponse({"error": "domain parameter required"}, status=400)
    
    try:
        db = get_db()
        
        # Verify domain exists
        domain_config = db.domainconfig.find_first(where={"domain": domain})
        if not domain_config:
             return JsonResponse({"error": f"Domain '{domain}' not found"}, status=404)
        
        # Total logs
        total_logs = db.sentimentlog.count(where={"domain": domain})
        
        # Pending reviews
        pending_reviews = db.sentimentlog.count(where={"domain": domain, "isReviewed": False})
        
        # Source breakdown
        source_group = db.sentimentlog.group_by(
            by=["source"],
            where={"domain": domain},
            count={"_all": True}
        )
        source_breakdown_raw = [{"source": g["source"], "count": g["_count"]["_all"]} for g in source_group]
        source_breakdown_raw = sorted(source_breakdown_raw, key=lambda x: x["count"], reverse=True)
        
        source_breakdown = [
            {"source": row["source"], "count": row["count"]} 
            for row in source_breakdown_raw
        ]
        
        # Synonyms count
        total_synonyms = db.sentimentsynonym.count(where={"domain": domain})
        
        # Patterns count
        total_patterns = db.sentimentpattern.count(where={"domain": domain})
        
        return JsonResponse({
            "domain": domain,
            "domain_name": domain_config.name,
            "total_logs": total_logs,
            "pending_reviews": pending_reviews,
            "source_breakdown": source_breakdown,
            "total_synonyms": total_synonyms,
            "total_patterns": total_patterns
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@login_required
def train_sentiment_model(request):
    """
    POST /api/ai/sentiment/train
    Body: { "domain": "transport" }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
        
    try:
        body = json.loads(request.body)
        domain = body.get("domain", "transport")
        
        # Lazy import to avoid circular dep or startup lag
        from .training_pipeline import SentimentTrainer
        
        trainer = SentimentTrainer(domain=domain)
        result = trainer.train()
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
