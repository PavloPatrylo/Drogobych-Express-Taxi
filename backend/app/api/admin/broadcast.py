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


from sqlalchemy.orm import selectinload

@router.post("/preview")
async def preview_broadcast(
    payload: BroadcastRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    recipients = await _recipient_ids(db, payload.trip_id, payload.target_group)
    return {"recipients_count": len(recipients), "text": payload.text}


@router.post("/send")
async def send_broadcast(
    payload: BroadcastRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_admin_access),
):
    recipients = await _recipient_ids(db, payload.trip_id, payload.target_group)
    background_tasks.add_task(run_telegram_broadcast, recipients, payload.text)

    record_audit_log(
        db,
        current_user,
        "ANNOUNCEMENT_BROADCAST_SENT",
        entity_type="broadcast",
        entity_id=0,
        source="WEB",
        message=f"Оголошення надіслано для ({payload.target_group or 'all'}) ({len(recipients)} осіб): {payload.text[:50]}...",
    )
    await db.commit()

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

    start_dt = datetime.combine(d_from, time.min, tzinfo=KYIV_TZ)
    end_dt = datetime.combine(d_to, time.max, tzinfo=KYIV_TZ)

    stmt = (
        select(Trip)
        .where(
            Trip.departure_time >= start_dt,
            Trip.departure_time <= end_dt,
            Trip.status != TripStatus.CANCELLED,
        )
        .options(
            selectinload(Trip.driver),
            selectinload(Trip.vehicle),
            selectinload(Trip.from_location),
            selectinload(Trip.to_location),
        )
    )
    if payload.driver_id:
        stmt = stmt.where(Trip.driver_id == payload.driver_id)

    res = await db.execute(stmt)
    trips = res.scalars().all()

    driver_trips = {}
    for t in trips:
        if t.driver and t.driver.telegram_id:
            driver_trips.setdefault(t.driver, []).append(t)

    drivers_notified = 0
    for driver, d_trips in driver_trips.items():
        trips_lines = []
        for tr in sorted(d_trips, key=lambda x: x.departure_time):
            dep_date = tr.departure_time.strftime("%d.%m.%Y")
            dep_time = tr.departure_time.strftime("%H:%M")
            route_name = (
                f"{tr.from_location.name} -> {tr.to_location.name}"
                if (tr.from_location and tr.to_location)
                else tr.route
            )
            vehicle_info = f"{tr.vehicle.model} ({tr.vehicle.plate_number})" if tr.vehicle else "Авто не призначено"
            trips_lines.append(f"🚌 **Рейс #{tr.id}** — {dep_date} о {dep_time}\n   Маршрут: {route_name}\n   Авто: {vehicle_info}")

        lines_text = "\n\n".join(trips_lines)
        comment_text = f"\n\n💬 *Примітка диспетчера:* {payload.comment}" if payload.comment else ""
        msg_text = (
            f"📅 **ОФІЦІЙНИЙ ГРАФІК РЕЙСІВ**\n"
            f"Період: {payload.date_from} — {payload.date_to}\n\n"
            f"{lines_text}"
            f"{comment_text}\n\n"
            f"Будь ласка, прибудьте на посадку за 15 хвилин до відправлення."
        )
        asyncio.create_task(run_telegram_broadcast([driver.telegram_id], msg_text))
        drivers_notified += 1

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
        message=f"Графік опубліковано для {driver_label} на період {payload.date_from} — {payload.date_to} ({drivers_notified} водіїв сповіщено в Telegram). Примітка: {payload.comment or '—'}",
    )
    await db.commit()

    return {
        "success": True,
        "message": f"Графік рейсів з {payload.date_from} по {payload.date_to} для ({driver_label}) успішно опубліковано! ({drivers_notified} водіїв отримали сповіщення у Telegram)",
        "date_from": payload.date_from,
        "date_to": payload.date_to,
        "comment": payload.comment,
    }


async def _recipient_ids(db: AsyncSession, trip_id: int | None = None, target_group: str | None = "all") -> list[int]:
    if target_group == "drivers":
        stmt = select(User.telegram_id).where(
            User.role == UserRole.DRIVER,
            User.telegram_id.isnot(None),
        )
    elif target_group in ["passengers", "all_passengers"]:
        stmt = select(User.telegram_id).where(
            User.role == UserRole.PASSENGER,
            User.telegram_id.isnot(None),
        )
    elif target_group == "today_passengers":
        today = datetime.now(KYIV_TZ).date()
        start_dt = datetime.combine(today, time.min, tzinfo=KYIV_TZ)
        end_dt = datetime.combine(today, time.max, tzinfo=KYIV_TZ)
        stmt = (
            select(User.telegram_id)
            .join(Booking, Booking.passenger_id == User.id)
            .join(Trip, Booking.trip_id == Trip.id)
            .where(
                User.role == UserRole.PASSENGER,
                User.telegram_id.isnot(None),
                Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]),
                Trip.departure_time >= start_dt,
                Trip.departure_time <= end_dt,
            )
        )
    elif trip_id and trip_id > 0:
        stmt = (
            select(User.telegram_id)
            .join(Booking, Booking.passenger_id == User.id)
            .where(
                User.role == UserRole.PASSENGER,
                User.telegram_id.isnot(None),
                Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]),
                Booking.trip_id == trip_id,
            )
        )
    else:
        # "all" or any unspecified group: target all users with telegram_id
        stmt = select(User.telegram_id).where(User.telegram_id.isnot(None))

    result = await db.execute(stmt.distinct())
    return [t_id for (t_id,) in result.all() if t_id]
