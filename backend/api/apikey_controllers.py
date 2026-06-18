import secrets
import json
import uuid
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .decorators import login_required
from .utils import get_db

@csrf_exempt
@login_required
def list_create_keys(request):
    db = get_db()
    
    if request.method == "GET":
        # Use ORM to fetch keys (it works for reading existing fields)
        keys = db.apikey.find_many(
            where={
                "userId": request.user.id,
                "active": True
            },
            order={"createdAt": "desc"}
        )
        
        # Now read names separately via raw SQL since Prisma client doesn't know about it
        key_ids = [k.id for k in keys]
        if key_ids:
            placeholders = ','.join(['?' for _ in key_ids])
            raw_query = f'SELECT id, name FROM ApiKey WHERE id IN ({placeholders})'
            name_results = db.query_raw(raw_query, *key_ids)
            # Build a dict of id -> name
            name_map = {}
            for row in name_results:
                if isinstance(row, dict):
                    name_map[row.get('id')] = row.get('name')
                else:
                    # If it's an object
                    name_map[getattr(row, 'id', None)] = getattr(row, 'name', None)
        else:
            name_map = {}
        
        data = []
        for k in keys:
            # Mask the key for display
            masked = f"{k.key[:6]}...{k.key[-4:]}"
            
            # Get name from our raw query results
            key_name = name_map.get(k.id) or "Chave Secreta"
            
            data.append({
                "id": k.id,
                "key": masked,
                "name": key_name,
                "createdAt": k.createdAt.isoformat() if hasattr(k.createdAt, 'isoformat') else str(k.createdAt)
            })
            
        return JsonResponse(data, safe=False)

    elif request.method == "POST":
        # Check Balance
        user = db.user.find_unique(where={"id": request.user.id})
        
        if not user or user.balance <= 0:
             return JsonResponse({"error": "Saldo insuficiente. Por favor, adicione fundos para criar uma nova Chave de API."}, status=403)

        try:
            body = json.loads(request.body)
            name = body.get("name", "Chave Secreta")
        except:
            name = "Chave Secreta"

        # Generate a secure random key
        random_part = secrets.token_urlsafe(32)
        new_key = f"sk-agent-{random_part}"
        new_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Create key using ORM (without name since client doesn't support it)
        try:
            key_obj = db.apikey.create(data={
                "id": new_id,
                "user": {"connect": {"id": request.user.id}},
                "key": new_key,
                "active": True
            })
            
            # Now update the name using raw SQL
            db.execute_raw('UPDATE ApiKey SET name = ? WHERE id = ?', name, new_id)
            
        except Exception as e:
            print(f"Create key error: {e}")
            return JsonResponse({"error": f"Erro ao criar chave: {str(e)}"}, status=500)
        
        # Return the FULL key only once here
        return JsonResponse({
            "id": key_obj.id,
            "key": new_key,
            "name": name,
            "createdAt": key_obj.createdAt.isoformat() if hasattr(key_obj.createdAt, 'isoformat') else str(key_obj.createdAt)
        })

    return JsonResponse({"error": "Método não permitido"}, status=405)

@csrf_exempt
@login_required
def revoke_key(request, key_id):
    if request.method != "DELETE":
         return JsonResponse({"error": "Método não permitido"}, status=405)
         
    db = get_db()
    
    # Ensure the key belongs to the user
    key = db.apikey.find_first(where={
        "id": key_id,
        "userId": request.user.id
    })
    
    if not key:
        return JsonResponse({"error": "Chave não encontrada"}, status=404)
        
    db.apikey.delete(where={"id": key_id})
    
    return JsonResponse({"message": "Chave revogada"})
