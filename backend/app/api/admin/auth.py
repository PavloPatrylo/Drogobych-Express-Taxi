# backend/app/api/admin/auth.py
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.schemas.admin import UserResponse
from app.api.deps import get_current_user
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Admin Auth"])

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    Вхід в систему. 
    form_data.username - це номер телефону.
    """
    # 1. Автентифікація через сервіс
    user = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    
    # 2. Генерація токена через сервіс
    token = auth_service.create_access_token(user.id, user.role)
    
    return {
        "access_token": token, 
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Повертає профіль поточного адміністратора/диспетчера.
    """
    return current_user

@router.get("/staff", response_model=list[UserResponse])
async def get_staff(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Тільки авторизовані можуть бачити персонал
):
    """
    Повертає список водіїв та диспетчерів.
    """
    return await auth_service.get_staff_list(db)