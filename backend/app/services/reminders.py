import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from aiogram import Bot

from app.core.config import settings
from app.db.database import async_session_maker
from app.db.models import Trip, Booking, BookingStatus, TripStatus, User

logger = logging.getLogger("reminders_scheduler")

try:
    KYIV_TZ = ZoneInfo("Europe/Kyiv")
except Exception:
    KYIV_TZ = ZoneInfo("Europe/Kiev")

reminded_booking_ids = set()

async def send_passenger_trip_reminders():
    now_kyiv = datetime.now(KYIV_TZ)
    window_start = now_kyiv
    window_end = now_kyiv + timedelta(minutes=65)

    async with async_session_maker() as session:
        stmt = (
            select(Trip)
            .where(Trip.departure_time >= window_start)
            .where(Trip.departure_time <= window_end)
            .where(Trip.status.in_([TripStatus.SCHEDULED, TripStatus.BOARDING]))
            .options(
                selectinload(Trip.from_location),
                selectinload(Trip.to_location),
                selectinload(Trip.driver),
                selectinload(Trip.vehicle),
                selectinload(Trip.bookings).selectinload(Booking.passenger),
            )
        )
        result = await session.execute(stmt)
        trips = result.scalars().all()

        if not trips:
            return

        bot = Bot(token=settings.BOT_TOKEN)
        try:
            for trip in trips:
                dep_kyiv = trip.departure_time.astimezone(KYIV_TZ) if trip.departure_time.tzinfo else trip.departure_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(KYIV_TZ)
                date_str = dep_kyiv.strftime("%d.%m.%Y")
                time_str = dep_kyiv.strftime("%H:%M")

                from_name = trip.from_location.name if trip.from_location else "Дрогобич"
                to_name = trip.to_location.name if trip.to_location else "Львів"
                driver_name = trip.driver.full_name if trip.driver else "Водій"
                driver_phone = trip.driver.phone if (trip.driver and trip.driver.phone) else "Вказано під час посадки"
                vehicle_model = trip.vehicle.model if trip.vehicle else "Автобус"
                vehicle_plate = trip.vehicle.plate_number if trip.vehicle else "UA"

                passenger_bookings = {}
                for b in trip.bookings:
                    if b.status in (BookingStatus.RESERVED, BookingStatus.PAID) and b.passenger_id:
                        if getattr(b, 'is_reminder_sent', False) or b.id in reminded_booking_ids:
                            continue
                        p_id = b.passenger_id
                        if p_id not in passenger_bookings:
                            passenger_bookings[p_id] = []
                        passenger_bookings[p_id].append(b)

                for p_id, b_list in passenger_bookings.items():
                    passenger = getattr(b_list[0], 'passenger', None) or await session.get(User, p_id)
                    if not passenger or not passenger.telegram_id:
                        continue

                    seats_count = sum(b.passengers_count for b in b_list)

                    msg_text = (
                        f"⏰ **НАГАДУВАННЯ ПРО ПОЇЗДКУ**\n\n"
                        f"Шановний(а) **{passenger.full_name or 'Пасажир'}**!\n"
                        f"До вашого відправлення залишилася **1 година**! 🚕\n\n"
                        f"📍 **Маршрут**: {from_name} → {to_name}\n"
                        f"🕐 **Час відправлення**: {date_str} о {time_str}\n"
                        f"🚌 **Автомобіль**: {vehicle_model} (`{vehicle_plate}`)\n"
                        f"👨‍✈️ **Водій**: {driver_name} (📞 {driver_phone})\n"
                        f"🎟 **Кількість квитків**: {seats_count} шт.\n\n"
                        f"📍 *Прибудьте на місце посадки за 10 хвилин до відправлення.*"
                    )

                    try:
                        await bot.send_message(chat_id=passenger.telegram_id, text=msg_text, parse_mode="Markdown")
                        for b in b_list:
                            b.is_reminder_sent = True
                            reminded_booking_ids.add(b.id)
                        await session.commit()
                        logger.info(f"Sent trip reminder to passenger {passenger.full_name} ({passenger.telegram_id}) for trip #{trip.id}")
                        await asyncio.sleep(0.1)
                    except Exception as e:
                        logger.warning(f"Failed to send reminder to {passenger.telegram_id}: {e}")
        finally:
            await bot.session.close()

from app.services.admin_use_cases import refresh_user_stats
from app.websocket_manager import manager

async def auto_close_expired_trips():
    now_kyiv = datetime.now(KYIV_TZ)
    async with async_session_maker() as session:
        # 1. Заплановані рейси (SCHEDULED, BOARDING): закриваємо, лише якщо виїзд був понад 2 години тому і водій так і не виїхав
        stmt_unstarted = (
            select(Trip)
            .where(Trip.departure_time < now_kyiv - timedelta(hours=2))
            .where(Trip.status.in_([TripStatus.SCHEDULED, TripStatus.BOARDING]))
        )
        unstarted_trips = (await session.execute(stmt_unstarted)).scalars().all()

        # 2. Рейси "В дорозі" (ACTIVE): закриваємо тільки після завершення часу прибуття (arrival_time + 1 година)!
        stmt_active = (
            select(Trip)
            .where(Trip.status == TripStatus.ACTIVE)
        )
        active_trips_all = (await session.execute(stmt_active)).scalars().all()
        active_expired = []
        for trip in active_trips_all:
            arr_time = trip.arrival_time or (trip.departure_time + timedelta(hours=2))
            if arr_time.tzinfo is None:
                arr_time = arr_time.replace(tzinfo=ZoneInfo("UTC"))
            arr_kyiv = arr_time.astimezone(KYIV_TZ)
            if now_kyiv > arr_kyiv + timedelta(hours=1):
                active_expired.append(trip)

        expired_trips = list(unstarted_trips) + active_expired
        if not expired_trips:
            return

        for trip in expired_trips:
            trip.status = TripStatus.COMPLETED

            b_stmt = select(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID])
            )
            bookings_to_noshow = (await session.execute(b_stmt)).scalars().all()
            for b in bookings_to_noshow:
                b.status = BookingStatus.NOSHOW
                if b.passenger_id:
                    await refresh_user_stats(session, b.passenger_id)

            await manager.broadcast("TRIP_MUTATED", {"trip_id": trip.id})
            logger.info(f"Auto-closed overdue trip #{trip.id} (status: {trip.status}) to COMPLETED")

        await session.commit()

async def start_reminder_scheduler():
    logger.info("Starting background scheduler (reminders & auto-close overdue trips)...")
    while True:
        try:
            await auto_close_expired_trips()
            await send_passenger_trip_reminders()
        except Exception as e:
            logger.error(f"Error in background scheduler: {e}")
        await asyncio.sleep(60)
