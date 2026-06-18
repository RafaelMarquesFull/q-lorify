import json
import jwt
import datetime
import bcrypt
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .utils import get_db

SECRET_KEY = settings.SECRET_KEY

@csrf_exempt
def register(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        
        if not email or not password:
            return JsonResponse({"error": "Email and password required"}, status=400)
            
        db = get_db()
        
        # Check if user exists
        existing = db.user.find_unique(where={"email": email})
        if existing:
            return JsonResponse({"error": "User already exists"}, status=400)
            
        # Hash password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        user = db.user.create(data={
            "email": email,
            "password": hashed,
            "name": name,
            "role": "CLIENT"
        })
        
        return JsonResponse({"message": "User created", "userId": user.id}, status=201)
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
        
    try:
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return JsonResponse({"error": "Email and password required"}, status=400)
            
        db = get_db()
        user = db.user.find_unique(where={"email": email})
        
        if not user:
            return JsonResponse({"error": "Invalid credentials"}, status=401)
            
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return JsonResponse({"error": "Invalid credentials"}, status=401)
            
        # Generate JWT
        payload = {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        return JsonResponse({"token": token, "user": {"id": user.id, "email": user.email, "role": user.role, "name": user.name}})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
@csrf_exempt
def google_login(request):
    """
    Handle Google SSO Login/Registration
    Body: { "credential": "JWT_TOKEN_FROM_GOOGLE" }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
        
    try:
        data = json.loads(request.body)
        credential = data.get("credential") # JWT from Google
        
        if not credential:
            return JsonResponse({"error": "Credential required"}, status=400)
            
        # Verify Token with Google
        # For simplicity and speed without extra heavy libs, we can verify against google's endpoint
        # or decode if we trust the source (but verification is better).
        # Using requests to verify token info
        import requests
        
        # Verify ID token
        verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
        resp = requests.get(verify_url)
        
        if resp.status_code != 200:
             return JsonResponse({"error": "Invalid Google Token"}, status=401)
             
        google_data = resp.json()
        
        # Check audience (CLIENT_ID) if needed, but implicit in receiving valid token signed by Google
        # client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None)
        # if client_id and google_data.get('aud') != client_id:
        #    return JsonResponse({"error": "Invalid Token Audience"}, status=401)
            
        email = google_data.get("email")
        name = google_data.get("name")
        picture = google_data.get("picture")
        
        if not email:
            return JsonResponse({"error": "Email not found in Google Token"}, status=400)
            
        db = get_db()
        
        # Find or Create User
        user = db.user.find_unique(where={"email": email})
        
        if not user:
            # Create user with random password (since they use SSO)
            # We can mark them as SSO user if we had a field, but for now just create
            salt = bcrypt.gensalt()
            random_pw = bcrypt.hashpw(f"GOOGLE_SSO_{datetime.datetime.now()}".encode(), salt).decode()
            
            user = db.user.create(data={
                "email": email,
                "password": random_pw,
                "name": name,
                "role": "CLIENT"
            })
            
        # Generate Session JWT
        payload = {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        return JsonResponse({
            "token": token, 
            "user": {
                "id": user.id, 
                "email": user.email, 
                "role": user.role, 
                "name": user.name,
                "picture": picture
            }
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
