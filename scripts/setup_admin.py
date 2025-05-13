import os
import sys
from app.database import SessionLocal, AccountModel, hash_password, init_db


def main():
    username = os.environ.get("APP_USERNAME")
    password = os.environ.get("APP_PASSWORD")
    if not username or not password:
        print("APP_USERNAME and APP_PASSWORD must be set in the environment.")
        sys.exit(1)

    init_db()  # Ensure tables exist
    db = SessionLocal()
    try:
        admin = db.query(AccountModel).filter(AccountModel.username == username).first()
        if admin:
            print(f"Admin user '{username}' already exists.")
        else:
            admin = AccountModel(
                username=username,
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"Created admin user: {username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
