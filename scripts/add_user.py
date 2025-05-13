import sys
from getpass import getpass
from app.database import SessionLocal, AccountModel, hash_password, init_db

def main():
    username = input("Enter new username: ").strip()
    if not username:
        print("Username cannot be empty.")
        sys.exit(1)
    password = getpass("Enter password: ")
    if not password:
        print("Password cannot be empty.")
        sys.exit(1)
    email = input("Enter email (optional): ").strip() or None

    init_db()  # Ensure tables exist
    db = SessionLocal()
    try:
        user = db.query(AccountModel).filter(AccountModel.username == username).first()
        if user:
            print(f"User '{username}' already exists.")
        else:
            user = AccountModel(
                username=username,
                password_hash=hash_password(password),
                email=email,
                is_active=True,
            )
            db.add(user)
            db.commit()
            print(f"Created user: {username}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
