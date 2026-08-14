# backend/generate_admin_hash.py
from app.core.security import hash_password

def create_admin_hash():
    password = "12345"  # Твій тестовий пароль
    hashed = hash_password(password)
    print(f"\n--- Скопіюй цей хеш для БД ---")
    print(f"{hashed}")
    print(f"-------------------------------\n")

if __name__ == "__main__":
    create_admin_hash()