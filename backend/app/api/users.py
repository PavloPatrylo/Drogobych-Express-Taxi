# app/api/users.py

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import async_session_maker
from app.db.models import User, UserStats, UserRole
from app.schemas.user import UserRead

from app.schemas.user import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/{telegram_id}", response_model=UserRead)
async def get_user_by_telegram_id(telegram_id: int):
    """
    Отримує профіль користувача та його статистику за Telegram ID.
    """
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
):
    """
    Дозволяє пасажиру змінити своє ПІБ / телефон у профілі.
    """
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
        await session.refresh(user)
        return user