# backend/app/services/auth_service.py
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.future import select
from datetime import datetime, timedelta
from typing import Union
from jose import jwt

from app.db.models import User, UserRole
from app.core.config import settings
from app.core.security import verify_password

def create_access_token(user_id: int, role: Union[UserRole, str]):
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    role_str = role.value if hasattr(role, "value") else str(role)
    data = {"sub": str(user_id), "role": role_str, "exp": expire}
    return jwt.encode(data, settings.SECRET_KEY, algorithm="HS256")

async def authenticate_user(db: Session, phone: str, password: str):
    # 1. Пошук користувача (лише за номером телефону)
    result = await db.execute(select(User).filter(User.phone == phone))
    user = result.scalars().first()
    
    # 2. Перевірка наявності пароля та верифікація через bcrypt (запобігає 500 помилці)
    if not user or not user.password or not verify_password(password, user.password):
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
        
    # 4. Перевірка доступу до адмін-панелі та кабінету працівника
    role_str = (user.role.value if hasattr(user.role, "value") else str(user.role)).upper()
    if role_str not in ["ADMIN", "DISPATCHER", "DRIVER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Доступ заборонено"
        )
        
    return user

async def get_staff_list(db: Session):
    """Повертає список водіїв, диспетчерів та адміністраторів."""
    result = await db.execute(
        select(User).filter(
            User.role.in_([
                UserRole.DRIVER, UserRole.DISPATCHER, UserRole.ADMIN,
                "driver", "dispatcher", "admin",
                "DRIVER", "DISPATCHER", "ADMIN"
            ])
        )
    )
    return result.scalars().all()
