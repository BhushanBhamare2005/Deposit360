import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models.user import User


def create_admin() -> None:
    create_tables()
    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()
    password = getpass.getpass("Admin password (minimum 12 characters): ")
    if len(password) < 12:
        raise SystemExit("Password must contain at least 12 characters.")

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("A user with that email already exists.")
        admin = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            roles=["admin"],
            is_active=True,
        )
        db.add(admin)
        db.commit()
    print("Admin account created.")


if __name__ == "__main__":
    create_admin()
