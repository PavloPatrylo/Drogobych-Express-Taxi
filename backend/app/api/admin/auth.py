# backend/app/api/admin/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, UserRole
from app.schemas.admin import UserResponse, StaffCreate, StaffUpdate
from app.api.deps import get_current_user, check_owner_access
from app.core.security import hash_password
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Admin Auth"])

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: AsyncSession = Depends(get_db)
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) # Тільки авторизовані можуть бачити персонал
):
    """
    Повертає список водіїв та диспетчерів.
    """
    return await auth_service.get_staff_list(db)


@router.post("/staff", response_model=UserResponse)
async def create_staff_member(
    payload: StaffCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    # Check if user already exists by phone
    dup = await db.execute(select(User).where(User.phone == payload.phone))
    if dup.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Користувач з таким номером телефону вже існує")

    hashed = hash_password(payload.password)
    new_user = User(
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
        password=hashed,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.put("/staff/{user_id}", response_model=UserResponse)
async def update_staff_member(
    user_id: int,
    payload: StaffUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    existing = await db.get(User, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Користувача не знайдено")

    if existing.phone != payload.phone:
        dup = await db.execute(select(User).where(User.phone == payload.phone))
        if dup.scalars().first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Користувач з таким номером телефону вже існує")

    existing.full_name = payload.full_name
    existing.phone = payload.phone
    existing.role = payload.role
    if payload.password:
        existing.password = hash_password(payload.password)

    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/staff/{user_id}")
async def delete_staff_member(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    existing = await db.get(User, user_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Користувача не знайдено")

    # Check if they are driver in active trips
    from app.db.models import Trip
    trip_stmt = select(Trip).where(Trip.driver_id == user_id)
    trip_res = await db.execute(trip_stmt)
    if trip_res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неможливо видалити водія, оскільки він має пов'язані рейси. Спочатку змініть водія у рейсах або видаліть ці рейси."
        )

    try:
        await db.delete(existing)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неможливо видалити користувача через наявність зв'язаних записів в аудиті або фінансах. Рекомендуємо натомість деактивувати його (заблокувати через CRM)."
        )

    return {"message": "Користувача успішно видалено"}