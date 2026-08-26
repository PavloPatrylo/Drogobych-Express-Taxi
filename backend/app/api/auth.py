# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.telegram import verify_telegram_webapp_init_data
from app.db.database import get_db
from app.db.models import User, UserStats, UserRole
from app.schemas.user import TelegramWebAppAuth, AuthTokenResponse, UserRead
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

    tg_user = data.get("user") or {}
    tg_id = tg_user.get("id")
    if not tg_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User data missing from Telegram initData"
        )

    # 1. Look up existing user by telegram_id
    stmt = (
        select(User)
        .where(User.telegram_id == int(tg_id))
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
            telegram_id=int(tg_id),
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
