#!/usr/bin/env python3
"""
Seed script for OrchFunction using SQLite directly.
Populates OrchFunction with default built-in functions.
"""

import sqlite3
import uuid
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'dev.db')

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
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    created = 0
    skipped = 0
    
    try:
        for func in BUILTIN_FUNCTIONS:
            # Check if function already exists
            cursor.execute(
                "SELECT id FROM OrchFunction WHERE name = ?",
                (func["name"],)
            )
            existing = cursor.fetchone()
            
            if existing:
                print(f"  ⏭️  {func['displayName']} already exists, skipping")
                skipped += 1
            else:
                # Insert new function
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO OrchFunction 
                    (id, name, displayName, description, enabled, pricePerUnit, 
                     unitSize, requiresAi, timeout, createdAt, updatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(uuid.uuid4()),
                    func["name"],
                    func["displayName"],
                    func["description"],
                    1,  # enabled
                    func["pricePerUnit"],
                    func["unitSize"],
                    1 if func["requiresAi"] else 0,
                    30000,  # timeout
                    now,
                    now
                ))
                print(f"  ✅ Created {func['displayName']}")
                created += 1
        
        conn.commit()
        print(f"\n✨ Functions seeding complete!")
        print(f"   Created: {created}, Skipped: {skipped}")
        
        # Show summary
        cursor.execute("SELECT name, displayName, enabled FROM OrchFunction ORDER BY name")
        all_functions = cursor.fetchall()
        print(f"\n📊 Total functions in database: {len(all_functions)}")
        for name, display_name, enabled in all_functions:
            status = "✅" if enabled else "❌"
            print(f"  {status} {display_name} ({name})")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    seed_functions()
