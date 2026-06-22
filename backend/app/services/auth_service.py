# backend/app/services/auth_service.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from datetime import datetime, timedelta
from jose import jwt

from app.db.models import User, UserRole
from app.core.config import settings
from app.core.security import verify_password  # <-- Імпортуємо наш надійний верифікатор

def create_access_token(user_id: int, role: UserRole):
    expire = datetime.utcnow() + timedelta(minutes=60 * 24)
    data = {"sub": str(user_id), "role": role.value, "exp": expire}
    return jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")

async def authenticate_user(db: Session, phone: str, password: str):
    # 1. Пошук користувача
    result = await db.execute(select(User).filter(User.phone == phone))
    user = result.scalars().first()
    
    # 2. Верифікація пароля через наш core.security (bcrypt)
    # Якщо користувача немає або пароль невірний, викидаємо 401
    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Невірні облікові дані"
        )
    
    # 3. Перевірка статусу акаунту
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Акаунт заблоковано"
        )
        
    # 4. Перевірка доступу до адмін-панелі
    if user.role not in [UserRole.ADMIN, UserRole.DISPATCHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Доступ заборонено"
        )
        
    return user

async def get_staff_list(db: Session):
    """Повертає список водіїв та диспетчерів."""
    result = await db.execute(
        select(User).filter(User.role.in_([UserRole.DRIVER, UserRole.DISPATCHER, UserRole.ADMIN]))
    )
    return result.scalars().all()