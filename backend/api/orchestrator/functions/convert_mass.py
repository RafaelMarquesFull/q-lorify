"""
Convert Mass Function
Detects mass/weight patterns in text and converts to a target unit.
Always includes the converted value written out in full Portuguese ("por extenso").

Supports:
  - Units: t (tonelada), kg (quilo), g (grama), mg (miligrama),
           lb (libra), oz (onça), @ (arroba)
  - Mixed-unit sequences on the same line
  - Portuguese number-to-words output
"""
import re
import math
from typing import Dict, Any, List, Optional, Tuple


# ──────────────────────────────────────────────────────────
# Conversion factors — everything relative to GRAMS
# ──────────────────────────────────────────────────────────
_TO_GRAMS: Dict[str, float] = {
    "t":   1_000_000.0,    # 1 tonelada = 1.000.000 g
    "kg":  1_000.0,        # 1 quilo = 1.000 g
    "g":   1.0,            # base unit
    "mg":  0.001,          # 1 miligrama = 0.001 g
    "lb":  453.592,        # 1 libra = 453.592 g
    "oz":  28.3495,        # 1 onça = 28.3495 g
    "@":   14_688.0,       # 1 arroba = 14.688 kg = 14688 g
}

# Human-readable unit labels (pt-BR) — singular and plural
_UNIT_LABELS: Dict[str, Tuple[str, str]] = {
    "t":   ("tonelada", "toneladas"),
    "kg":  ("quilo", "quilos"),
    "g":   ("grama", "gramas"),
    "mg":  ("miligrama", "miligramas"),
    "lb":  ("libra", "libras"),
    "oz":  ("onça", "onças"),
    "@":   ("arroba", "arrobas"),
}

# Short labels for output
_UNIT_SHORT: Dict[str, str] = {
    "t": "t", "kg": "kg", "g": "g", "mg": "mg",
    "lb": "lb", "oz": "oz", "@": "@",
}


# ──────────────────────────────────────────────────────────
# Unit pattern table (order: longer/more specific first)
# ──────────────────────────────────────────────────────────
_MASS_UNIT_PATTERNS: List[Tuple[str, str]] = [
    # Full words (Portuguese)
    (r'toneladas?',                            't'),
    (r'quilogramas?|quilos?|kilogramas?|kilos?', 'kg'),
    (r'miligramas?',                           'mg'),
    (r'gramas?',                               'g'),
    (r'libras?|pounds?',                       'lb'),
    (r'on[çc]as?|ounces?',                     'oz'),
    (r'arrobas?',                              '@'),
    # Abbreviations
    (r'kg',    'kg'),
    (r'mg',    'mg'),
    (r'oz',    'oz'),
    (r'lb',    'lb'),
    (r'lbs',   'lb'),
    (r't',     't'),
    (r'g',     'g'),   # 'g' last to avoid matching 'mg', 'kg'
]

_ALL_MASS_UNITS_RE = '|'.join(pat for pat, _ in _MASS_UNIT_PATTERNS)

# Number pattern: integers, decimals with . or , (e.g. 1234, 3.5, 25,4, 1.234,56)
_NUM_PAT = r'\d+(?:[.,]\d+)*'

# Individual mass measurement regex
_MASS_RE = re.compile(
    r'(?P<number>' + _NUM_PAT + r')\s*'
    r'(?P<unit>' + _ALL_MASS_UNITS_RE + r')'
    r'(?:\b|(?=\s|$|[^a-záéíóúàãõç]))',
    re.IGNORECASE
)


# ──────────────────────────────────────────────────────────
# Number-to-words in Portuguese (por extenso)
# ──────────────────────────────────────────────────────────

_UNITS = [
    "zero", "um", "dois", "três", "quatro", "cinco",
    "seis", "sete", "oito", "nove", "dez", "onze",
    "doze", "treze", "quatorze", "quinze", "dezesseis",
    "dezessete", "dezoito", "dezenove"
]

_TENS = [
    "", "dez", "vinte", "trinta", "quarenta", "cinquenta",
    "sessenta", "setenta", "oitenta", "noventa"
]

_HUNDREDS = [
    "", "cento", "duzentos", "trezentos", "quatrocentos",
    "quinhentos", "seiscentos", "setecentos", "oitocentos",
    "novecentos"
]

# (singular, plural) for each power-of-thousand group
_GROUPS = [
    ("", ""),
    ("mil", "mil"),
    ("milhão", "milhões"),
    ("bilhão", "bilhões"),
    ("trilhão", "trilhões"),
]


def _int_to_extenso(n: int) -> str:
    """Convert an integer to its Portuguese written form (por extenso)."""
    if n < 0:
        return "menos " + _int_to_extenso(-n)
    if n == 0:
        return "zero"
    if n == 100:
        return "cem"

    parts = []
    group_index = 0

    while n > 0:
        chunk = n % 1000
        n //= 1000

        if chunk == 0:
            group_index += 1
            continue

        chunk_text = _chunk_to_text(chunk)

        if group_index > 0 and group_index < len(_GROUPS):
            singular, plural = _GROUPS[group_index]
            group_label = plural if chunk > 1 and group_index >= 2 else singular
            chunk_text = chunk_text + " " + group_label

        parts.append(chunk_text)
        group_index += 1

    parts.reverse()

    # Join with " e " for readability
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[0] + " e " + parts[1]
    else:
        # "um milhão, duzentos mil e trinta"
        return ", ".join(parts[:-1]) + " e " + parts[-1]


def _chunk_to_text(n: int) -> str:
    """Convert a number 1-999 to Portuguese text."""
    if n == 0:
        return ""
    if n == 100:
        return "cem"
    if n < 20:
        return _UNITS[n]
    if n < 100:
        tens = n // 10
        units = n % 10
        if units == 0:
            return _TENS[tens]
        return _TENS[tens] + " e " + _UNITS[units]

    # 100-999
    hundreds = n // 100
    remainder = n % 100
    if remainder == 0:
        return "cem" if hundreds == 1 else _HUNDREDS[hundreds]

    hundreds_text = _HUNDREDS[hundreds]
    remainder_text = _chunk_to_text(remainder)
    return hundreds_text + " e " + remainder_text


def numero_por_extenso(value: float) -> str:
    """
    Convert a number (including decimals) to its Portuguese written form.

    Examples:
        1000 → "um mil"
        1.5  → "um vírgula cinco"
        0.5  → "zero vírgula cinco"
        1500 → "um mil e quinhentos"
        2500000 → "dois milhões e quinhentos mil"
    """
    if value == int(value):
        return _int_to_extenso(int(value))

    # Split integer and decimal parts
    int_part = int(value)
    dec_part = value - int_part

    # Get decimal digits (up to 6 significant digits)
    dec_str = f"{dec_part:.6f}".split('.')[1].rstrip('0')

    if not dec_str:
        return _int_to_extenso(int_part)

    int_text = _int_to_extenso(int_part)

    # Write each decimal digit individually
    dec_digits = [_UNITS[int(d)] for d in dec_str]
    dec_text = " ".join(dec_digits)

    return f"{int_text} vírgula {dec_text}"


# ──────────────────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────────────────

def _parse_number(s: str) -> float:
    """Parse a number string that may use . or , as decimal/thousands separator."""
    s = s.strip()
    if '.' in s and ',' in s:
        if s.rindex(',') > s.rindex('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        parts = s.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(',', '.')
        else:
            s = s.replace(',', '')
    return float(s)


def _resolve_unit(raw_unit: str) -> Optional[str]:
    """Map a raw matched unit text to the canonical key."""
    raw = raw_unit.strip().lower()
    for pattern, canonical in _MASS_UNIT_PATTERNS:
        if re.fullmatch(pattern, raw, re.IGNORECASE):
            return canonical
    return None


def _convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value from one mass unit to another via grams."""
    grams = value * _TO_GRAMS.get(from_unit, 1.0)
    return grams / _TO_GRAMS.get(to_unit, 1.0)


def _get_label(unit: str, value: float) -> str:
    """Get the appropriate singular/plural label for a unit."""
    labels = _UNIT_LABELS.get(unit, (unit, unit))
    return labels[0] if abs(value) == 1 else labels[1]


def _format_value(value: float, precision: int) -> float:
    """Round a value to the given precision."""
    return round(value, precision)


# ──────────────────────────────────────────────────────────
# Main execute function
# ──────────────────────────────────────────────────────────

def execute(
    content: str,
    target_unit: str = "kg",
    precision: int = 2,
    group_by_line: bool = True
) -> Dict[str, Any]:
    """
    Detect mass/weight patterns in text and convert to target_unit.
    Always includes the converted value written out in Portuguese ("por extenso").

    Args:
        content: Text to scan for mass measurements
        target_unit: The unit to convert to (t, kg, g, mg, lb, oz, @)
        precision: Decimal places in the converted values (default: 2)
        group_by_line: If True, group measurements from the same line (default: True)

    Returns:
        Dictionary with detected measurements, conversions, and "por extenso" text
    """
    # Normalize target unit
    target_unit = target_unit.lower().strip()
    unit_aliases = {
        'tonelada': 't', 'toneladas': 't', 'ton': 't',
        'quilo': 'kg', 'quilos': 'kg', 'quilograma': 'kg', 'quilogramas': 'kg',
        'kilo': 'kg', 'kilos': 'kg',
        'grama': 'g', 'gramas': 'g',
        'miligrama': 'mg', 'miligramas': 'mg',
        'libra': 'lb', 'libras': 'lb', 'lbs': 'lb', 'pound': 'lb', 'pounds': 'lb',
        'onça': 'oz', 'onças': 'oz', 'ounce': 'oz', 'ounces': 'oz',
        'arroba': '@', 'arrobas': '@',
    }
    target_unit = unit_aliases.get(target_unit, target_unit)
    if target_unit not in _TO_GRAMS:
        target_unit = "kg"

    precision = max(0, min(precision, 10))

    all_measurements: List[Dict[str, Any]] = []
    dimension_groups: List[Dict[str, Any]] = []
    seen_spans: List[Tuple[int, int]] = []

    lines = content.split('\n')
    global_offset = 0

    for line_idx, line in enumerate(lines):
        line_measurements = []

        for match in _MASS_RE.finditer(line):
            span = (global_offset + match.start(), global_offset + match.end())

            # Skip overlapping matches
            overlap = False
            for s_start, s_end in seen_spans:
                if not (span[1] <= s_start or span[0] >= s_end):
                    overlap = True
                    break
            if overlap:
                continue

            value = _parse_number(match.group('number'))
            source_unit = _resolve_unit(match.group('unit'))
            if not source_unit:
                continue

            converted_value = _convert(value, source_unit, target_unit)
            formatted_value = _format_value(converted_value, precision)

            # Labels
            source_label_singular, source_label_plural = _UNIT_LABELS.get(source_unit, (source_unit, source_unit))
            target_label_singular, target_label_plural = _UNIT_LABELS.get(target_unit, (target_unit, target_unit))
            source_label = source_label_singular if abs(value) == 1 else source_label_plural
            target_label = target_label_singular if abs(formatted_value) == 1 else target_label_plural

            # Por extenso
            extenso = numero_por_extenso(formatted_value)
            extenso_full = f"{extenso} {target_label}"

            entry = {
                "original": match.group(0).strip(),
                "type": "single",
                "source_unit": source_unit,
                "target_unit": target_unit,
                "source_label": source_label,
                "target_label": target_label,
                "value": value,
                "converted_value": formatted_value,
                "converted_text": f"{formatted_value} {_UNIT_SHORT.get(target_unit, target_unit)}",
                "extenso": extenso_full,
            }

            line_measurements.append(entry)
            all_measurements.append(entry)
            seen_spans.append(span)

        # Group by line
        if group_by_line and len(line_measurements) > 1:
            dimension_groups.append({
                "line": line.strip(),
                "line_number": line_idx + 1,
                "measurements": line_measurements,
                "converted_summary": ", ".join(
                    m["converted_text"] for m in line_measurements
                ),
            })

        global_offset += len(line) + 1

    if not all_measurements:
        return {
            "found": False,
            "count": 0,
            "measurements": [],
            "dimension_groups": [],
            "summary": "Nenhuma medida de massa encontrada no texto",
            "message": "Nenhuma medida de massa encontrada no texto"
        }

    # Build summary
    target_label = _UNIT_LABELS.get(target_unit, (target_unit, target_unit))[1]
    summary_parts = []
    for m in all_measurements:
        summary_parts.append(f"{m['converted_value']} {_UNIT_SHORT.get(target_unit, target_unit)} ({m['extenso']})")

    summary = (
        f"{len(all_measurements)} medida(s) de massa detectada(s), "
        f"convertida(s) para {target_label}: "
        + "; ".join(summary_parts[:10])
    )
    if len(summary_parts) > 10:
        summary += f" ... (+{len(summary_parts) - 10} mais)"

    result = {
        "found": True,
        "count": len(all_measurements),
        "target_unit": target_unit,
        "target_label": target_label,
        "measurements": all_measurements,
        "summary": summary,
    }

    if group_by_line and dimension_groups:
        result["dimension_groups"] = dimension_groups

    # ── Structured output for AI reformatter ──
    peso_extenso = []
    peso_numerico = []
    for m in all_measurements:
        peso_numerico.append(m.get("converted_value"))
        extenso = m.get("extenso", "")
        if extenso:
            unit_short = _UNIT_SHORT.get(target_unit, target_unit)
            peso_extenso.append(f"{m['converted_value']} {unit_short} ({extenso})")
    
    result["peso_extenso"] = peso_extenso
    result["peso_numerico"] = peso_numerico

    # _summary: concise human-readable text for the AI reformatter
    extenso_text = "; ".join(peso_extenso) if peso_extenso else "nenhum"
    result["_summary"] = (
        f"Peso encontrado: {extenso_text}. "
        f"Total: {len(all_measurements)} medida(s) de massa."
    )

    return result
