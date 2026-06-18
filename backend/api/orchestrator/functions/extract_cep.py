"""
Extract CEP Function
Extracts Brazilian ZIP codes (CEP) from text.
Optionally enriches with address data from ViaCEP and OpenCEP (fallback).
"""
import re
import requests
from typing import Dict, Any, Optional


def execute(content: str, enrich: bool = False) -> Dict[str, Any]:
    """
    Extract all CEPs from text content.
    
    Args:
        content: Text to search for CEP
        enrich: If True, fetch address data from ViaCEP (primary) and OpenCEP (fallback)
    
    Returns:
        Dictionary with found CEPs and optionally address data
    """
    # Pattern for Brazilian CEP: 12345-678 or 12345678
    cep_pattern = r'\b(\d{5})-?(\d{3})\b'
    matches = list(re.finditer(cep_pattern, content))
    
    if not matches:
        return {
            "found": False,
            "cep": None,
            "ceps": [],
            "count": 0,
            "message": "Nenhum CEP encontrado no texto"
        }
    
    # Deduplicate CEPs while preserving order
    seen = set()
    ceps = []
    for match in matches:
        cep_raw = match.group(1) + match.group(2)
        if cep_raw not in seen:
            seen.add(cep_raw)
            cep_formatted = f"{match.group(1)}-{match.group(2)}"
            cep_entry = {
                "cep": cep_raw,
                "cep_formatted": cep_formatted
            }
            
            if enrich:
                address = _enrich_cep(cep_raw)
                cep_entry["address"] = address
                cep_entry["enriched"] = address is not None
            
            ceps.append(cep_entry)
    
    # Backward compatibility: primary CEP in top-level fields
    result = {
        "found": True,
        "cep": ceps[0]["cep"],
        "cep_formatted": ceps[0]["cep_formatted"],
        "count": len(ceps),
        "ceps": ceps
    }
    
    # If enriched, also put first address at top level for compatibility
    if enrich and ceps[0].get("address"):
        result["address"] = ceps[0]["address"]
    
    return result


def _enrich_cep(cep: str) -> Optional[Dict[str, Any]]:
    """
    Enrich a CEP with address data.
    Tries ViaCEP first, falls back to OpenCEP.
    
    Args:
        cep: 8-digit CEP string (no hyphen)
    
    Returns:
        Address dictionary or None if enrichment failed
    """
    # Try ViaCEP first
    address = _fetch_viacep(cep)
    if address:
        return address
    
    # Fallback to OpenCEP
    address = _fetch_opencep(cep)
    if address:
        return address
    
    return None


def _fetch_viacep(cep: str) -> Optional[Dict[str, Any]]:
    """Fetch address from ViaCEP API."""
    try:
        response = requests.get(
            f"https://viacep.com.br/ws/{cep}/json/",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if not data.get("erro"):
                return {
                    "logradouro": data.get("logradouro") or None,
                    "complemento": data.get("complemento") or None,
                    "bairro": data.get("bairro") or None,
                    "cidade": data.get("localidade") or None,
                    "estado": data.get("uf") or None,
                    "pais": "Brasil",
                    "ibge": data.get("ibge") or None,
                    "ddd": data.get("ddd") or None,
                    "fonte": "viacep"
                }
    except Exception:
        pass
    
    return None


def _fetch_opencep(cep: str) -> Optional[Dict[str, Any]]:
    """Fetch address from OpenCEP API (fallback)."""
    try:
        response = requests.get(
            f"https://opencep.com/v1/{cep}",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if not data.get("erro"):
                return {
                    "logradouro": data.get("logradouro") or None,
                    "complemento": data.get("complemento") or None,
                    "bairro": data.get("bairro") or None,
                    "cidade": data.get("localidade") or None,
                    "estado": data.get("uf") or None,
                    "pais": "Brasil",
                    "ibge": data.get("ibge") or None,
                    "ddd": data.get("ddd") or None,
                    "fonte": "opencep"
                }
    except Exception:
        pass
    
    return None
