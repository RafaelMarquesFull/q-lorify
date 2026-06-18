"""
Rules-Prompt Compiler & Applicator.

Compiles business rules from a system prompt into structured JSON via a robust LLM.
Applies compiled rules deterministically at runtime — zero LLM cost for rule application.

Flow:
  1. Admin saves Agent system prompt → compile_prompt_rules() is called
  2. Robust LLM extracts rules → JSON saved to Agent.compiledRules
  3. At runtime, apply_compiled_rules() applies rules deterministically
"""
import hashlib
import json
import re
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple


# ════════════════════════════════════════════════════════════════════════════════
# HASH DETECTION: Detect system prompt changes to trigger recompilation
# ════════════════════════════════════════════════════════════════════════════════

# Patterns for dynamic variables that change per-request (ignored in hash)
_DYNAMIC_PATTERNS = [
    re.compile(r'`status_cotacao`[^`]*`[^`]+`'),           # `status_cotacao`: `valor`
    re.compile(r'\{\{\s*\$json\.\w+\s*\}\}'),              # {{ $json.status }}
    re.compile(r"\{\{\s*\$\('.*?'\).*?\}\}"),               # {{ $('When chat...').item... }}
    re.compile(r'\{status_entrada\}'),                      # {status_entrada}
    re.compile(r'`[a-z_]+`:\s*`[a-z_]+`'),                 # generic `field`: `value` pairs
]


def compute_prompt_hash(system_prompt: str) -> str:
    """
    Compute SHA256 hash of system prompt, ignoring dynamic variables.
    Only structural/rule changes trigger a different hash.
    """
    if not system_prompt:
        return ""
    normalized = system_prompt.strip()
    for pattern in _DYNAMIC_PATTERNS:
        normalized = pattern.sub("__DYN__", normalized)
    # Also normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]


def check_prompt_changed(system_prompt: str, stored_hash: str) -> bool:
    """Return True if system prompt has changed (rules need recompilation)."""
    if not stored_hash:
        return True  # Never compiled
    return compute_prompt_hash(system_prompt) != stored_hash


# ════════════════════════════════════════════════════════════════════════════════
# META-PROMPT: Sent to robust LLM to extract rules from system prompt
# This is the ONLY fixed prompt in the system — everything else is dynamic.
# ════════════════════════════════════════════════════════════════════════════════

_META_PROMPT_SYSTEM = """Você é um compilador de regras de negócio. Analise um system prompt e extraia as regras em JSON estruturado.

## REGRA CRÍTICA: AGRUPAMENTO
Crie NO MÁXIMO 10 regras, agrupando por tipo lógico. NÃO crie uma regra por keyword individual.
Exemplo correto: UMA regra keyword_list com 12 categorias, NÃO 12 regras separadas.

## TIPOS DE REGRA:

### intent_match
Detecta intenção do usuário por palavras-chave na mensagem.
```json
{"id": "intent_global", "type": "intent_match", "priority": 0,
 "triggers": ["sair", "voltar ao início", "reiniciar", "cancelar"],
 "action": {"set_field": "status_cotacao", "value": "menu_inicial"}}
```

### state_transition
Transição condicional baseada em estado de entrada. Busca triggers na mensagem do usuário.
IMPORTANTE para triggers em português: inclua TODAS as conjugações verbais:
- "corrigir" → inclua "corrigir", "corrija", "corrige", "corrigindo", "correção", "alterar", "altere", "alteração", "ajustar", "ajuste"
- "confirmar" → inclua "confirmar", "confirma", "confirmado", "confirmo", "sim", "prosseguir", "ok", "seguir", "pode seguir"
```json
{"id": "state_cotar_corrigir", "type": "state_transition", "priority": 1,
 "input_field": "status_cotacao_entrada",
 "transitions": {"cotar_corrigir": [
   {"triggers": ["confirmar","confirma","confirmado","sim","prosseguir","ok","pode seguir","seguir"],
    "action": {"set_field": "status_cotacao", "value": "cotar"}},
   {"triggers": ["corrigir","corrija","corrige","correção","alterar","altere","alteração","ajustar","ajuste","mudar","trocar","troque"],
    "action": {"set_field": "status_cotacao", "value": "corrigir"},
    "is_default": true}
 ]}}
```

### keyword_list
Lista de palavras-chave por categoria. Se o prompt define DIFERENTES ações para DIFERENTES listas de categorias, crie UMA regra keyword_list POR AÇÃO (ex: uma para "validacao_humana", outra para "finalizar").
CRÍTICO: Os keywords devem ser os NOMES REAIS DOS PRODUTOS, não apenas nomes das categorias.
Exemplo: Para "Linha Branca" inclua "refrigerador", "freezer", "lavadora", "secadora", "micro-ondas", "fogão", "cooktop", etc.
Inclua variações sem acento (ex: "farmácia" e "farmacia", "fogão" e "fogao").
```json
{"id": "restricted_products", "type": "keyword_list", "priority": 2,
 "target_fields": ["tipo_mercadoria"],
 "categories": [
   {"name": "Linha Branca", "keywords": ["refrigerador", "freezer", "lavadora", "secadora", "micro-ondas", "fogão", "fogao", "cooktop", "coifa"]},
   {"name": "Bebidas", "keywords": ["bebida", "cerveja", "vinho"]}
 ],
 "on_match": {"set_field": "status_cotacao", "value": "validacao_humana"}}
```

### field_audit
Verifica campos obrigatórios. Use os nomes EXATOS dos campos do cache/schema.
```json
{"id": "completeness", "type": "field_audit", "priority": 4,
 "required_fields": ["documento_remetente", "documento_destinatario", "cep_origem", "cep_destino", "volumes", "peso", "valor", "tipo_mercadoria"],
 "on_complete": {"set_field": "status_cotacao", "value": "confirmar"},
 "on_incomplete": {"set_field": "status_cotacao", "value": "dado_faltante", "list_missing_in": "campos_faltantes"}}
```

### format_rule
Regra de formatação (CEP sem hífen, CNPJ sem pontuação, etc.)
```json
{"id": "fmt_cep", "type": "format_rule", "priority": 99,
 "field_pattern": "cep_.*", "transform": "digits_only", "expected_length": 8}
```

### dynamic_variable
Variáveis dinâmicas extraídas do system prompt em runtime.
```json
{"name": "status_cotacao_entrada", "source": "system_prompt",
 "pattern": "status_cotacao.*?`([a-z_]+)`"}
```

## FORMATO DE SAÍDA:
```json
{
  "version": 1,
  "priority_order": ["id1", "id2", ...],
  "rules": [...],
  "dynamic_variables": [...]
}
```

## REGRAS OBRIGATÓRIAS:
1. MÁXIMO 10 regras — agrupe por tipo lógico
2. priority_order deve listar os IDs na ordem de execução (priority crescente)
3. Quando o prompt menciona nomes de campos (CEP, CNPJ, peso, etc.), mapeie para snake_case: documento_remetente, documento_destinatario, cep_origem, cep_destino, volumes, peso, valor, tipo_mercadoria, pagador, dimensoes_formatadas
4. Para keyword_list: inclua TODAS as palavras-chave de todas as categorias do prompt, com variações sem acento
5. Para state_transition: inclua TODAS as conjugações e sinônimos em português
6. Responda APENAS com JSON válido, sem markdown fences, sem explicações"""

_META_PROMPT_USER = """Extraia as regras de negócio do system prompt abaixo.

CAMPOS DO CACHE (use estes nomes exatos nos required_fields e target_fields):
documento_remetente, documento_destinatario, documento_pagador, cep_origem, cep_destino, volumes, peso, valor, dimensoes_formatadas, tipo_dimensoes, tipo_mercadoria, pagador

## SYSTEM PROMPT:
{system_prompt}

## JSON:"""


# ════════════════════════════════════════════════════════════════════════════════
# COMPILATION: Call robust LLM to extract rules from system prompt
# ════════════════════════════════════════════════════════════════════════════════

def compile_prompt_rules(db, system_prompt: str, rules_model_id: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Send system prompt to a robust LLM to extract business rules.

    Args:
        db: Prisma database client
        system_prompt: The agent's system prompt text
        rules_model_id: ID of the robust LLM model to use for compilation

    Returns:
        (success, compiled_rules_dict, error_message)
    """
    from .key_rotation import get_next_api_key

    if not system_prompt or not system_prompt.strip():
        return False, None, "System prompt is empty"

    if not rules_model_id:
        return False, None, "No rules model ID configured"

    # Get model info
    model_info = db.query_raw('''
        SELECT m.providerModelId, p.baseUrl, p.apiKey, m.providerId
        FROM AIModel m JOIN AIProvider p ON m.providerId = p.id
        WHERE m.id = ?
    ''', rules_model_id)

    if not model_info or len(model_info) == 0:
        return False, None, f"Rules model '{rules_model_id}' not found"

    m = model_info[0]
    api_key = get_next_api_key(m.get("providerId")) or m.get("apiKey")

    if not api_key:
        return False, None, "No API key available for rules model"

    user_message = _META_PROMPT_USER.format(system_prompt=system_prompt)

    print(f"[RulesCompiler] Compiling rules with model: {m.get('providerModelId')}")
    print(f"[RulesCompiler] System prompt length: {len(system_prompt)} chars")

    try:
        payload = {
            "model": m.get("providerModelId"),
            "messages": [
                {"role": "system", "content": _META_PROMPT_SYSTEM},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.05,
            "max_tokens": 8000
        }

        resp = requests.post(
            f"{m.get('baseUrl')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=60
        )

        if resp.status_code != 200:
            return False, None, f"LLM API error: status={resp.status_code} body={resp.text[:300]}"

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        content = content.strip()

        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        compiled = json.loads(content)

        # Basic validation
        if not isinstance(compiled, dict):
            return False, None, "LLM returned non-dict JSON"
        if "rules" not in compiled:
            return False, None, "LLM response missing 'rules' key"
        if not isinstance(compiled["rules"], list):
            return False, None, "'rules' must be a list"

        rule_count = len(compiled["rules"])
        rule_types = set(r.get("type") for r in compiled["rules"])
        print(f"[RulesCompiler] Compiled {rule_count} rules, types: {rule_types}")

        # Log token usage
        usage = data.get("usage", {})
        print(f"[RulesCompiler] Tokens: input={usage.get('prompt_tokens', '?')} output={usage.get('completion_tokens', '?')}")

        return True, compiled, None

    except json.JSONDecodeError as je:
        return False, None, f"Failed to parse LLM JSON: {je}"
    except requests.exceptions.Timeout:
        return False, None, "LLM request timed out (60s)"
    except Exception as e:
        return False, None, f"Compilation error: {str(e)}"


def save_compiled_rules(db, agent_id: str, compiled_rules: Dict) -> bool:
    """
    Save compiled rules to the Agent record in the database.
    """
    try:
        db.agent.update(
            where={"id": agent_id},
            data={
                "compiledRules": json.dumps(compiled_rules, ensure_ascii=False),
                "rulesCompiledAt": datetime.utcnow(),
                "rulesVersion": {"increment": 1}
            }
        )
        print(f"[RulesCompiler] Saved compiled rules for agent {agent_id}")
        return True
    except Exception as e:
        print(f"[RulesCompiler] Failed to save rules: {e}")
        return False


# ════════════════════════════════════════════════════════════════════════════════
# RUNTIME APPLICATION: Apply compiled rules deterministically
# ════════════════════════════════════════════════════════════════════════════════

def apply_compiled_rules(
    result: Dict,
    compiled_rules_json: str,
    user_content: str = "",
    extraction_results: Optional[Dict] = None,
    system_prompt: str = ""
) -> Dict:
    """
    Apply pre-compiled rules deterministically to the formatter output.
    This replaces all hardcoded logic (_post_process_status, _classify_mercadoria, etc.)

    Args:
        result: The formatter's JSON output (update_db structure)
        compiled_rules_json: JSON string of compiled rules from Agent.compiledRules
        user_content: Original user message text
        extraction_results: Raw function extraction results (for fabrication guards)
        system_prompt: The system prompt (for dynamic variable extraction)

    Returns:
        The modified result dict with rules applied
    """
    if not compiled_rules_json:
        print("[RulesApply] No compiled rules — skipping")
        return result

    try:
        compiled = json.loads(compiled_rules_json) if isinstance(compiled_rules_json, str) else compiled_rules_json
    except json.JSONDecodeError:
        print("[RulesApply] Failed to parse compiled rules JSON")
        return result

    if not isinstance(compiled, dict) or "rules" not in compiled:
        print("[RulesApply] Invalid compiled rules structure")
        return result

    # Resolve the update_db and cache from result
    update_db = result.get("update_db", result)
    if not isinstance(update_db, dict):
        return result
    cache = update_db.get("cache_recuperacao", {})
    if not isinstance(cache, dict):
        cache = {}

    # Extract dynamic variables from system prompt
    dynamic_vars = _extract_dynamic_variables(compiled.get("dynamic_variables", []), system_prompt)

    # Get priority order
    priority_order = compiled.get("priority_order", [r["id"] for r in compiled["rules"]])

    # Index rules by id
    rules_by_id = {r["id"]: r for r in compiled["rules"]}

    # Apply fabrication guards FIRST (before status rules)
    for rule in compiled["rules"]:
        if rule.get("type") == "fabrication_guard":
            _apply_fabrication_guard(rule, cache, extraction_results)

    # Apply format rules
    for rule in compiled["rules"]:
        if rule.get("type") == "format_rule":
            _apply_format_rule(rule, cache)

    # Apply status/business rules in priority order
    status_resolved = False
    for rule_id in priority_order:
        if status_resolved:
            break
        rule = rules_by_id.get(rule_id)
        if not rule:
            continue

        rule_type = rule.get("type")

        if rule_type == "intent_match":
            status_resolved = _apply_intent_match(rule, update_db, cache, user_content)

        elif rule_type == "state_transition":
            status_resolved = _apply_state_transition(rule, update_db, cache, user_content, dynamic_vars)

        elif rule_type == "keyword_list":
            status_resolved = _apply_keyword_list(rule, update_db, cache, user_content)

        elif rule_type == "field_audit":
            status_resolved = _apply_field_audit(rule, update_db, cache)

        elif rule_type == "document_role_match":
            _apply_document_role_match(rule, update_db, cache)

    # ── CAMADA 2: AI Fallback — minimal prompt when no rule matched ──
    if not status_resolved and user_content:
        print("[RulesApply] No deterministic rule matched → trying AI fallback (Camada 2)")
        ai_status = _ai_fallback_classify(
            compiled, cache, user_content, dynamic_vars, extraction_results
        )
        if ai_status:
            update_db["status_cotacao"] = ai_status
            print(f"[RulesApply] AI fallback → status_cotacao={ai_status}")

    return result


# ════════════════════════════════════════════════════════════════════════════════
# CAMADA 2: AI FALLBACK — Minimal prompt for ambiguous cases
# ════════════════════════════════════════════════════════════════════════════════

_FALLBACK_VALID_STATUSES = [
    "menu_inicial", "cotar", "corrigir", "cotar_corrigir",
    "validacao_humana", "finalizar", "confirmar", "dado_faltante"
]


def _ai_fallback_classify(
    compiled: Dict, cache: Dict, user_content: str,
    dynamic_vars: Dict, extraction_results: Dict
) -> Optional[str]:
    """
    Camada 2: When no deterministic rule resolved the status, call AI with a
    minimal prompt (~200 tokens) to classify. Returns status string or None.
    """
    try:
        from api.engine_controllers import _call_model, get_db
        db = get_db()

        # Find the cheapest/fastest model available for fallback
        fallback_models = db.query_raw('''
            SELECT m.id, m.providerModelId, p.baseUrl, p.apiKey, m.providerId,
                   m.costPerInputToken, m.costPerOutputToken
            FROM AIModel m JOIN AIProvider p ON m.providerId = p.id
            WHERE m.isPublic = 1
            ORDER BY m.costPerInputToken ASC LIMIT 1
        ''')
        if not fallback_models:
            print("[RulesApply] AI fallback: no model available")
            return None

        model_data = fallback_models[0]

        # Build concise field summary
        field_lines = []
        if isinstance(cache, dict):
            for k, v in cache.items():
                if v is not None and v != "" and v != []:
                    field_lines.append(f"  {k}: {v}")

        fields_str = "\n".join(field_lines) if field_lines else "  (nenhum campo preenchido)"
        status_entrada = dynamic_vars.get("status_cotacao_entrada", "desconhecido")
        valid_statuses = ", ".join(_FALLBACK_VALID_STATUSES)

        system_msg = "Você é um classificador de status de cotação logística. Responda APENAS com o status correto, sem explicação."
        user_msg = f"""Status de entrada: {status_entrada}
Mensagem do cliente: {user_content}
Campos preenchidos:
{fields_str}

Status válidos: {valid_statuses}
Qual é o status_cotacao correto? Responda APENAS o status."""

        result = _call_model(db, model_data, system_msg, user_msg, temperature=0.05)

        if result and isinstance(result, dict):
            status = result.get("status_cotacao", "")
        elif result and isinstance(result, str):
            status = result.strip().lower().replace('"', '').replace("'", "")
        else:
            return None

        # Validate the status
        if status in _FALLBACK_VALID_STATUSES:
            return status
        # Try to find a partial match
        for valid in _FALLBACK_VALID_STATUSES:
            if valid in status:
                return valid

        print(f"[RulesApply] AI fallback returned invalid status: '{status}'")
        return None

    except Exception as e:
        print(f"[RulesApply] AI fallback error: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════════
# RULE TYPE HANDLERS
# ════════════════════════════════════════════════════════════════════════════════

# Portuguese verb suffixes to strip for stem matching
_PT_SUFFIXES = [
    "ando", "endo", "indo",  # gerund
    "ação", "acao", "ção", "cao",  # noun forms
    "ado", "ido", "ado",  # past participle
    "ar", "er", "ir",  # infinitive
    "ou", "ei", "eu",  # past
    "am", "em",  # 3rd person plural
    "a", "e", "i", "o",  # conjugation endings
]


def _pt_stem(word: str) -> str:
    """Get a rough Portuguese stem by stripping common suffixes."""
    w = word.lower().strip()
    if len(w) <= 3:
        return w
    for suffix in _PT_SUFFIXES:
        if w.endswith(suffix) and len(w) - len(suffix) >= 3:
            return w[:-len(suffix)]
    return w


def _stem_match(trigger: str, text: str) -> bool:
    """Check if trigger matches text using substring, stem, and prefix matching."""
    trigger_low = trigger.lower()
    text_low = text.lower()
    # Direct substring match first
    if trigger_low in text_low:
        return True
    # Stem match + prefix fallback for irregular verbs (corrigir→corrija, g→j)
    trigger_stem = _pt_stem(trigger_low)
    if len(trigger_stem) >= 3:
        # Use min prefix length (handles g/j alternation: corrig- vs corrij-)
        prefix_len = max(3, len(trigger_stem) - 1)
        trigger_prefix = trigger_stem[:prefix_len]
        for word in text_low.split():
            word_clean = re.sub(r'[^\w]', '', word)
            if not word_clean:
                continue
            word_stem = _pt_stem(word_clean)
            if word_stem == trigger_stem:
                return True
            # Prefix fallback for irregular conjugations
            if len(word_stem) >= prefix_len and word_stem[:prefix_len] == trigger_prefix:
                return True
    return False


def _extract_dynamic_variables(var_defs: List[Dict], system_prompt: str) -> Dict[str, str]:
    """Extract dynamic variable values from system prompt using defined patterns."""
    variables = {}
    if not system_prompt or not var_defs:
        return variables

    for var_def in var_defs:
        name = var_def.get("name", "")
        pattern = var_def.get("pattern", "")
        if not name or not pattern:
            continue
        try:
            match = re.search(pattern, system_prompt, re.IGNORECASE)
            if match:
                variables[name] = match.group(1) if match.lastindex else match.group(0)
                print(f"[RulesApply] Dynamic var '{name}' = '{variables[name]}'")
        except re.error as e:
            print(f"[RulesApply] Invalid regex for dynamic var '{name}': {e}")

    return variables


def _apply_intent_match(rule: Dict, update_db: Dict, cache: Dict, user_content: str) -> bool:
    """
    Check if user content matches intent triggers.
    Returns True if status was set (stops further processing).
    """
    triggers = rule.get("triggers", [])
    if not triggers or not user_content:
        return False

    text = user_content.lower().strip()
    for trigger in triggers:
        if _stem_match(trigger, text):
            action = rule.get("action", {})
            if action:
                field = action.get("set_field")
                value = action.get("value")
                if field and value:
                    update_db[field] = value
                    print(f"[RulesApply] intent_match '{rule.get('id')}' → {field}={value} (trigger: '{trigger}')")
                    return True
    return False


def _apply_state_transition(
    rule: Dict, update_db: Dict, cache: Dict, user_content: str, dynamic_vars: Dict
) -> bool:
    """
    Apply state-based transitions using deterministic pattern matching.
    Returns True if status was set.
    """
    input_field = rule.get("input_field", "")
    transitions = rule.get("transitions", {})

    if not input_field or not transitions:
        return False

    # Get current state from dynamic variables or from update_db
    current_state = dynamic_vars.get(input_field) or update_db.get(input_field, "")
    if not current_state:
        return False

    # Find matching transition for current state
    state_transitions = transitions.get(current_state)
    if not state_transitions:
        return False

    if not isinstance(state_transitions, list):
        state_transitions = [state_transitions]

    text = user_content.lower().strip() if user_content else ""

    for transition in state_transitions:
        triggers = transition.get("triggers", [])
        action = transition.get("action", {})

        if not triggers:
            continue

        for trigger in triggers:
            if _stem_match(trigger, text):
                field = action.get("set_field")
                value = action.get("value")
                if field and value:
                    update_db[field] = value
                    print(f"[RulesApply] state_transition '{rule.get('id')}' state={current_state} → {field}={value} (trigger: '{trigger}')")
                    return True

    # Check for a default/fallback transition
    for transition in state_transitions:
        if transition.get("is_default"):
            action = transition.get("action", {})
            field = action.get("set_field")
            value = action.get("value")
            if field and value:
                update_db[field] = value
                print(f"[RulesApply] state_transition '{rule.get('id')}' state={current_state} → {field}={value} (default)")
                return True

    return False


def _apply_keyword_list(rule: Dict, update_db: Dict, cache: Dict, user_content: str) -> bool:
    """
    Check fields against keyword categories.
    Returns True if a match was found (stops further processing).
    """
    target_fields = rule.get("target_fields", [])
    categories = rule.get("categories", [])
    on_match = rule.get("on_match", {})

    if not categories or not on_match:
        return False

    # Build text to search — always include cache fields AND user content
    text_parts = []
    for field_name in target_fields:
        val = cache.get(field_name)
        if val:
            text_parts.append(str(val).lower())

    # Always check user_content for keyword matching (most reliable source)
    if user_content:
        text_parts.append(user_content.lower())

    search_text = " ".join(text_parts)
    if not search_text.strip():
        return False

    # Search all categories
    for category in categories:
        cat_name = category.get("name", "")
        keywords = category.get("keywords", [])
        for kw in keywords:
            if kw.lower() in search_text:
                field = on_match.get("set_field")
                value = on_match.get("value")
                if field and value:
                    update_db[field] = value
                    print(f"[RulesApply] keyword_list '{rule.get('id')}' matched '{kw}' (category: {cat_name}) → {field}={value}")
                    return True

    return False


def _apply_field_audit(rule: Dict, update_db: Dict, cache: Dict) -> bool:
    """
    Check required fields for completeness.
    Returns True (always resolves status at this stage).
    """
    required_fields = rule.get("required_fields", [])
    on_complete = rule.get("on_complete", {})
    on_incomplete = rule.get("on_incomplete", {})

    if not required_fields:
        return False

    # Find missing fields
    missing = []
    for field in required_fields:
        val = cache.get(field)
        if val is None or val == "" or val == "ausente" or val == []:
            missing.append(field)

    if missing:
        # Incomplete
        field = on_incomplete.get("set_field")
        value = on_incomplete.get("value")
        list_field = on_incomplete.get("list_missing_in")
        if field and value:
            update_db[field] = value
            if list_field:
                update_db[list_field] = missing
            print(f"[RulesApply] field_audit '{rule.get('id')}' → {field}={value} (missing: {missing})")
            return True
    else:
        # Complete
        field = on_complete.get("set_field")
        value = on_complete.get("value")
        list_field = on_complete.get("list_missing_in", on_incomplete.get("list_missing_in"))
        if field and value:
            update_db[field] = value
            if list_field:
                update_db[list_field] = []
            print(f"[RulesApply] field_audit '{rule.get('id')}' → {field}={value} (all complete)")
            return True

    return False


def _apply_document_role_match(rule: Dict, update_db: Dict, cache: Dict):
    """
    Compare document fields to classify roles (e.g., pagador CIF/FOB/Terceiro).
    Does NOT return True — this rule doesn't block other rules from executing.
    """
    compare = rule.get("compare_fields", {})
    outcomes = rule.get("outcomes", {})
    target_field = rule.get("target_field", "")

    if not compare or not outcomes or not target_field:
        return

    pagador_field = compare.get("pagador", "")
    remetente_field = compare.get("remetente", "")
    destinatario_field = compare.get("destinatario", "")

    pagador_val = cache.get(pagador_field, "")
    remetente_val = cache.get(remetente_field, "")
    destinatario_val = cache.get(destinatario_field, "")

    if not pagador_val:
        return

    result_value = None
    if pagador_val and remetente_val and pagador_val == remetente_val:
        result_value = outcomes.get("pagador_eq_remetente")
    elif pagador_val and destinatario_val and pagador_val == destinatario_val:
        result_value = outcomes.get("pagador_eq_destinatario")
    else:
        result_value = outcomes.get("default")

    if result_value:
        cache[target_field] = result_value
        print(f"[RulesApply] document_role_match '{rule.get('id')}' → {target_field}={result_value}")


def _apply_fabrication_guard(rule: Dict, cache: Dict, extraction_results: Optional[Dict]):
    """
    Validate AI-generated fields against function results.
    Nullify fields that were fabricated (function didn't find data but AI invented it).
    """
    if not extraction_results:
        return

    field = rule.get("field", "")
    source = rule.get("validation_source", "")
    path = rule.get("validation_path", "")
    on_fail = rule.get("on_fail", "nullify")

    if not field or not source:
        return

    # Get function result
    func_result = extraction_results.get(source, {})
    if not isinstance(func_result, dict):
        return

    # Navigate to the validation path
    has_data = False
    if path:
        parts = path.split(".")
        current = func_result
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                # Also check nested _raw/_resultado
                if current is None:
                    raw = func_result.get("_raw", func_result.get("_resultado", {}))
                    if isinstance(raw, dict):
                        current = raw.get(part)
            else:
                current = None
                break
        if isinstance(current, list):
            has_data = len(current) > 0
        elif current is not None:
            has_data = bool(current)
    else:
        # No path — just check if function returned any non-meta data
        has_data = any(k for k in func_result if not k.startswith("_"))

    if not has_data and cache.get(field) is not None:
        if on_fail == "nullify":
            print(f"[RulesApply] fabrication_guard: nullifying '{field}' ({source} found nothing)")
            cache[field] = None
            # Also nullify related extenso fields
            extenso_field = f"{field}_extenso"
            if extenso_field in cache:
                cache[extenso_field] = None


def _apply_format_rule(rule: Dict, cache: Dict):
    """
    Apply formatting rules to cache fields.
    """
    field_pattern = rule.get("field_pattern", "")
    transform = rule.get("transform", "")
    expected_length = rule.get("expected_length")

    if not field_pattern or not transform:
        return

    try:
        pattern = re.compile(field_pattern)
    except re.error:
        return

    for field_name, value in list(cache.items()):
        if not pattern.match(field_name) or value is None:
            continue

        original = str(value)

        if transform == "digits_only":
            new_value = re.sub(r"[^\d]", "", original)
            if expected_length and len(new_value) != expected_length:
                continue  # Don't transform if length doesn't match
            cache[field_name] = new_value

        elif transform == "uppercase":
            cache[field_name] = original.upper()

        elif transform == "lowercase":
            cache[field_name] = original.lower()

        elif transform == "strip_non_digits":
            cache[field_name] = re.sub(r"[^\d]", "", original)
