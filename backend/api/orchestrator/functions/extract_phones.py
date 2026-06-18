"""
Extract Phone Numbers Function
Extracts Brazilian phone numbers from text.
Filters out false positives from CNPJ/CPF numbers.
"""
import re
from typing import Dict, Any, List


def execute(content: str, format_output: bool = True) -> Dict[str, Any]:
    """
    Extract Brazilian phone numbers from text content.
    
    Args:
        content: Text to search for phone numbers
        format_output: If True, format numbers in standard format
    
    Returns:
        Dictionary with found phone numbers
    """
    # First, identify CNPJ/CPF positions to exclude them
    cnpj_positions = set()
    cnpj_pattern = r'\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b'
    for match in re.finditer(cnpj_pattern, content):
        for i in range(match.start(), match.end()):
            cnpj_positions.add(i)
    
    cpf_pattern = r'\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b'
    for match in re.finditer(cpf_pattern, content):
        for i in range(match.start(), match.end()):
            cnpj_positions.add(i)
    
    # Brazilian phone patterns
    # Matches: (11) 99999-9999, 11 99999-9999, 11999999999, +55 11 99999-9999
    patterns = [
        r'\+?55\s*\(?(\d{2})\)?\s*(\d{4,5})[-\s]?(\d{4})',  # With country code
        r'\(?(\d{2})\)?\s*(\d{4,5})[-\s]?(\d{4})',  # Without country code
    ]
    
    phones = []
    
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            # Skip if this match overlaps with a CNPJ/CPF position
            match_positions = set(range(match.start(), match.end()))
            if match_positions & cnpj_positions:
                continue
            
            ddd = match.group(1)
            part1 = match.group(2)
            part2 = match.group(3)
            
            # Validate DDD (valid Brazilian area codes are 11-99, but must be valid)
            ddd_int = int(ddd)
            if ddd_int < 11 or ddd_int > 99:
                continue
            
            raw = f"{ddd}{part1}{part2}"
            
            # Skip if total digits don't match phone format (10 or 11 digits)
            if len(raw) not in (10, 11):
                continue
            
            if format_output:
                formatted = f"({ddd}) {part1}-{part2}"
            else:
                formatted = raw
            
            phone_info = {
                "raw": raw,
                "formatted": formatted,
                "ddd": ddd,
                "is_mobile": len(part1) == 5 and part1.startswith('9')
            }
            
            # Avoid duplicates
            if raw not in [p["raw"] for p in phones]:
                phones.append(phone_info)
    
    return {
        "found": len(phones) > 0,
        "count": len(phones),
        "phones": phones
    }
