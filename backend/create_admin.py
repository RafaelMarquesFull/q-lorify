
import os
import django
import bcrypt

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from prisma import Prisma

def create_admin():
    db = Prisma()
    db.connect()
    
    email = "admin@qlorify.ai"
    password = "admin123"
    
    # Check if exists
    existing = db.user.find_unique(where={"email": email})
    if existing:
        print(f"User {email} already exists.")
        if existing.role != "ADMIN":
            db.user.update(where={"id": existing.id}, data={"role": "ADMIN"})
            print("Promoted to ADMIN.")
        return

    # Create
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    db.user.create(data={
        "email": email,
        "password": hashed,
        "name": "Super Admin",
        "role": "ADMIN"
    })
    print(f"Created admin user: {email}")
    db.disconnect()

if __name__ == "__main__":
    create_admin()
