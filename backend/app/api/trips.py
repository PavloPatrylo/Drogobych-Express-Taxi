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
    UserRole
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
        # Визначаємо початок і кінець обраної доби
        start_of_day = datetime.combine(travel_date, time.min)
        end_of_day = datetime.combine(travel_date, time.max)

        # Шукаємо рейси (status = SCHEDULED або BOARDING)
        stmt = (
            select(Trip)
            .where(Trip.from_location_id == from_id)
            .where(Trip.to_location_id == to_id)
            .where(Trip.departure_time >= start_of_day)
            .where(Trip.departure_time <= end_of_day)
            .where(Trip.status.in_([TripStatus.SCHEDULED, TripStatus.BOARDING]))
            .options(selectinload(Trip.from_location), selectinload(Trip.to_location))
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
                status=trip.status.value
            )
            response_trips.append(trip_data)

        return response_trips
    
# === ОТРИМАТИ МАНІФЕСТ ДЛЯ ВОДІЯ (UC-D1 - FULL) ===
@router.get("/driver/{telegram_id}/manifest", response_model=list[TripManifest])
async def get_driver_manifest(telegram_id: int):
    async with async_session_maker() as session:
        # 1. Знаходимо водія
        user_stmt = select(User).where(User.telegram_id == telegram_id, User.role == UserRole.DRIVER)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        
        if not driver:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        # 2. Отримуємо всі рейси водія
        FromLoc = aliased(Location)
        ToLoc = aliased(Location)
        
        trips_stmt = (
            select(Trip, FromLoc.name, ToLoc.name)
            .join(FromLoc, Trip.from_location_id == FromLoc.id)
            .join(ToLoc, Trip.to_location_id == ToLoc.id)
            .where(Trip.driver_id == driver.id)
            .where(Trip.status.in_([TripStatus.SCHEDULED, TripStatus.BOARDING, TripStatus.ACTIVE]))
            .order_by(Trip.departure_time)
        )
        trips_rows = (await session.execute(trips_stmt)).all()

        manifests = []
        for trip, from_name, to_name in trips_rows:
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
    
# === ЗМІНА СТАТУСУ РЕЙСУ (UC-D2) ===
@router.patch("/{trip_id}/status")
async def update_trip_status(trip_id: int, telegram_id: int, payload: TripStatusUpdate):
    async with async_session_maker() as session:
        # 1. Знаходимо водія
        user_stmt = select(User).where(User.telegram_id == telegram_id)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        
        if not driver:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        # 2. Знаходимо рейс
        trip_stmt = select(Trip).where(Trip.id == trip_id)
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        
        if not trip:
            raise HTTPException(status_code=404, detail="Рейс не знайдено")
            
        if trip.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Це не ваш рейс")

        # 3. Перевірка допустимих переходів (Strict State Machine згідно UC-D2)
        # Ключ - поточний статус, Значення - єдиний можливий наступний статус
        valid_transitions = {
            'SCHEDULED': 'BOARDING',
            'BOARDING': 'ACTIVE',
            'ACTIVE': 'COMPLETED'
        }

        # Якщо статус у БД зберігається як Enum, беремо його ім'я
        current_status = trip.status.name if hasattr(trip.status, 'name') else trip.status
        requested_status = payload.status

        # Альтернативний сценарій A2.1: Неприпустимий перехід
        if current_status not in valid_transitions or valid_transitions[current_status] != requested_status:
            raise HTTPException(status_code=400, detail="Ця дія недоступна")

        # 4. Оновлюємо статус рейсу
        # Якщо в тебе TripStatus - це Enum:
        trip.status = TripStatus[requested_status] 

        # 5. АВТОМАТИЧНИЙ NO-SHOW (Реалізація вимоги UC-D5.3)
        # Якщо рейс вирушив в дорогу (ACTIVE), всі хто не з'явився - отримують NOSHOW
        if requested_status == 'ACTIVE':
            bookings_stmt = select(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID])
            )
            bookings_to_noshow = (await session.execute(bookings_stmt)).scalars().all()
            
            for b in bookings_to_noshow:
                b.status = BookingStatus.NOSHOW
                # Примітка: тут в ідеалі ще треба робити +1 до UserStats.total_noshows пасажира
                # згідно з вимогою FR-11, але це можна додати пізніше, щоб не ускладнювати

        await session.commit()
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
        
        trips_stmt = (
            select(Trip, FromLoc.name, ToLoc.name)
            .join(FromLoc, Trip.from_location_id == FromLoc.id)
            .join(ToLoc, Trip.to_location_id == ToLoc.id)
            .where(Trip.driver_id == driver.id)
            .order_by(Trip.departure_time)
        )
        trips_rows = (await session.execute(trips_stmt)).all()

        summary_list = []
        total_daily_sum = 0.0

        for trip, from_name, to_name in trips_rows:
            status_str = str(getattr(trip.status, 'name', trip.status)).upper()
            if 'COMPLETED' not in status_str:
                continue 
            
            # 2. Конвертуємо час відправлення з бази в київський пояс для порівняння дати
            if trip.departure_time:
                # Переконуємось, що об'єкт datetime має інформацію про зону (зазвичай UTC з бази)
                dep_time_aware = trip.departure_time.replace(tzinfo=ZoneInfo("UTC")) if trip.departure_time.tzinfo is None else trip.departure_time
                trip_date_kyiv = dep_time_aware.astimezone(KYIV_TZ).date()
            else:
                continue

            if trip_date_kyiv != filter_date:
                continue

            bookings_stmt = select(Booking).where(
                Booking.trip_id == trip.id,
                Booking.status == BookingStatus.BOARDED
            )
            bookings = (await session.execute(bookings_stmt)).scalars().all()

            seated = sum(b.passengers_count for b in bookings if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() == 'SEATED')
            standing = sum(b.passengers_count for b in bookings if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() == 'STANDING')
            parcels = sum(1 for b in bookings if (b.booking_type.name if hasattr(b.booking_type, 'name') else str(b.booking_type)).upper() == 'PARCEL')
            
            trip_sum = sum(float(b.amount_paid or 0) for b in bookings)
            total_daily_sum += trip_sum

            summary_list.append({
                "trip_id": trip.id,
                "route": f"{from_name} → {to_name}",
                "time": trip.departure_time.replace(tzinfo=ZoneInfo("UTC")).astimezone(KYIV_TZ).strftime("%H:%M"),
                "seated": seated,
                "standing": standing,
                "parcels": parcels,
                "trip_sum": trip_sum
            })

        return {
            "date": filter_date.strftime("%d.%m.%Y"),
            "total_sum": total_daily_sum,
            "trips": summary_list
        }