from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_admin_access
from app.db.database import get_db
from app.db.models import Booking, BookingStatus, User
from app.schemas.admin import BroadcastRequest

router = APIRouter(prefix="/broadcast", tags=["Admin Broadcast"])


@router.post("/preview")
async def preview_broadcast(
    payload: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    recipients = await _recipient_ids(db, payload.trip_id)
    return {"recipients_count": len(recipients), "text": payload.text}


@router.post("/send")
async def send_broadcast(
    payload: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    recipients = await _recipient_ids(db, payload.trip_id)
    return {
        "message": "Broadcast queued",
        "recipients_count": len(recipients),
        "sent_by": current_user.id,
    }


async def _recipient_ids(db: AsyncSession, trip_id: int | None) -> list[int]:
    stmt = (
        select(User.telegram_id)
        .join(Booking, Booking.passenger_id == User.id)
        .where(User.telegram_id.is_not(None))
        .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
    )
    if trip_id is not None:
        stmt = stmt.where(Booking.trip_id == trip_id)

    result = await db.execute(stmt.distinct())
    return [telegram_id for telegram_id in result.scalars().all() if telegram_id]
