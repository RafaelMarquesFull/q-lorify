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
        keys = db.apikey.find_many(
            where={
                "userId": request.user.id,
                "active": True
            },
            order={"createdAt": "desc"}
        )
        
        data = []
        for k in keys:
            # Mask the key for display
            masked = f"{k.key[:6]}...{k.key[-4:]}"
            
            data.append({
                "id": k.id,
                "key": masked,
                "name": k.name or "Chave Secreta",
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
        
        # Create key using ORM
        try:
            key_obj = db.apikey.create(data={
                "id": new_id,
                "user": {"connect": {"id": request.user.id}},
                "key": new_key,
                "name": name,
                "active": True
            })
            
        except Exception as e:
            print(f"Create key error: {e}")
            return JsonResponse({"error": f"Erro ao criar chave: {str(e)}"}, status=500)
        
        # Return the FULL key only once here
        return JsonResponse({
            "id": key_obj.id,
            "key": new_key,
            "name": key_obj.name,
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
