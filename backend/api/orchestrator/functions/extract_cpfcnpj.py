"""
Extract CPF/CNPJ Function
Extracts Brazilian CPF and CNPJ numbers from text.
Only returns valid CPF/CNPJ numbers. Returns "ausente" for invalid/missing values.
Optionally enriches CNPJ with company data from OpenCNPJ (never enriches CPF).
"""
import re
from typing import Dict, Any, List, Optional


def execute(content: str, validate: bool = True, enrich: bool = False) -> Dict[str, Any]:
    """
    Extract CPF and CNPJ from text content.
    
    Args:
        content: Text to search for CPF/CNPJ
        validate: If True, validate the extracted numbers
        enrich: If True, enrich CNPJs with company data from OpenCNPJ (never CPFs)
    
    Returns:
        Dictionary with found CPF and CNPJ numbers.
        Invalid or missing values are marked as "ausente".
    """
    # Quick check: if content is too short or looks like a CEP, reject early
    clean = re.sub(r'[.\-/\s]', '', content.strip())
    
    # CEP detection: 8 digits, starts with valid CEP ranges
    if re.fullmatch(r'\d{8}', clean) and not re.fullmatch(r'\d{11}', clean) and not re.fullmatch(r'\d{14}', clean):
        return {
            "found": False,
            "count": 0,
            "cpfs": [],
            "cnpjs": [],
            "all": [],
            "status": "ausente",
            "message": "Valor parece ser um CEP, não um CPF/CNPJ"
        }
    
    results = []
    
    # CNPJ patterns: 12.345.678/0001-00 or 12345678000100
    cnpj_pattern = r'\b(\d{2})[.\s]?(\d{3})[.\s]?(\d{3})[/\s]?(\d{4})[-.\s]?(\d{2})\b'
    
    # Find CNPJs first (longer pattern)
    for match in re.finditer(cnpj_pattern, content):
        raw = ''.join(match.groups())
        formatted = f"{match.group(1)}.{match.group(2)}.{match.group(3)}/{match.group(4)}-{match.group(5)}"
        
        is_valid = validate_cnpj(raw) if validate else True
        
        # Only include valid CNPJs
        if not is_valid:
            continue
        
        # Extract surrounding text context for role identification
        ctx_start = max(0, match.start() - 80)
        ctx_end = min(len(content), match.end() + 20)
        context_text = content[ctx_start:match.start()].strip()
        
        cnpj_entry = {
            "type": "cnpj",
            "raw": raw,
            "formatted": formatted,
            "valid": True,
            "position": match.start(),
            "context": context_text
        }
        
        # Enrich CNPJ with company data (never CPF)
        if enrich:
            company_data = _enrich_cnpj(raw)
            cnpj_entry["company_data"] = company_data
            cnpj_entry["enriched"] = company_data is not None
        
        results.append(cnpj_entry)
    
    # CPF patterns: 123.456.789-00 or 12345678900
    cpf_pattern = r'\b(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})[-.\s]?(\d{2})\b'
    
    # Find CPFs (never enriched)
    for match in re.finditer(cpf_pattern, content):
        raw = ''.join(match.groups())
        
        # Skip if this is part of a CNPJ (already extracted)
        is_part_of_cnpj = any(
            r["type"] == "cnpj" and raw in r["raw"]
            for r in results
        )
        if is_part_of_cnpj:
            continue
        
        # Skip if this looks like a CEP (8 digits captured as 11 with overlap)
        if len(raw) != 11:
            continue
        
        is_valid = validate_cpf(raw) if validate else True
        
        # Only include valid CPFs
        if not is_valid:
            continue
        
        formatted = f"{match.group(1)}.{match.group(2)}.{match.group(3)}-{match.group(4)}"
        
        results.append({
            "type": "cpf",
            "raw": raw,
            "formatted": formatted,
            "valid": True,
            "position": match.start()
        })
    
    # Sort by position
    results.sort(key=lambda x: x["position"])
    
    cpfs = [r for r in results if r["type"] == "cpf"]
    cnpjs = [r for r in results if r["type"] == "cnpj"]
    
    if not results:
        return {
            "found": False,
            "count": 0,
            "cpfs": [],
            "cnpjs": [],
            "all": [],
            "status": "ausente",
            "message": "Nenhum CPF/CNPJ válido encontrado"
        }
    
    result = {
        "found": True,
        "count": len(results),
        "cpfs": cpfs,
        "cnpjs": cnpjs,
        "all": results,
        "status": "encontrado"
    }
    
    # Flatten enrichment for compatibility/AI visibility
    if cnpjs and len(cnpjs) > 0 and cnpjs[0].get("company_data"):
        result["company_data"] = cnpjs[0]["company_data"]
        result["enriched"] = True
        
    return result


def _enrich_cnpj(cnpj: str) -> Optional[Dict[str, Any]]:
    """
    Enrich a CNPJ with company data from OpenCNPJ API.
    Uses the open.cnpja.com API directly.
    
    Args:
        cnpj: 14-digit CNPJ string (no formatting)
    
    Returns:
        Company data dictionary or None if enrichment failed
    """
    import requests

    
    try:
        response = requests.get(
            f"https://open.cnpja.com/office/{cnpj}",
            timeout=10,
            headers={"Accept": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract company info
            company = data.get("company", {})
            address = data.get("address", {})
            status = data.get("status", {})
            main_activity = data.get("mainActivity", {})
            
            company_data = {
                "razao_social": company.get("name"),
                "nome_fantasia": data.get("alias") or None,
                "cnpj": data.get("taxId"),
                "situacao_cadastral": status.get("text"),
                "data_situacao_cadastral": data.get("statusDate"),
                "natureza_juridica": company.get("nature", {}).get("text") if isinstance(company.get("nature"), dict) else None,
                "porte": company.get("size", {}).get("text") if isinstance(company.get("size"), dict) else None,
                "data_abertura": data.get("founded"),
                "capital_social": company.get("equity"),
                "endereco": {
                    "logradouro": address.get("street"),
                    "numero": address.get("number"),
                    "complemento": address.get("details") or None,
                    "bairro": address.get("district"),
                    "municipio": address.get("city"),
                    "uf": address.get("state"),
                    "cep": address.get("zip"),
                },
                "atividade_principal": main_activity.get("text") if isinstance(main_activity, dict) else None,
                "atividade_principal_codigo": main_activity.get("id") if isinstance(main_activity, dict) else None,
                "fonte": "opencnpj"
            }
            
            # Extract phone and email if available
            phones = data.get("phones", [])
            if phones and len(phones) > 0:
                phone = phones[0]
                company_data["telefone"] = phone.get("number") if isinstance(phone, dict) else str(phone)
            
            emails = data.get("emails", [])
            if emails and len(emails) > 0:
                email = emails[0]
                company_data["email"] = email.get("address") if isinstance(email, dict) else str(email)
            
            # Clean None values from endereco
            company_data["endereco"] = {k: v for k, v in company_data["endereco"].items() if v}
            
            return company_data
            
            return company_data
            
    except Exception as e:
        print(f"[CNPJ Enrichment] Error enriching {cnpj}: {e}")
    
    return None


def validate_cpf(cpf: str) -> bool:
    """Validate CPF using check digits."""
    if len(cpf) != 11:
        return False
    
    # All same digits is invalid
    if cpf == cpf[0] * 11:
        return False
    
    # Calculate first check digit
    sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
    d1 = (sum1 * 10) % 11
    if d1 == 10:
        d1 = 0
    
    if d1 != int(cpf[9]):
        return False
    
    # Calculate second check digit
    sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
    d2 = (sum2 * 10) % 11
    if d2 == 10:
        d2 = 0
    
    return d2 == int(cpf[10])


def validate_cnpj(cnpj: str) -> bool:
    """Validate CNPJ using check digits."""
    if len(cnpj) != 14:
        return False
    
    # All same digits is invalid
    if cnpj == cnpj[0] * 14:
        return False
    
    # Weights for first check digit
    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum1 = sum(int(cnpj[i]) * w1[i] for i in range(12))
    d1 = sum1 % 11
    d1 = 0 if d1 < 2 else 11 - d1
    
    if d1 != int(cnpj[12]):
        return False
    
    # Weights for second check digit
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum2 = sum(int(cnpj[i]) * w2[i] for i in range(13))
    d2 = sum2 % 11
    d2 = 0 if d2 < 2 else 11 - d2
    
    return d2 == int(cnpj[13])
