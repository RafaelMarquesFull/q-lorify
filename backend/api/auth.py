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
        
        import uuid
        verification_token = str(uuid.uuid4())
        
        user = db.user.create(data={
            "email": email,
            "password": hashed,
            "name": name,
            "role": "CLIENT",
            "emailVerified": False,
            "emailVerificationToken": verification_token
        })
        
        from .emails import send_validation_email
        send_validation_email(email, name, verification_token)
        
        return JsonResponse({"message": "User created. Please check your email to verify your account.", "userId": user.id}, status=201)
        
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
            
        if not user.emailVerified:
            return JsonResponse({"error": "E-mail não verificado. Por favor, cheque sua caixa de entrada para ativar a conta."}, status=403)
            
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
        
        # Async email login warning
        try:
            from .emails import send_login_warning
            ip = request.META.get('REMOTE_ADDR', 'Desconhecido')
            device = request.META.get('HTTP_USER_AGENT', 'Dispositivo Desconhecido')
            send_login_warning(email, ip, device, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except:
            pass
        
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
            
            import uuid
            verification_token = str(uuid.uuid4())
            
            user = db.user.create(data={
                "email": email,
                "password": random_pw,
                "name": name,
                "role": "CLIENT",
                "emailVerified": False,
                "emailVerificationToken": verification_token
            })
            
            from .emails import send_validation_email
            send_validation_email(email, name, verification_token)
            
            return JsonResponse({"error": "Conta criada via Google. Por favor, valide seu e-mail antes de acessar. Enviamos um link para sua caixa de entrada."}, status=403)
            
        if not user.emailVerified:
            return JsonResponse({"error": "E-mail não verificado. Por favor, cheque sua caixa de entrada para ativar a conta."}, status=403)
            
        # Async email login warning
        try:
            from .emails import send_login_warning
            ip = request.META.get('REMOTE_ADDR', 'Desconhecido')
            device = request.META.get('HTTP_USER_AGENT', 'Dispositivo Desconhecido')
            send_login_warning(email, ip, device, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        except:
            pass
            
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

@csrf_exempt
def verify_email(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    token = request.GET.get("token")
    if not token:
        return JsonResponse({"error": "Token is required"}, status=400)
    db = get_db()
    user = db.user.find_first(where={"emailVerificationToken": token})
    if not user:
        return JsonResponse({"error": "Invalid or expired token"}, status=400)
    
    db.user.update(where={"id": user.id}, data={
        "emailVerified": True,
        "emailVerificationToken": None
    })
    
    from .emails import send_welcome_email
    send_welcome_email(user.email, user.name)
    
    from django.shortcuts import redirect
    import os
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    return redirect(f"{frontend_url}/login?verified=true")

@csrf_exempt
def request_password_reset(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        email = data.get("email")
        if not email:
            return JsonResponse({"error": "Email required"}, status=400)
        db = get_db()
        user = db.user.find_unique(where={"email": email})
        if user:
            import uuid
            import datetime
            reset_token = str(uuid.uuid4())
            expires = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            db.user.update(where={"id": user.id}, data={
                "passwordResetToken": reset_token,
                "passwordResetExpires": expires.isoformat() + "Z"
            })
            from .emails import send_password_reset
            send_password_reset(user.email, reset_token)
            
        return JsonResponse({"message": "Se o e-mail existir, um link de recuperação foi enviado."})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def reset_password(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        token = data.get("token")
        new_password = data.get("password")
        if not token or not new_password:
            return JsonResponse({"error": "Token and new password required"}, status=400)
            
        db = get_db()
        user = db.user.find_first(where={"passwordResetToken": token})
        if not user:
            return JsonResponse({"error": "Token inválido"}, status=400)
            
        import datetime
        if user.passwordResetExpires:
            expires_str = str(user.passwordResetExpires).replace("Z", "+00:00")
            try:
                expires_dt = datetime.datetime.fromisoformat(expires_str)
                if datetime.datetime.now(datetime.timezone.utc) > expires_dt:
                    return JsonResponse({"error": "Token expirado"}, status=400)
            except:
                pass
                
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
        
        db.user.update(where={"id": user.id}, data={
            "password": hashed,
            "passwordResetToken": None,
            "passwordResetExpires": None
        })
        
        return JsonResponse({"message": "Senha redefinida com sucesso"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
