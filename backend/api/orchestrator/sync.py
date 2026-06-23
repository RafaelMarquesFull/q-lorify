"""
Function Sync Service.
Auto-syncs built-in functions with the database.
"""
import os
import uuid
from datetime import datetime
from typing import List, Dict
from ..utils import get_db


# Built-in function definitions
BUILTIN_FUNCTIONS = {
    "extract_cep": {
        "displayName": "Extrator de CEP",
        "description": "Extrai CEPs brasileiros do texto e opcionalmente enriquece com dados de endereço via ViaCEP",
        "cost": "low",
        "requiresAi": False,
    },
    "extract_emails": {
        "displayName": "Extrator de E-mails",
        "description": "Extrai endereços de e-mail do texto",
        "cost": "low",
        "requiresAi": False,
    },
    "extract_phones": {
        "displayName": "Extrator de Telefones",
        "description": "Extrai números de telefone brasileiros do texto",
        "cost": "low",
        "requiresAi": False,
    },
    "extract_cpfcnpj": {
        "displayName": "Extrator de CPF/CNPJ",
        "description": "Extrai e valida CPFs e CNPJs do texto",
        "cost": "low",
        "requiresAi": False,
    },
    "extract_endereco": {
        "displayName": "Extrator de Endereços",
        "description": "Extrai endereços brasileiros do texto com parsing de componentes",
        "cost": "low",
        "requiresAi": False,
    },
    "normalize_text": {
        "displayName": "Normalizador de Texto",
        "description": "Limpa e normaliza texto (remove acentos, espaços extras, etc)",
        "cost": "low",
        "requiresAi": False,
    },
    "convert_units": {
        "displayName": "Conversor de Dimensões",
        "description": "Detecta medidas em texto (mm, cm, m, km, polegadas, frações, diâmetro) e converte para unidade alvo",
        "cost": "low",
        "requiresAi": False,
    },
    "convert_mass": {
        "displayName": "Conversor de Massa",
        "description": "Detecta medidas de massa em texto (toneladas, quilos, gramas, libras, onças, arrobas) e converte para unidade alvo com valor por extenso",
        "cost": "low",
        "requiresAi": False,
    },
}


def sync_builtin_functions():
    """
    Sync built-in functions with the database.
    Creates new functions if they don't exist, doesn't override existing ones.
    """
    db = get_db()
    
    for name, config in BUILTIN_FUNCTIONS.items():
        try:
            # Check if function exists
            existing = db.orchfunction.find_first(
                where={"name": name}
            )
            
            if not existing:
                # Create new function
                func_id = str(uuid.uuid4())
                db.orchfunction.create(
                    data={
                        "id": func_id,
                        "name": name,
                        "displayName": config["displayName"],
                        "description": config["description"],
                        "enabled": True,
                        "pricePerUnit": 0.0,
                        "unitSize": 1000,
                        "requiresAi": bool(config["requiresAi"]),
                        "timeout": 30000
                    }
                )
                print(f"[FunctionSync] ✅ Created built-in function: {name}")
            else:
                print(f"[FunctionSync] Function already exists: {name}")
                
        except Exception as e:
            print(f"[FunctionSync] Error syncing {name}: {e}")


def get_available_functions() -> List[str]:
    """Get list of available function names from the functions directory."""
    functions_dir = os.path.join(os.path.dirname(__file__), 'functions')
    
    functions = []
    if os.path.exists(functions_dir):
        for filename in os.listdir(functions_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                functions.append(filename[:-3])
    
    return functions


def get_function_metadata(name: str) -> Dict:
    """Get metadata for a built-in function."""
    return BUILTIN_FUNCTIONS.get(name, {
        "displayName": name.replace("_", " ").title(),
        "description": "",
        "cost": "low",
        "requiresAi": False,
    })
