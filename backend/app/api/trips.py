from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import date, datetime, time
from typing import List

from sqlalchemy.orm import aliased
from datetime import datetime, timezone

from app.db.database import async_session_maker
from app.schemas.trip import TripReadPassenger, LocationRead

from app.schemas.booking import TripManifest, TripStatusUpdate

from app.db.models import (
    Trip,
    Location,
    Booking,
    User,
    TripStatus,
    BookingStatus,
    BookingType,
    UserRole,
    AuditLog,
)

from datetime import datetime
from zoneinfo import ZoneInfo # 👈 Додаємо для підтримки київського часу
# Створюємо об'єкт часового поясу

try:
    KYIV_TZ = ZoneInfo("Europe/Kyiv")
except Exception:
    KYIV_TZ = ZoneInfo("Europe/Kiev")

router = APIRouter(prefix="/trips", tags=["Trips"])

# 1. Отримати список міст (для випадаючого списку "Звідки" / "Куди")
@router.get("/locations", response_model=List[LocationRead])
async def get_locations():
    async with async_session_maker() as session:
        result = await session.execute(select(Location).order_by(Location.name))
        return result.scalars().all()

# 2. Пошук рейсів (UC-P2)
@router.get("/search", response_model=List[TripReadPassenger])
async def search_trips(
    from_id: int = Query(...),
    to_id: int = Query(...),
    travel_date: date = Query(...)
):
    """
    Шукає рейси за напрямком та датою і вираховує кількість вільних місць.
    """
    async with async_session_maker() as session:
        # Визначаємо початок і кінець обраної доби у Київському часовому поясі
        now_kyiv = datetime.now(KYIV_TZ)
        start_of_day = datetime.combine(travel_date, time.min, tzinfo=KYIV_TZ)
        end_of_day = datetime.combine(travel_date, time.max, tzinfo=KYIV_TZ)

        # Якщо пасажир шукає рейси на СЬОГОДНІ — відсікаємо минулі рейси, які вже виїхали!
        if travel_date == now_kyiv.date():
            start_of_day = max(start_of_day, now_kyiv)

        # Шукаємо рейси (status = SCHEDULED або BOARDING)
        stmt = (
            select(Trip)
            .where(Trip.from_location_id == from_id)
            .where(Trip.to_location_id == to_id)
            .where(Trip.departure_time >= start_of_day)
            .where(Trip.departure_time <= end_of_day)
            .where(Trip.status.in_([TripStatus.SCHEDULED, TripStatus.BOARDING]))
            .options(
                selectinload(Trip.from_location), 
                selectinload(Trip.to_location),
                selectinload(Trip.vehicle) # 👈 ДОДАЛИ ЦЕЙ РЯДОК
            )
            .order_by(Trip.departure_time)
        )
        
        result = await session.execute(stmt)
        trips = result.scalars().all()

        response_trips = []
        
        # Обчислюємо available_seats для кожного рейсу згідно з SRS (UC-P2.6)
        for trip in trips:
            # Шукаємо суму всіх проданих сидячих місць на цей рейс
            booked_stmt = (
                select(func.sum(Booking.passengers_count))
                .where(Booking.trip_id == trip.id)
                .where(Booking.booking_type == BookingType.SEATED)
                .where(Booking.status.not_in([BookingStatus.CANCELLED, BookingStatus.NOSHOW]))
            )
            booked_result = await session.execute(booked_stmt)
            booked_seats = booked_result.scalar() or 0
            
            # Вільні місця = Ліміт - Зайняті
            available = trip.seats_limit_snapshot - booked_seats
            
            # Додаємо рейс у відповідь, якщо є хоч одне місце (або можемо віддавати всі, а фронт напише "Місць немає")
            trip_data = TripReadPassenger(
                id=trip.id,
                from_location=trip.from_location,
                to_location=trip.to_location,
                departure_time=trip.departure_time,
                price_seated=trip.price_seated,
                available_seats=available,
                status=trip.status.value,

                vehicle_plate=trip.vehicle.plate_number if trip.vehicle else "Не вказано",
                vehicle_model=trip.vehicle.model if trip.vehicle else "Автобус"
            );
            response_trips.append(trip_data)

        return response_trips
    
# === ОТРИМАТИ МАНІФЕСТ ДЛЯ ВОДІЯ (UC-D1 - FULL) ===
@router.get("/driver/{telegram_id}/manifest", response_model=list[TripManifest])
async def get_driver_manifest(telegram_id: int, target_date: str = None):
    from app.services.reminders import auto_close_expired_trips
    await auto_close_expired_trips()

    async with async_session_maker() as session:
        # 1. Знаходимо водія
        user_stmt = select(User).where(User.telegram_id == telegram_id, User.role == UserRole.DRIVER)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        
        if not driver:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        now_kyiv = datetime.now(KYIV_TZ)
        if target_date:
            try:
                filter_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                filter_date = now_kyiv.date()
        else:
            filter_date = now_kyiv.date()

        # 2. Отримуємо рейси водія
        FromLoc = aliased(Location)
        ToLoc = aliased(Location)
        
        trips_stmt = (
            select(Trip, FromLoc.name, ToLoc.name)
            .join(FromLoc, Trip.from_location_id == FromLoc.id)
            .join(ToLoc, Trip.to_location_id == ToLoc.id)
            .where(Trip.driver_id == driver.id)
            .where(Trip.status.in_([TripStatus.SCHEDULED, TripStatus.BOARDING, TripStatus.ACTIVE, TripStatus.COMPLETED, TripStatus.CLOSED]))
            .order_by(Trip.departure_time)
        )
        trips_rows = (await session.execute(trips_stmt)).all()

        manifests = []
        for trip, from_name, to_name in trips_rows:
            if trip.departure_time:
                dep_aware = trip.departure_time.replace(tzinfo=ZoneInfo("UTC")) if trip.departure_time.tzinfo is None else trip.departure_time
                trip_date_kyiv = dep_aware.astimezone(KYIV_TZ).date()
                if trip_date_kyiv != filter_date:
                    continue
            # !!! ОДИНАКОВИЙ ФІЛЬТР ДЛЯ ВСІХ ТИПІВ БРОНЮВАНЬ !!!
            # Ми обов'язково фільтруємо за trip.id
            bookings_stmt = (
                select(Booking, User)
                .outerjoin(User, Booking.passenger_id == User.id)
                .where(Booking.trip_id == trip.id)  # <--- ЦЕЙ РЯДОК РОЗДІЛЯЄ БРОНЮВАННЯ ПО РЕЙСАХ
                .where(Booking.status != BookingStatus.CANCELLED)
            )
            bookings_rows = (await session.execute(bookings_stmt)).all()

            passengers = []
            booked_seated_count = 0
            
            for booking, passenger in bookings_rows:
                # Рахуємо тільки сидячі для ліміту місць в автобусі
                if booking.booking_type == BookingType.SEATED:
                    booked_seated_count += booking.passengers_count
                
                # 👇 ДОДАЙ ЦЕЙ БЛОК ДЛЯ ПРАВИЛЬНОГО ІМЕНІ 👇
                if passenger:
                    display_name = passenger.full_name
                elif booking.booking_type.name == 'STANDING':
                    display_name = "Стоячий пасажир"
                elif booking.booking_type.name == 'PARCEL':
                    # Якщо водій ввів опис (наприклад телефон), покажемо його
                    display_name = f"Посилка: {booking.comment}" if getattr(booking, 'comment', None) else "Посилка"
                else:
                    display_name = "Запис"
                # 👆 КІНЕЦЬ НОВОГО БЛОКУ 👆

                passengers.append({
                    "booking_id": booking.id,
                    "full_name": display_name, # <--- ТУТ ТЕПЕР ВИКОРИСТОВУЄМО display_name
                    "phone": passenger.phone if passenger else "-",
                    "seats": booking.passengers_count,
                    "status": booking.status.name,
                    "amount_paid": float(booking.amount_paid),
                    "booking_type": booking.booking_type.name
                })

            manifests.append({
                "trip_id": trip.id,
                "departure_time": trip.departure_time,
                "from_location": from_name,
                "to_location": to_name,
                "available_seats": trip.seats_limit_snapshot - booked_seated_count,
                "trip_status": trip.status.name,
                "passengers": passengers
            })

        return manifests
    
# === ЗМІНА СТАТУСУ РЕЙСУ (UC-D2 та Скасування Диспетчером) ===
@router.patch("/{trip_id}/status")
async def update_trip_status(trip_id: int, telegram_id: int, payload: TripStatusUpdate):
    async with async_session_maker() as session:
        # 1. Знаходимо користувача, який робить запит (Водій або Диспетчер)
        user_stmt = select(User).where(User.telegram_id == telegram_id)
        actor = (await session.execute(user_stmt)).scalar_one_or_none()
        
        if not actor:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        # 2. Знаходимо рейс
        trip_stmt = select(Trip).where(Trip.id == trip_id)
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        
        if not trip:
            raise HTTPException(status_code=404, detail="Рейс не знайдено")

        current_status = trip.status.name if hasattr(trip.status, 'name') else trip.status
        requested_status = payload.status

        # 3. ЛОГІКА ДИСПЕТЧЕРА: Скасування рейсу
        if requested_status == 'CANCELLED':
            if actor.role != UserRole.DISPATCHER:
                raise HTTPException(status_code=403, detail="Тільки диспетчер має право скасовувати рейс")
            
            trip.status = TripStatus.CANCELLED
            
            # Автоматично скасовуємо всі заброньовані/оплачені квитки на цей рейс
            bookings_stmt = select(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID])
            )
            bookings_to_cancel = (await session.execute(bookings_stmt)).scalars().all()
            for b in bookings_to_cancel:
                b.status = BookingStatus.CANCELLED
                
        # 4. ЛОГІКА ВОДІЯ: Звичайний або прискорений рух/закриття рейсу
        else:
            if actor.role != UserRole.DRIVER or trip.driver_id != actor.id:
                raise HTTPException(status_code=403, detail="Це не ваш рейс або ви не водій")

            # Дозволяємо водію переводити рейс у COMPLETED з будь-якого стану (SCHEDULED, BOARDING, ACTIVE)
            valid_driver_statuses = ['SCHEDULED', 'BOARDING', 'ACTIVE']

            if requested_status == 'COMPLETED':
                if current_status not in valid_driver_statuses:
                    raise HTTPException(status_code=400, detail="Цей рейс вже закритий або не може бути завершений")
                trip.status = TripStatus.COMPLETED
                
                # При завершенні рейсу всі невідмічені квитки отримують НЕЯВКА (NOSHOW)
                bookings_stmt = select(Booking).where(
                    Booking.trip_id == trip.id,
                    Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID])
                )
                bookings_to_noshow = (await session.execute(bookings_stmt)).scalars().all()
                for b in bookings_to_noshow:
                    b.status = BookingStatus.NOSHOW
            else:
                valid_transitions = {
                    'SCHEDULED': 'BOARDING',
                    'BOARDING': 'ACTIVE',
                    'ACTIVE': 'COMPLETED'
                }
                if current_status not in valid_transitions or valid_transitions[current_status] != requested_status:
                    raise HTTPException(status_code=400, detail="Ця дія недоступна")
                
                trip.status = TripStatus[requested_status]

                if requested_status == 'ACTIVE':
                    bookings_stmt = select(Booking).where(
                        Booking.trip_id == trip.id,
                        Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID])
                    )
                    bookings_to_noshow = (await session.execute(bookings_stmt)).scalars().all()
                    for b in bookings_to_noshow:
                        b.status = BookingStatus.NOSHOW

        await session.commit()
        await manager.broadcast("TRIP_MUTATED", {"trip_id": trip.id})
        return {"message": f"Статус рейсу змінено на {requested_status}"}

# === ФІНАНСОВИЙ ЗВІТ ВОДІЯ ЗА ДЕНЬ (КИЇВСЬКИЙ ЧАС) ===
@router.get("/driver/{telegram_id}/summary")
async def get_driver_daily_summary(telegram_id: int, target_date: str = None):
    async with async_session_maker() as session:
        user_stmt = select(User).where(User.telegram_id == telegram_id, User.role == UserRole.DRIVER)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        if not driver:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        # 1. Визначаємо поточну дату в Києві
        now_kyiv = datetime.now(KYIV_TZ)
        
        if target_date:
            try:
                # Очікуємо рядок YYYY-MM-DD з фронтенду
                filter_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            except ValueError:
                filter_date = now_kyiv.date()
        else:
            filter_date = now_kyiv.date()

        FromLoc = aliased(Location)
        ToLoc = aliased(Location)
        
        start_dt = datetime.combine(filter_date, time.min, tzinfo=KYIV_TZ)
        end_dt = datetime.combine(filter_date, time.max, tzinfo=KYIV_TZ)

        trips_stmt = (
            select(Trip, FromLoc.name, ToLoc.name)
            .join(FromLoc, Trip.from_location_id == FromLoc.id)
            .join(ToLoc, Trip.to_location_id == ToLoc.id)
            .where(Trip.driver_id == driver.id)
            .where(Trip.departure_time >= start_dt)
            .where(Trip.departure_time <= end_dt)
            .where(Trip.status.in_([TripStatus.COMPLETED, TripStatus.CLOSED]))
            .order_by(Trip.departure_time)
        )
        trips_rows = (await session.execute(trips_stmt)).all()

        summary_list = []
        total_daily_sum = 0.0
        total_cash_sum = 0.0
        total_card_sum = 0.0

        for trip, from_name, to_name in trips_rows:
            bookings_stmt = select(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status.in_([BookingStatus.BOARDED, BookingStatus.PAID, BookingStatus.RESERVED])
            )
            bookings = (await session.execute(bookings_stmt)).scalars().all()

            seated = sum(b.passengers_count for b in bookings if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() == 'SEATED')
            standing = sum(b.passengers_count for b in bookings if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() == 'STANDING')
            parcels = sum(1 for b in bookings if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() == 'PARCEL')
            
            # Розрахункова сума рейсів (Скільки водій ПОВИНЕН здати за підсумками активних квитків)
            expected_trip_sum = sum(float(b.amount_paid or 0) for b in bookings)

            c_cash = float(trip.submitted_cash) if trip.submitted_cash is not None else expected_trip_sum
            c_card = float(trip.submitted_card) if trip.submitted_card is not None else 0.0

            total_daily_sum += expected_trip_sum
            total_cash_sum += c_cash
            total_card_sum += c_card

            dep_aware = trip.departure_time.replace(tzinfo=ZoneInfo("UTC")) if trip.departure_time.tzinfo is None else trip.departure_time
            dep_kyiv = dep_aware.astimezone(KYIV_TZ)

            summary_list.append({
                "trip_id": trip.id,
                "route": f"{from_name} → {to_name}",
                "time": dep_kyiv.strftime("%H:%M"),
                "status": trip.status.name,
                "submitted_cash": c_cash,
                "submitted_card": c_card,
                "seated": seated,
                "standing": standing,
                "parcels": parcels,
                "trip_sum": expected_trip_sum
            })

        return {
            "date": filter_date.strftime("%d.%m.%Y"),
            "total_to_hand_in": total_daily_sum,
            "total_cash": total_cash_sum,
            "total_card": total_card_sum,
            "total_sum": total_daily_sum,
            "trips": summary_list
        }


# === ОПУБЛІКОВАНИЙ ГРАФІК ВОДІЯ (ДЛЯ TELEGRAM MINI APP) ===
@router.get("/driver/{telegram_id}/published-schedule")
async def get_driver_published_schedule(telegram_id: int, date_from: str = None, date_to: str = None):
    async with async_session_maker() as session:
        user_stmt = select(User).where(User.telegram_id == telegram_id, User.role == UserRole.DRIVER)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        if not driver:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        now_kyiv = datetime.now(KYIV_TZ)
        if date_from and date_to:
            try:
                d_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                d_to = datetime.strptime(date_to, "%Y-%m-%d").date()
            except ValueError:
                d_from = now_kyiv.date()
                d_to = now_kyiv.date()
        else:
            d_from = now_kyiv.date()
            d_to = now_kyiv.date()

        audit_stmt = (
            select(AuditLog)
            .where(AuditLog.action == "DRIVER_SCHEDULE_PUBLISHED")
            .order_by(AuditLog.created_at.desc())
        )
        audit_res = await session.execute(audit_stmt)
        last_pub = audit_res.scalars().first()

        pub_comment = last_pub.message if last_pub else None

        FromLoc = aliased(Location)
        ToLoc = aliased(Location)

        start_dt = datetime.combine(d_from, time.min, tzinfo=KYIV_TZ)
        end_dt = datetime.combine(d_to, time.max, tzinfo=KYIV_TZ)

        trips_stmt = (
            select(Trip, FromLoc.name, ToLoc.name)
            .options(selectinload(Trip.vehicle))
            .join(FromLoc, Trip.from_location_id == FromLoc.id)
            .join(ToLoc, Trip.to_location_id == ToLoc.id)
            .where(Trip.driver_id == driver.id)
            .where(Trip.departure_time >= start_dt)
            .where(Trip.departure_time <= end_dt)
            .where(Trip.status != TripStatus.CANCELLED)
            .order_by(Trip.departure_time)
        )
        trips_rows = (await session.execute(trips_stmt)).all()

        schedule_trips = []
        total_seats = 0
        total_revenue = 0.0

        for trip, from_name, to_name in trips_rows:
            dep_aware = trip.departure_time.replace(tzinfo=ZoneInfo("UTC")) if trip.departure_time.tzinfo is None else trip.departure_time
            dep_kyiv = dep_aware.astimezone(KYIV_TZ)
            
            total_seats += trip.seats_limit_snapshot
            
            b_stmt = select(func.sum(Booking.passengers_count), func.sum(Booking.amount_paid)).where(
                Booking.trip_id == trip.id,
                Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED])
            )
            b_res = await session.execute(b_stmt)
            b_row = b_res.first()
            booked_count = b_row[0] if b_row and b_row[0] else 0
            rev = float(b_row[1]) if b_row and b_row[1] else 0.0
            total_revenue += rev

            schedule_trips.append({
                "trip_id": trip.id,
                "date": dep_kyiv.strftime("%Y-%m-%d"),
                "date_formatted": dep_kyiv.strftime("%d.%m.%Y"),
                "time": dep_kyiv.strftime("%H:%M"),
                "route": f"{from_name} → {to_name}",
                "from_location": from_name,
                "to_location": to_name,
                "status": trip.status.name,
                "seats_limit": trip.seats_limit_snapshot,
                "booked_seats": booked_count,
                "vehicle_model": trip.vehicle.model if trip.vehicle else "Автобус",
                "vehicle_plate": trip.vehicle.plate_number if trip.vehicle else "—",
            })

        return {
            "driver_name": driver.full_name,
            "date_from": d_from.strftime("%d.%m.%Y"),
            "date_to": d_to.strftime("%d.%m.%Y"),
            "trips_count": len(schedule_trips),
            "total_seats": total_seats,
            "total_revenue": total_revenue,
            "comment": pub_comment,
            "trips": schedule_trips
        }