from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_admin_access
from app.db.database import get_db
from app.db.models import User
from app.schemas.admin import AdminUserResponse
from app.services import admin_use_cases

router = APIRouter(tags=["Admin CRM"])


@router.get("/passengers", response_model=list[AdminUserResponse])
async def get_passengers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.list_passengers(db)


@router.post("/passengers/{user_id}/toggle-status", response_model=AdminUserResponse)
async def toggle_passenger_status(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.toggle_passenger(db, user_id, actor=current_user)


@router.post("/passengers/{user_id}/block", response_model=AdminUserResponse)
async def block_passenger(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.toggle_passenger(db, user_id, is_active=False, actor=current_user)


@router.post("/passengers/{user_id}/unblock", response_model=AdminUserResponse)
async def unblock_passenger(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    return await admin_use_cases.toggle_passenger(db, user_id, is_active=True, actor=current_user)
