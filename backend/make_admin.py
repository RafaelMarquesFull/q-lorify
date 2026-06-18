from prisma import Prisma
from api.utils import get_db

db = get_db()

def make_admin(email):
    user = db.user.find_unique(where={"email": email})
    if user:
        db.user.update(where={"email": email}, data={"role": "ADMIN"})
        print(f"User {email} is now ADMIN")
    else:
        print("User not found")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        make_admin(sys.argv[1])
    else:
        print("Usage: python3 make_admin.py <email>")
