import asyncio
from datetime import datetime, time
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot

from app.core.config import settings
from app.api.deps import check_admin_access
from app.db.database import get_db
from app.db.models import Booking, BookingStatus, User, Trip, TripStatus, UserRole
from app.schemas.admin import BroadcastRequest, PublishScheduleRequest, PublishSchedulePreviewResponse
from app.services.admin_use_cases import record_audit_log

try:
    KYIV_TZ = ZoneInfo("Europe/Kyiv")
except Exception:
    KYIV_TZ = ZoneInfo("Europe/Kiev")

router = APIRouter(prefix="/broadcast", tags=["Admin Broadcast"])


async def run_telegram_broadcast(recipients: list[int], text: str):
    bot = Bot(token=settings.BOT_TOKEN)
    try:
        for telegram_id in recipients:
            try:
                await bot.send_message(chat_id=telegram_id, text=text)
                await asyncio.sleep(0.05)  # respect rate limit
            except Exception:
                pass
    finally:
        await bot.session.close()


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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    recipients = await _recipient_ids(db, payload.trip_id)
    background_tasks.add_task(run_telegram_broadcast, recipients, payload.text)
    return {
        "message": "Broadcast queued",
        "recipients_count": len(recipients),
        "sent_by": current_user.id,
    }


# ══════════════════════════════════════════════
# ПУБЛІКАЦІЯ ГРАФІКІВ ДЛЯ ВОДІЇВ ДИСПЕТЧЕРОМ
# ══════════════════════════════════════════════
@router.post("/publish-schedule/preview", response_model=PublishSchedulePreviewResponse)
async def preview_publish_schedule(
    payload: PublishScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    try:
        d_from = datetime.strptime(payload.date_from, "%Y-%m-%d").date()
        d_to = datetime.strptime(payload.date_to, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Формат дати повинен бути YYYY-MM-DD")

    start_dt = datetime.combine(d_from, time.min, tzinfo=KYIV_TZ)
    end_dt = datetime.combine(d_to, time.max, tzinfo=KYIV_TZ)

    stmt = select(Trip).where(
        Trip.departure_time >= start_dt,
        Trip.departure_time <= end_dt,
        Trip.status != TripStatus.CANCELLED,
    )
    if payload.driver_id:
        stmt = stmt.where(Trip.driver_id == payload.driver_id)

    res = await db.execute(stmt)
    trips = res.scalars().all()

    trips_count = len(trips)
    distinct_drivers = {t.driver_id for t in trips if t.driver_id}
    drivers_count = len(distinct_drivers)
    total_seats_limit = sum(t.seats_limit_snapshot for t in trips)

    # Calculate total revenue for active bookings in this set of trips
    if trips:
        trip_ids = [t.id for t in trips]
        b_stmt = select(func.sum(Booking.amount_paid)).where(
            Booking.trip_id.in_(trip_ids),
            Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]),
        )
        b_res = await db.execute(b_stmt)
        total_revenue = float(b_res.scalar() or 0.0)
    else:
        total_revenue = 0.0

    return PublishSchedulePreviewResponse(
        trips_count=trips_count,
        drivers_count=drivers_count,
        total_seats_limit=total_seats_limit,
        total_revenue=total_revenue,
        date_from=payload.date_from,
        date_to=payload.date_to,
    )


@router.post("/publish-schedule")
async def publish_schedule(
    payload: PublishScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    try:
        d_from = datetime.strptime(payload.date_from, "%Y-%m-%d").date()
        d_to = datetime.strptime(payload.date_to, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Формат дати повинен бути YYYY-MM-DD")

    driver_label = "Усім водіям"
    if payload.driver_id:
        driver = await db.get(User, payload.driver_id)
        if driver:
            driver_label = f"Водію {driver.full_name}"

    record_audit_log(
        db,
        current_user,
        "DRIVER_SCHEDULE_PUBLISHED",
        entity_type="schedule",
        entity_id=0,
        source="WEB",
        message=f"Графік опубліковано для {driver_label} на період {payload.date_from} — {payload.date_to}. Примітка: {payload.comment or '—'}",
    )
    await db.commit()

    return {
        "success": True,
        "message": f"Графік рейсів з {payload.date_from} по {payload.date_to} для ({driver_label}) успішно опубліковано!",
        "date_from": payload.date_from,
        "date_to": payload.date_to,
        "comment": payload.comment,
    }


async def _recipient_ids(db: AsyncSession, trip_id: int | None) -> list[int]:
    if not trip_id or trip_id == 0:
        stmt = select(User.telegram_id).where(User.telegram_id.is_not(None))
    else:
        stmt = (
            select(User.telegram_id)
            .join(Booking, Booking.passenger_id == User.id)
            .where(User.telegram_id.is_not(None))
            .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
            .where(Booking.trip_id == trip_id)
        )

    result = await db.execute(stmt.distinct())
    return [telegram_id for telegram_id in result.scalars().all() if telegram_id]
