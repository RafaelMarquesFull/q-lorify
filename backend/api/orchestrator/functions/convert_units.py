"""
Convert Units / Dimension Converter Function
Detects measurement patterns in text and converts to a target unit.

Supports:
  - Units: mm, cm, m, km, pol/in (inches), ft (feet), yd (yards), mi (miles)
  - Inch symbol: " and ″  (e.g. 10", 1,5″)
  - Fractions: 1/2", 3/4", 1/4"
  - Diameter symbol: Ø (marks output as is_diameter=True)
  - Mixed-unit sequences on the same line (e.g. "25,4 cm 10" 0,3 m")
  - Dimension group labels: "Dimensões:", "Dimensão:", "Dim:"
  - Grouped dimensions with x separator: "36 x 30 x 55 CM"
"""
import re
from typing import Dict, Any, List, Optional, Tuple
from fractions import Fraction


# ──────────────────────────────────────────────────────────
# Conversion factors — everything relative to METERS
# ──────────────────────────────────────────────────────────
_TO_METERS: Dict[str, float] = {
    "mm":  0.001,
    "cm":  0.01,
    "m":   1.0,
    "km":  1000.0,
    "pol": 0.0254,       # 1 inch = 0.0254 m
    "in":  0.0254,
    "ft":  0.3048,       # 1 foot = 0.3048 m
    "yd":  0.9144,       # 1 yard = 0.9144 m
    "mi":  1609.344,     # 1 mile = 1609.344 m
}

# Human-readable unit labels (pt-BR)
_UNIT_LABELS: Dict[str, str] = {
    "mm":  "milímetros",
    "cm":  "centímetros",
    "m":   "metros",
    "km":  "quilômetros",
    "pol": "polegadas",
    "in":  "polegadas",
    "ft":  "pés",
    "yd":  "jardas",
    "mi":  "milhas",
}

# ──────────────────────────────────────────────────────────
# Unit pattern table  (order matters — longer/more specific first)
# ──────────────────────────────────────────────────────────
_UNIT_PATTERNS: List[Tuple[str, str]] = [
    # Full words (Portuguese / English)
    (r'milímetros?|milimetros?',         'mm'),
    (r'centímetros?|centimetros?',       'cm'),
    (r'quilômetros?|quilometros?|kms?',  'km'),
    (r'polegadas?',                      'pol'),
    (r'inch(?:es)?',                     'pol'),
    (r'pés|pes|feet|foot',               'ft'),
    (r'jardas?|yards?',                  'yd'),
    (r'milhas?|miles?',                  'mi'),
    (r'metros?',                         'm'),
    # Abbreviations
    (r'mm',   'mm'),
    (r'cm',   'cm'),
    (r'km',   'km'),
    (r'pol',  'pol'),
    (r'ft',   'ft'),
    (r'yd',   'yd'),
    (r'mi',   'mi'),
    (r'm',    'm'),   # 'm' last to avoid matching 'mm','mi','milhas' etc.
]

_ALL_UNITS_RE = '|'.join(pat for pat, _ in _UNIT_PATTERNS)


# ──────────────────────────────────────────────────────────
# Individual measurement regex
# ──────────────────────────────────────────────────────────
# Matches patterns like:
#   Ø 3/4"         → diameter, fraction, inches
#   10"            → 10 inches (quote)
#   1,5″           → 1.5 inches (unicode double prime)
#   25,4 cm        → 25.4 cm
#   0,3 m          → 0.3 m
#   Ø 50 mm        → diameter 50 mm
#   1500 mm        → 1500 mm

# Number: integers, decimals with . or , (e.g. 1234, 3.5, 25,4, 1.234,56)
_NUM_PAT = r'\d+(?:[.,]\d+)*'

# Fraction: 1/2, 3/4, etc. (optionally preceded by a whole number)
_FRAC_PAT = r'\d+/\d+'
_WHOLE_FRAC_PAT = r'\d+\s+\d+/\d+'  # e.g. "1 1/2"

# Inch symbols: " or ″
_INCH_SYMBOL = r'["\u2033]'

# Diameter symbol (optional)
_DIAMETER = r'[Øø∅]'

# Build individual measurement regex
# Group 1: Diameter mark (optional)
# Group 2: Whole+Fraction OR Fraction OR Decimal number
# Group 3: Unit text OR inch symbol
_INDIVIDUAL_RE = re.compile(
    r'(?P<diameter>' + _DIAMETER + r')?\s*'
    r'(?:'
        r'(?P<whole_frac>' + _WHOLE_FRAC_PAT + r')'   # "1 1/2"
        r'|(?P<frac>' + _FRAC_PAT + r')'               # "3/4"
        r'|(?P<number>' + _NUM_PAT + r')'               # "25,4"
    r')\s*'
    r'(?:'
        r'(?P<inch_sym>' + _INCH_SYMBOL + r')'          # " or ″
        r'|(?P<unit>' + _ALL_UNITS_RE + r')'            # mm, cm, m, etc.
    r')'
    r'(?:\b|(?=\s|$|[^a-záéíóúàãõç]))',
    re.IGNORECASE
)

# Grouped dimensions: "36 x 30 x 55 CM" (same unit for all values)
_DIMENSIONS_X_RE = re.compile(
    r'(?P<n1>' + _NUM_PAT + r')\s*[xX×]\s*'
    r'(?P<n2>' + _NUM_PAT + r')'
    r'(?:\s*[xX×]\s*(?P<n3>' + _NUM_PAT + r'))?\s*'
    r'(?P<unit>' + _ALL_UNITS_RE + r')'
    r'(?:\b|(?=\s|$|[^a-záéíóúàãõç]))',
    re.IGNORECASE
)

# Dimension label pattern (to detect lines that start with "Dimensões:", etc.)
_DIM_LABEL_RE = re.compile(
    r'^(?:dimens[ãa]o|dimens[õo]es|dim\.?)\s*:\s*',
    re.IGNORECASE | re.MULTILINE
)

# Quantity prefix pattern: matches "20 unidades", "10 caixas de", "5 de", "1=", etc.
# immediately before a dimension group
_QTY_PREFIX_RE = re.compile(
    r'(\d+)\s*(?:unidades?|caixas?|volumes?|paletes?|itens?|pçs?|peças?|un\.?)?\s*(?:de\s+|=)?$',
    re.IGNORECASE
)


def _extract_quantity_before(line: str, match_start: int) -> Optional[int]:
    """Look backwards from a dimension match to find a quantity prefix."""
    prefix = line[:match_start]
    qty_match = _QTY_PREFIX_RE.search(prefix)
    if qty_match:
        return int(qty_match.group(1))
    return None


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


def _parse_value(match: re.Match) -> float:
    """Extract the numeric value from a measurement match."""
    if match.group('whole_frac'):
        # e.g. "1 1/2" → 1.5
        parts = match.group('whole_frac').split()
        whole = float(parts[0])
        frac = Fraction(parts[1])
        return whole + float(frac)
    elif match.group('frac'):
        # e.g. "3/4" → 0.75
        return float(Fraction(match.group('frac')))
    else:
        return _parse_number(match.group('number'))


def _resolve_unit(raw_unit: str) -> Optional[str]:
    """Map a raw matched unit text to the canonical key."""
    raw = raw_unit.strip().lower()
    for pattern, canonical in _UNIT_PATTERNS:
        if re.fullmatch(pattern, raw, re.IGNORECASE):
            return canonical
    return None


def _get_unit_from_match(match: re.Match) -> str:
    """Determine the unit from a match (either explicit unit or inch symbol)."""
    if match.group('inch_sym'):
        return 'pol'
    raw = match.group('unit')
    resolved = _resolve_unit(raw)
    return resolved if resolved else 'pol'


def _convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value from one unit to another via meters."""
    from_key = from_unit if from_unit in _TO_METERS else 'pol'
    to_key = to_unit if to_unit in _TO_METERS else 'm'
    meters = value * _TO_METERS[from_key]
    return meters / _TO_METERS[to_key]


def _format_value(value: float, precision: int) -> float:
    """Round a value to the given precision, with adaptive precision for small values.
    
    If rounding would produce 0.0 for a non-zero value, automatically
    increases precision to preserve at least 2 significant digits.
    E.g. 0.0025 with precision=2 → 0.0025 (not 0.0)
    """
    import math
    rounded = round(value, precision)
    if rounded == 0.0 and value != 0.0:
        # Calculate how many decimal places we need for 2 significant digits
        # e.g. for 0.0025 → log10(0.0025) = -2.6 → ceil(2.6) = 3 → 3+1 = 4
        magnitude = -math.floor(math.log10(abs(value)))
        needed_precision = magnitude + 1  # +1 for at least 2 significant digits
        return round(value, max(precision, needed_precision))
    return rounded


# ──────────────────────────────────────────────────────────
# Main execute function
# ──────────────────────────────────────────────────────────

def execute(
    content: str,
    target_unit: str = "m",
    precision: int = 2,
    group_by_line: bool = True
) -> Dict[str, Any]:
    """
    Detect measurement patterns in text and convert to target_unit.

    Args:
        content: Text to scan for measurements
        target_unit: The unit to convert to (mm, cm, m, km, pol, ft, yd, mi)
        precision: Decimal places in the converted values (default: 2)
        group_by_line: If True, group measurements from the same line (default: True)

    Returns:
        Dictionary with detected measurements and their conversions
    """
    target_unit = target_unit.lower().strip()
    if target_unit in ('"', '″', 'polegada', 'polegadas', 'inch', 'inches'):
        target_unit = 'pol'
    if target_unit not in _TO_METERS:
        target_unit = "m"

    precision = max(0, min(precision, 10))

    all_measurements: List[Dict[str, Any]] = []
    dimension_groups: List[Dict[str, Any]] = []
    seen_spans: List[Tuple[int, int]] = []  # track matched spans to avoid overlaps

    lines = content.split('\n')
    global_offset = 0

    for line_idx, line in enumerate(lines):
        line_measurements = []

        # ── 1) Try grouped "x" dimensions first: "36 x 30 x 55 CM" ──
        for match in _DIMENSIONS_X_RE.finditer(line):
            span = (global_offset + match.start(), global_offset + match.end())
            raw_unit_text = match.group('unit')
            source_unit = _resolve_unit(raw_unit_text)
            if not source_unit:
                continue

            nums = [match.group('n1'), match.group('n2')]
            if match.group('n3'):
                nums.append(match.group('n3'))

            converted_dims = []
            for num_str in nums:
                value = _parse_number(num_str)
                converted_value = _convert(value, source_unit, target_unit)
                converted_dims.append({
                    "original_value": value,
                    "original_unit": source_unit,
                    "converted_value": _format_value(converted_value, precision),
                })

            # Detect quantity prefix (e.g. "20 unidades 20x30x40 cm")
            qty = _extract_quantity_before(line, match.start())

            entry = {
                "original": match.group(0).strip(),
                "type": "dimensions",
                "source_unit": source_unit,
                "target_unit": target_unit,
                "source_label": _UNIT_LABELS.get(source_unit, source_unit),
                "target_label": _UNIT_LABELS.get(target_unit, target_unit),
                "is_diameter": False,
                "quantity": qty,
                "values": converted_dims,
                "converted_text": " x ".join(
                    str(d["converted_value"]) for d in converted_dims
                ) + f" {target_unit}",
            }

            line_measurements.append(entry)
            all_measurements.append(entry)
            seen_spans.append(span)

        # ── 2) Individual measurements (with mixed units per line) ──
        for match in _INDIVIDUAL_RE.finditer(line):
            span = (global_offset + match.start(), global_offset + match.end())

            # Skip if overlapping with an "x" dimension match
            overlap = False
            for s_start, s_end in seen_spans:
                if not (span[1] <= s_start or span[0] >= s_end):
                    overlap = True
                    break
            if overlap:
                continue

            value = _parse_value(match)
            source_unit = _get_unit_from_match(match)
            is_diameter = bool(match.group('diameter'))
            converted_value = _convert(value, source_unit, target_unit)

            entry = {
                "original": match.group(0).strip(),
                "type": "single",
                "source_unit": source_unit,
                "target_unit": target_unit,
                "source_label": _UNIT_LABELS.get(source_unit, source_unit),
                "target_label": _UNIT_LABELS.get(target_unit, target_unit),
                "is_diameter": is_diameter,
                "value": value,
                "converted_value": _format_value(converted_value, precision),
                "converted_text": f"{_format_value(converted_value, precision)} {target_unit}",
            }

            line_measurements.append(entry)
            all_measurements.append(entry)
            seen_spans.append(span)

        # ── 3) Group measurements by line ──
        if group_by_line and len(line_measurements) > 1:
            # Check if this line has a "Dimensões:" label
            has_label = bool(_DIM_LABEL_RE.match(line.strip()))
            dimension_groups.append({
                "line": line.strip(),
                "line_number": line_idx + 1,
                "has_label": has_label,
                "measurements": line_measurements,
                "converted_summary": ", ".join(
                    m.get("converted_text", "") for m in line_measurements
                ),
            })

        global_offset += len(line) + 1  # +1 for the \n

    if not all_measurements:
        return {
            "found": False,
            "count": 0,
            "measurements": [],
            "dimension_groups": [],
            "summary": "Nenhuma medida encontrada no texto",
            "message": "Nenhuma medida encontrada no texto"
        }

    # Build summary
    target_label = _UNIT_LABELS.get(target_unit, target_unit)
    converted_vals = []
    for m in all_measurements:
        if m["type"] == "dimensions":
            for v in m.get("values", []):
                converted_vals.append(str(v["converted_value"]))
        else:
            converted_vals.append(str(m["converted_value"]))

    summary = (
        f"{len(all_measurements)} medida(s) detectada(s), "
        f"convertida(s) para {target_label}: "
        + ", ".join(converted_vals[:10])
    )
    if len(converted_vals) > 10:
        summary += f" ... (+{len(converted_vals) - 10} mais)"

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
    # formatted_dimensions: list of "AxLxC" strings grouped by dimension_groups,
    # or individual values if no groups
    formatted_dims = []
    if dimension_groups:
        for g in dimension_groups:
            g_measurements = g.get("measurements", [])
            for m in g_measurements:
                if m.get("type") == "dimensions":
                    vals = [str(v["converted_value"]) for v in m.get("values", [])]
                    if vals:
                        dim_str = "x".join(vals)
                        qty = m.get("quantity")
                        if qty and qty > 1:
                            dim_str = f"{qty}={dim_str}"
                        formatted_dims.append(dim_str)
                else:
                    formatted_dims.append(str(m.get("converted_value", "")))
    else:
        # No dimension groups — list individual converted values
        for m in all_measurements:
            if m.get("type") == "dimensions":
                vals = [str(v["converted_value"]) for v in m.get("values", [])]
                if vals:
                    dim_str = "x".join(vals)
                    qty = m.get("quantity")
                    if qty and qty > 1:
                        dim_str = f"{qty}={dim_str}"
                    formatted_dims.append(dim_str)
            else:
                formatted_dims.append(str(m.get("converted_value", "")))

    result["formatted_dimensions"] = formatted_dims
    
    # Individual flat values (useful for schemas that want separate values)
    individual_values = []
    for m in all_measurements:
        if m.get("type") == "dimensions":
            for v in m.get("values", []):
                individual_values.append(v["converted_value"])
        else:
            individual_values.append(m.get("converted_value"))
    result["individual_values"] = individual_values

    # _summary: concise human-readable text for the AI reformatter
    dim_text = ", ".join(formatted_dims) if formatted_dims else "nenhuma"
    result["_summary"] = (
        f"Dimensões encontradas: {dim_text} ({target_label}). "
        f"Total: {len(all_measurements)} medida(s)."
    )

    return result
