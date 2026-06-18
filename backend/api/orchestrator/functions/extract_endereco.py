"""
Extract Address Function
Extracts Brazilian addresses from text using pattern matching.
"""
import re
from typing import Dict, Any, List


def execute(content: str, detailed: bool = True) -> Dict[str, Any]:
    """
    Extract addresses from text content.
    
    Args:
        content: Text to search for addresses
        detailed: If True, try to parse address components
    
    Returns:
        Dictionary with found addresses
    """
    results = []
    
    # Common address patterns
    # Rua/Av./Alameda + name + number
    address_patterns = [
        # Rua/Av./etc + nome + número
        r'(?:Rua|R\.|Avenida|Av\.|Alameda|Al\.|Travessa|Tv\.|Praça|Pç\.|Estrada|Est\.)\s+([^,\n]+?)\s*,?\s*(?:n[º°]?\s*)?(\d+)',
        # More flexible pattern
        r'(?:Rua|Avenida|Alameda|Travessa|Praça|Estrada)\s+[\w\s]+\s*,?\s*\d+',
    ]
    
    for pattern in address_patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            full_match = match.group(0)
            
            # Avoid duplicates
            if any(full_match in r.get("raw", "") or r.get("raw", "") in full_match for r in results):
                continue
            
            address_info = {
                "raw": full_match.strip(),
                "position": match.start()
            }
            
            if detailed:
                # Try to parse components
                address_info["components"] = parse_address_components(full_match)
            
            results.append(address_info)
    
    # Sort by position
    results.sort(key=lambda x: x["position"])
    
    return {
        "found": len(results) > 0,
        "count": len(results),
        "addresses": results
    }


def parse_address_components(address: str) -> Dict[str, str]:
    """Parse address into components."""
    components = {}
    
    # Extract street type
    type_match = re.match(
        r'(Rua|R\.|Avenida|Av\.|Alameda|Al\.|Travessa|Tv\.|Praça|Pç\.|Estrada|Est\.)',
        address,
        re.IGNORECASE
    )
    if type_match:
        type_str = type_match.group(1).lower()
        type_map = {
            'rua': 'Rua', 'r.': 'Rua',
            'avenida': 'Avenida', 'av.': 'Avenida',
            'alameda': 'Alameda', 'al.': 'Alameda',
            'travessa': 'Travessa', 'tv.': 'Travessa',
            'praça': 'Praça', 'pç.': 'Praça',
            'estrada': 'Estrada', 'est.': 'Estrada'
        }
        components["type"] = type_map.get(type_str, type_str.title())
    
    # Extract number
    number_match = re.search(r',?\s*(?:n[º°]?\s*)?(\d+)\s*$', address)
    if number_match:
        components["number"] = number_match.group(1)
    
    # Extract street name (between type and number)
    if type_match and number_match:
        name_start = type_match.end()
        name_end = number_match.start()
        name = address[name_start:name_end].strip(' ,')
        components["street"] = name
    
    return components
