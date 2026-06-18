import jwt
from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from asgiref.sync import iscoroutinefunction, sync_to_async
from .utils import get_db

SECRET_KEY = settings.SECRET_KEY

def _auth_logic_sync(request):
    """
    Synchronous logic to validate authentication.
    Returns (error_response, success_bool)
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return JsonResponse({'error': 'Unauthorized: Missing or invalid token'}, status=401), False
    
    token = auth_header.split(' ')[1]
    db = get_db()
    
    # Check if it's a user API key (sk-agent-* format)
    if token.startswith('sk-agent-'):
        api_key = db.apikey.find_first(where={"key": token, "active": True})
        
        if not api_key:
            return JsonResponse({'error': 'Unauthorized: Invalid or inactive API key'}, status=401), False
        
        # Get the user associated with this key
        user = db.user.find_unique(where={'id': api_key.userId})
        
        if not user:
            return JsonResponse({'error': 'Unauthorized: User not found'}, status=401), False
        
        # Attach user to request
        request.user = user
        request.auth_method = 'api_key'
        return None, True
        
    # Check if it's an Orchestrator Client token (sk-test-* or sk-client-*)
    if token.startswith('sk-'):
        client = db.orchclient.find_first(where={
            "token": token,
            "enabled": True
        })
        
        if client:
            # Mock a user-like object or attach client
            request.user = client
            request.client = client
            request.auth_method = 'orch_client'
            return None, True
    
    # Otherwise, treat as JWT token
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('id')
        
        user = db.user.find_unique(where={'id': user_id})
        
        if not user:
            return JsonResponse({'error': 'Unauthorized: User not found'}, status=401), False
        
        # Attach user to request
        request.user = user
        request.auth_method = 'jwt'
        return None, True
        
    except jwt.ExpiredSignatureError:
        return JsonResponse({'error': 'Unauthorized: Token expired'}, status=401), False
    except jwt.InvalidTokenError:
        return JsonResponse({'error': 'Unauthorized: Invalid token'}, status=401), False

def login_required(view_func):
    """
    Authentication decorator that supports both sync and async views.
    """
    is_async = iscoroutinefunction(view_func)
    
    if is_async:
        @wraps(view_func)
        async def async_wrapper(request, *args, **kwargs):
            # Run auth logic in a sync_to_async wrapper to prevent blocking event loop
            err_resp, success = await sync_to_async(_auth_logic_sync)(request)
            if not success:
                return err_resp
            return await view_func(request, *args, **kwargs)
        return async_wrapper
    else:
        @wraps(view_func)
        def sync_wrapper(request, *args, **kwargs):
            err_resp, success = _auth_logic_sync(request)
            if not success:
                return err_resp
            return view_func(request, *args, **kwargs)
        return sync_wrapper

def admin_required(view_func):
    is_async = iscoroutinefunction(view_func)
    
    if is_async:
        @wraps(view_func)
        async def async_wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user'):
                 return JsonResponse({'error': 'Unauthorized: User not authenticated'}, status=401)
            
            if getattr(request.user, 'role', None) != 'ADMIN':
                 return JsonResponse({'error': 'Forbidden: Admin access required'}, status=403)
                 
            return await view_func(request, *args, **kwargs)
        return async_wrapper
    else:
        @wraps(view_func)
        def sync_wrapper(request, *args, **kwargs):
            if not hasattr(request, 'user'):
                 return JsonResponse({'error': 'Unauthorized: User not authenticated'}, status=401)
            
            if getattr(request.user, 'role', None) != 'ADMIN':
                 return JsonResponse({'error': 'Forbidden: Admin access required'}, status=403)
                 
            return view_func(request, *args, **kwargs)
        return sync_wrapper
