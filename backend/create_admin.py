
from database import SessionLocal
from main import password_hasher
from models import User

from getpass import getpass

db = SessionLocal()

try:
    name = input("Enter admin name: ").strip()
    email = input("Enter admin email: ").strip().lower()
    password = getpass("Enter admin password: ")
    confirm = getpass("Confirm admin password: ")

    if not name or not email or not password:
        raise ValueError("All fields are required.")

    if password != confirm:
        raise ValueError("Passwords do not match.")

    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise ValueError("This email already exists.")

    admin = User(
        full_name=name,
        email=email,
        password_hash=password_hasher.hash(password),
        role="admin",
        partner_id=None,
        is_active=1
    )

    db.add(admin)
    db.commit()

    print("\nAdmin account created successfully!")

except Exception as e:
    db.rollback()
    print("\nError:", e)

finally:
    db.close()
