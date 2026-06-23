#!/usr/bin/env python3
"""
Seed script for OrchFunction using SQLite directly.
Populates OrchFunction with default built-in functions.
"""

import uuid
from datetime import datetime
from prisma import Prisma

# Built-in function definitions to seed
BUILTIN_FUNCTIONS = [
    {
        "name": "extract_cep",
        "displayName": "Extrator de CEP",
        "description": "Extrai CEPs brasileiros do texto e opcionalmente enriquece com dados de endereço via ViaCEP",
        "pricePerUnit": 0.0,
        "unitSize": 1000,
        "requiresAi": False,
    },
    {
        "name": "extract_emails",
        "displayName": "Extrator de E-mails",
        "description": "Extrai endereços de e-mail do texto",
        "pricePerUnit": 0.0,
        "unitSize": 1000,
        "requiresAi": False,
    },
    {
        "name": "extract_phones",
        "displayName": "Extrator de Telefones",
        "description": "Extrai números de telefone brasileiros do texto",
        "pricePerUnit": 0.0,
        "unitSize": 1000,
        "requiresAi": False,
    },
    {
        "name": "extract_cpfcnpj",
        "displayName": "Extrator de CPF/CNPJ",
        "description": "Extrai e valida CPFs e CNPJs do texto",
        "pricePerUnit": 0.0,
        "unitSize": 1000,
        "requiresAi": False,
    },
    {
        "name": "extract_endereco",
        "displayName": "Extrator de Endereços",
        "description": "Extrai endereços brasileiros do texto com parsing de componentes",
        "pricePerUnit": 0.0,
        "unitSize": 1000,
        "requiresAi": False,
    },
    {
        "name": "normalize_text",
        "displayName": "Normalizador de Texto",
        "description": "Limpa e normaliza texto (remove acentos, espaços extras, etc)",
        "pricePerUnit": 0.0,
        "unitSize": 1000,
        "requiresAi": False,
    },
    {
        "name": "convert_units",
        "displayName": "Conversor de Dimensões",
        "description": "Detecta medidas em texto (mm, cm, m, km, polegadas, frações, diâmetro) e converte para unidade alvo",
        "pricePerUnit": 0.0,
        "unitSize": 1000,
        "requiresAi": False,
    },
    {
        "name": "convert_mass",
        "displayName": "Conversor de Massa",
        "description": "Detecta medidas de massa em texto (toneladas, quilos, gramas, libras, onças, arrobas) e converte para unidade alvo com valor por extenso",
        "pricePerUnit": 0.0,
        "unitSize": 1000,
        "requiresAi": False,
    },
]


def seed_functions():
    """Seed built-in functions into database."""
    print("🌱 Starting functions seeding...")
    
    db = Prisma()
    db.connect()
    
    created = 0
    skipped = 0
    
    try:
        for func in BUILTIN_FUNCTIONS:
            existing = db.orchfunction.find_unique(where={"name": func["name"]})
            
            if existing:
                print(f"  ⏭️  {func['displayName']} already exists, skipping")
                skipped += 1
            else:
                db.orchfunction.create(
                    data={
                        "name": func["name"],
                        "displayName": func["displayName"],
                        "description": func["description"],
                        "enabled": True,
                        "pricePerUnit": func["pricePerUnit"],
                        "unitSize": func["unitSize"],
                        "requiresAi": func["requiresAi"],
                        "timeout": 30000
                    }
                )
                print(f"  ✅ Created {func['displayName']}")
                created += 1
        
        print(f"\n✨ Functions seeding complete!")
        print(f"   Created: {created}, Skipped: {skipped}")
        
        all_functions = db.orchfunction.find_many(order={"name": "asc"})
        print(f"\n📊 Total functions in database: {len(all_functions)}")
        for f in all_functions:
            status = "✅" if f.enabled else "❌"
            print(f"  {status} {f.displayName} ({f.name})")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        raise
    finally:
        db.disconnect()


if __name__ == "__main__":
    seed_functions()
