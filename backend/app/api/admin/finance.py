from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_owner_access
from app.db.database import get_db
from app.db.models import User
from app.schemas.admin import AdminCloseTripRequest, AdminTripResponse
from app.services import admin_use_cases

router = APIRouter(prefix="/finance", tags=["Admin Finance"])


@router.get("/summary")
async def get_finance_summary(
    date_from: str | None = None,
    date_to: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    return await admin_use_cases.finance_summary(db, date_from, date_to)


@router.get("/trips/{trip_id}/stats")
async def get_trip_stats(
    trip_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    return await admin_use_cases.trip_finance_stats(db, trip_id)


@router.post("/trips/{trip_id}/close", response_model=AdminTripResponse)
async def close_trip(
    trip_id: int,
    payload: AdminCloseTripRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_owner_access),
):
    return await admin_use_cases.close_trip(db, trip_id, current_user, payload.submitted_amount)
