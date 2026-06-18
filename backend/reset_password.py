import bcrypt
from api.utils import get_db

def reset_password(email, new_password):
    db = get_db()
    user = db.user.find_unique(where={"email": email})
    
    if not user:
        print(f"User {email} not found")
        return

    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
    
    db.user.update(
        where={"email": email},
        data={"password": hashed}
    )
    print(f"Password for {email} reset to: {new_password}")

if __name__ == "__main__":
    reset_password("admin@admin.com", "password123")
