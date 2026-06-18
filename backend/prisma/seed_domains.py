#!/usr/bin/env python3
"""
Seed script for domain templates using SQLite directly.
Populates DomainConfig with default domain templates.
"""

import sqlite3
import json
import uuid
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'dev.db')

DOMAIN_TEMPLATES = [
    {
        "domain": "transport",
        "name": "Transporte & Logística",
        "icon": "🚚",
        "description": "Cotações, rastreio, entregas e documentos fiscais",
        "defaultCategories": json.dumps([
            "cotação", "rastreio", "boleto", "coleta", 
            "cte", "nfe", "atendente", "finalizar"
        ]),
        "systemPrompt": """Você é um assistente especializado em LOGÍSTICA e TRANSPORTE.

Contexto: O usuário é um cliente de transportadora que precisa de:
- Cotações de frete
- Rastreamento de cargas  
- Emissão de documentos (CT-e, NF-e, boletos)
- Agendamento de coletas

Vocabulário específico:
- "frete", "envio", "despacho" → cotação
- "tracking", "onde está", "localizar" → rastreio
- "segunda via", "pagar" → boleto
- "buscar mercadoria", "retirar" → coleta

Seja objetivo e focado em logistics operations.""",
        "isDefault": 1
    },
    {
        "domain": "health",
        "name": "Saúde & Medicina",
        "icon": "🏥",
        "description": "Consultas, exames, receitas e emergências",
        "defaultCategories": json.dumps([
            "consulta", "exame", "receita", "agendamento",
            "resultado", "emergencia", "atendimento"
        ]),
        "systemPrompt": """Você é um assistente de ATENDIMENTO MÉDICO e SAÚDE.

Contexto: O usuário é um paciente que precisa de:
- Agendar consultas médicas
- Solicitar exames
- Pegar receitas/prescrições
- Consultar resultados

Vocabulário específico:
- "médico", "doutor", "dr" → consulta
- "análise", "laboratório", "sangue" → exame
- "remédio", "prescrição", "medicamento" → receita

Priorize empatia em contextos de saúde.""",
        "isDefault": 0
    },
    {
        "domain": "food",
        "name": "Alimentação & Delivery",
        "icon": "🍔",
        "description": "Pedidos, cardápio e entregas de restaurante",
        "defaultCategories": json.dumps([
            "cardápio", "pedido", "entrega", "reserva",
            "cancelamento", "pagamento", "reclamacao"
        ]),
        "systemPrompt": """Você é um assistente de RESTAURANTE e DELIVERY.

Contexto: O usuário quer:
- Ver o cardápio/menu
- Fazer pedidos
- Acompanhar entrega
- Fazer reservas

Vocabulário específico:
- "menu", "prato", "comida" → cardápio
- "pedir", "quero", "vou querer" → pedido
- "delivery", "entregar", "trazer" → entrega

Tom amigável e informal.""",
        "isDefault": 0
    },
    {
        "domain": "ecommerce",
        "name": "E-commerce & Varejo",
        "icon": "🏪",
        "description": "Produtos, estoque, compras e devoluções",
        "defaultCategories": json.dumps([
            "produto", "estoque", "compra", "pagamento",
            "entrega", "devolucao", "rastreio", "suporte"
        ]),
        "systemPrompt": """Você é um assistente de E-COMMERCE.

Contexto: Cliente quer:
- Consultar produtos
- Fazer compras
- Acompanhar pedidos
- Resolver problemas

Vocabulário específico:
- "buscar", "mostrar", "ver" → produto
- "disponível", "tem" → estoque
- "carrinho", "finalizar" → compra""",
        "isDefault": 0
    },
    {
        "domain": "automotive",
        "name": "Automotivo & Veículos",
        "icon": "🚗",
        "description": "Manutenção, peças e serviços automotivos",
        "defaultCategories": json.dumps([
            "revisao", "pecas", "agendamento", "orcamento",
            "garantia", "vistoria", "documentacao"
        ]),
        "systemPrompt": """Você é um assistente AUTOMOTIVO.

Contexto: Cliente precisa de:
- Agendar revisões
- Comprar peças
- Orçamentos
- Documentação

Vocabulário técnico necessário.""",
        "isDefault": 0
    }
]

def seed_domains():
    """Seed domain templates into database."""
    print("🌱 Starting domain seeding...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        for template in DOMAIN_TEMPLATES:
            # Check if domain already exists
            cursor.execute(
                "SELECT id FROM DomainConfig WHERE domain = ?",
                (template["domain"],)
            )
            existing = cursor.fetchone()
            
            if existing:
                print(f"  ⏭️  {template['name']} already exists, skipping")
            else:
                # Insert new domain
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO DomainConfig 
                    (id, domain, name, description, icon, defaultCategories, 
                     systemPrompt, matchingRules, isActive, isDefault, 
                     createdAt, updatedAt)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(uuid.uuid4()),
                    template["domain"],
                    template["name"],
                    template.get("description"),
                    template.get("icon"),
                    template["defaultCategories"],
                    template["systemPrompt"],
                    None,  # matchingRules
                    1,     # isActive
                    template["isDefault"],
                    now,
                    now
                ))
                print(f"  ✅ Created {template['name']}")
        
        conn.commit()
        print("\n✨ Domain seeding complete!")
        
        # Show summary
        cursor.execute("SELECT name, icon, isDefault FROM DomainConfig")
        all_domains = cursor.fetchall()
        print(f"\n📊 Total domains in database: {len(all_domains)}")
        for name, icon, is_default in all_domains:
            default_marker = " (default)" if is_default else ""
            print(f"  {icon} {name}{default_marker}")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    seed_domains()
