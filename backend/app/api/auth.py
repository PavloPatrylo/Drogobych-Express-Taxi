from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.telegram import verify_telegram_webapp_init_data
from app.db.database import get_db
from app.db.models import User, UserStats, UserRole
from app.schemas.user import TelegramWebAppAuth, DevLoginRequest, AuthTokenResponse, UserRead
from app.services.auth_service import create_access_token

router = APIRouter(prefix="/auth", tags=["Public Authentication"])

@router.post("/telegram-webapp", response_model=AuthTokenResponse)
async def telegram_webapp_login(
    payload: TelegramWebAppAuth,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates Telegram WebApp initData, auto-provisions PASSENGER users if new,
    and returns a valid JWT Access Token.
    Strictly verifies Telegram HMAC-SHA256 signature and rejects unverified or spoofed requests.
    """
    try:
        data = verify_telegram_webapp_init_data(
            init_data=payload.init_data,
            bot_token=settings.BOT_TOKEN,
            max_age_seconds=settings.MAX_INIT_DATA_AGE_SECONDS
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Telegram authentication failed: {str(e)}"
        )

    tg_user = data.get("user")
    if not tg_user or not tg_user.get("id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram user payload is missing from initData"
        )

    tg_id = int(tg_user["id"])

    # 1. Look up existing user by telegram_id
    stmt = (
        select(User)
        .where(User.telegram_id == tg_id)
        .options(selectinload(User.stats))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is blocked"
            )
    else:
        # 2. Provision new user ONLY as PASSENGER
        first_name = tg_user.get("first_name", "")
        last_name = tg_user.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip() or tg_user.get("username") or "Пасажир"

        user = User(
            telegram_id=tg_id,
            full_name=full_name,
            role=UserRole.PASSENGER,
            is_active=True,
            stats=UserStats(total_trips=0, total_noshows=0, trust_score_cached=100)
        )
        db.add(user)
        await db.commit()
        
        # Reload with stats
        stmt_reload = (
            select(User)
            .where(User.id == user.id)
            .options(selectinload(User.stats))
        )
        user = (await db.execute(stmt_reload)).scalar_one()

    # 3. Create Access Token with internal user.id as sub
    token = create_access_token(user_id=user.id, role=user.role)

    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user)
    )


@router.post("/dev-login", response_model=AuthTokenResponse)
async def dev_login(
    payload: Optional[DevLoginRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Development-only login endpoint for running in browser (Chrome) without Telegram.
    Strictly disabled unless DEV_AUTH_ENABLED is explicitly True in server config.
    """
    if not settings.DEV_AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev authentication is disabled"
        )

    req_tg_id = payload.telegram_id if payload else None
    req_role = payload.role if payload else None

    user = None
    if req_tg_id:
        stmt = (
            select(User)
            .where(User.telegram_id == req_tg_id)
            .options(selectinload(User.stats))
        )
        user = (await db.execute(stmt)).scalar_one_or_none()

    if not user and req_role:
        stmt = (
            select(User)
            .where(User.role == req_role, User.is_active == True)
            .order_by(
                User.telegram_id.isnot(None).desc(),
                (User.id == 34).desc() if req_role == UserRole.DRIVER else (User.id == 33).desc(),
                User.id.desc()
            )
            .options(selectinload(User.stats))
            .limit(1)
        )
        user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        # Для Mini App за замовчуванням вибираємо пасажира (щоб не брати акаунт адміна)
        target_role = req_role or UserRole.PASSENGER
        stmt = (
            select(User)
            .where(User.role == target_role, User.is_active == True)
            .order_by(
                User.telegram_id.isnot(None).desc(),
                (User.id == 33).desc(),
                User.id.desc()
            )
            .options(selectinload(User.stats))
            .limit(1)
        )
        user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        stmt = (
            select(User)
            .where(User.is_active == True)
            .order_by(User.telegram_id.isnot(None).desc(), User.id.desc())
            .options(selectinload(User.stats))
            .limit(1)
        )
        user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        dev_id = req_tg_id or 1685900931
        user = User(
            telegram_id=dev_id,
            phone="+380993227890",
            full_name="Локальний Тестер",
            role=req_role or UserRole.PASSENGER,
            is_active=True,
            is_driver_activated=True,
            stats=UserStats(total_trips=0, total_noshows=0, trust_score_cached=100)
        )
        db.add(user)
        await db.commit()

        stmt_reload = (
            select(User)
            .where(User.id == user.id)
            .options(selectinload(User.stats))
        )
        user = (await db.execute(stmt_reload)).scalar_one()

    # СУВОРА ГАРАНТІЯ ДЛЯ DEV-РЕЖИМУ:
    # Користувач ОБОВ'ЯЗКОВО повинен мати валідний telegram_id та підтверджений телефон,
    # щоб усі функції Mini App (квитки, маніфест, бронювання) працювали без помилок.
    modified = False
    if user.telegram_id is None:
        user.telegram_id = 1000000000 + user.id
        modified = True
    if not user.phone:
        user.phone = f"+3809900000{user.id:02d}"
        modified = True
    if not user.is_active:
        user.is_active = True
        modified = True
    if user.role == UserRole.DRIVER and not user.is_driver_activated:
        user.is_driver_activated = True
        modified = True
    if modified:
        await db.commit()
        await db.refresh(user)

    token = create_access_token(user_id=user.id, role=user.role)
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user)
    )
