# app/api/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.database import async_session_maker
from app.db.models import User, UserRole
from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserRead)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Повертає профіль поточного авторизованого користувача та його статистику.
    """
    async with async_session_maker() as session:
        stmt = (
            select(User)
            .where(User.id == current_user.id)
            .options(selectinload(User.stats))
        )
        user = (await session.execute(stmt)).scalar_one()
        return user


@router.put("/me", response_model=UserRead)
async def update_my_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Дозволяє авторизованому користувачу змінити своє ПІБ / телефон у профілі.
    """
    async with async_session_maker() as session:
        stmt = (
            select(User)
            .where(User.id == current_user.id)
            .options(selectinload(User.stats))
        )
        user = (await session.execute(stmt)).scalar_one()

        if payload.full_name is not None and payload.full_name.strip():
            user.full_name = payload.full_name.strip()
        if payload.phone is not None and payload.phone.strip():
            user.phone = payload.phone.strip()

        await session.commit()
        stmt_ref = select(User).where(User.id == user.id).options(selectinload(User.stats))
        return (await session.execute(stmt_ref)).scalar_one()


@router.get("/{telegram_id}", response_model=UserRead)
async def get_user_by_telegram_id(
    telegram_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Отримує профіль користувача за Telegram ID (з авторизаційним контролем).
    """
    if current_user.telegram_id != telegram_id and current_user.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Немає доступу до профілю іншого користувача"
        )

    async with async_session_maker() as session:
        stmt = (
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.stats))
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Користувача не знайдено")

        return user


@router.put("/{telegram_id}", response_model=UserRead)
async def update_user_profile(
    telegram_id: int,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Дозволяє змінити ПІБ / телефон (з авторизаційним контролем).
    """
    if current_user.telegram_id != telegram_id and current_user.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Немає доступу до редагування профілю іншого користувача"
        )

    async with async_session_maker() as session:
        stmt = (
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.stats))
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Користувача не знайдено")

        if payload.full_name is not None and payload.full_name.strip():
            user.full_name = payload.full_name.strip()
        if payload.phone is not None and payload.phone.strip():
            user.phone = payload.phone.strip()

        await session.commit()
        stmt_ref = select(User).where(User.id == user.id).options(selectinload(User.stats))
        return (await session.execute(stmt_ref)).scalar_one()