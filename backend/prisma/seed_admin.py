import bcrypt
from prisma import Prisma

def main() -> None:
    db = Prisma()
    db.connect()

    email = "administrador@qlorify.com"
    password = "37412518963Rafa@"
    
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    # Check if user exists
    existing_user = db.user.find_unique(where={"email": email})
    
    if existing_user:
        db.user.update(
            where={"email": email},
            data={
                "password": hashed_password,
                "role": "ADMIN",
                "emailVerified": True
            }
        )
        print(f"✅ Admin user {email} updated successfully!")
    else:
        db.user.create(
            data={
                "email": email,
                "password": hashed_password,
                "name": "Administrador",
                "role": "ADMIN",
                "emailVerified": True
            }
        )
        print(f"✅ Admin user {email} created successfully!")

    db.disconnect()

if __name__ == '__main__':
    main()
