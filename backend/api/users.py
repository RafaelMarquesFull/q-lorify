from django.http import JsonResponse
from django.db.models import F
from django.views.decorators.csrf import csrf_exempt
from .decorators import login_required
from .utils import get_db

@csrf_exempt
@login_required
def me(request):
    """Return current user profile"""
    user = request.user
    db = get_db()
    
    # Refresh user to get relations if needed, or query separate
    # But request.user is just the object from find_unique in decorator without includes unless we changed it.
    # The decorator implementation: user = db.user.find_unique(where={'id': user_id}) 
    # It does NOT include subscription.
    
    # We need to fetch subscription
    sub = db.subscription.find_unique(where={"userId": user.id})
    
    return JsonResponse({
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "createdAt": user.createdAt,
        "subscription": {
            "status": sub.status if sub else "inactive",
            "plan": sub.plan if sub else "free"
        }
    })

@csrf_exempt
@login_required
def update_me(request):
    """Update current user profile"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
        
    try:
        import json
        from .auth import hash_password
        
        data = json.loads(request.body)
        user = request.user
        db = get_db()
        
        updates = {}
        
        # specific fields allowed to update
        if "name" in data and data["name"]:
            updates["name"] = data["name"]
            
        if "password" in data and data["password"]:
            # Basic length check
            if len(data["password"]) < 6:
                return JsonResponse({"error": "Password must be at least 6 characters"}, status=400)
            updates["password"] = hash_password(data["password"])
            
        if not updates:
            return JsonResponse({"error": "No valid fields to update"}, status=400)
            
        updated_user = db.user.update(
            where={"id": user.id},
            data=updates
        )
        
        return JsonResponse({
            "message": "Profile updated successfully",
            "user": {
                "id": updated_user.id,
                "name": updated_user.name,
                "email": updated_user.email
            }
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
