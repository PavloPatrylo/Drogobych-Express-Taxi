from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import date, datetime, time
from typing import List

from app.db.database import async_session_maker
from app.db.models import Trip, Location, Booking, TripStatus, BookingStatus, BookingType
from app.schemas.trip import TripReadPassenger, LocationRead

from app.db.models import Booking, User, BookingStatus, UserRole
from app.schemas.booking import TripManifest

from sqlalchemy.orm import aliased

from app.db.models import Trip, Booking, User, BookingStatus, UserRole, Location

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
    
# === ОТРИМАТИ МАНІФЕСТ ДЛЯ ВОДІЯ (UC-D1) ===
@router.get("/driver/{telegram_id}/manifest", response_model=list[TripManifest])
async def get_driver_manifest(telegram_id: int):
    async with async_session_maker() as session:
        # 1. Перевіряємо, чи цей користувач дійсно водій
        user_stmt = select(User).where(User.telegram_id == telegram_id, User.role == UserRole.DRIVER)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        
        if not driver:
            raise HTTPException(status_code=403, detail="Доступ заборонено: Ви не водій")

        # 2. Шукаємо всі рейси, призначені цьому водію
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

        manifests = []
        for trip, from_name, to_name in trips_rows:
            # 3. Для кожного рейсу дістаємо список пасажирів (тільки активні броні)
            bookings_stmt = (
                select(Booking, User)
                .join(User, Booking.passenger_id == User.id)
                .where(Booking.trip_id == trip.id)
                .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
            )
            bookings_rows = (await session.execute(bookings_stmt)).all()

            passengers = []
            booked_seats_count = 0
            
            for booking, passenger in bookings_rows:
                booked_seats_count += booking.passengers_count
                passengers.append({
                    "booking_id": booking.id,
                    "full_name": passenger.full_name,
                    "phone": passenger.phone,
                    "seats": booking.passengers_count,
                    "status": booking.status.value,
                    "amount_paid": float(booking.amount_paid)
                })

            manifests.append({
                "trip_id": trip.id,
                "departure_time": trip.departure_time,
                "from_location": from_name,
                "to_location": to_name,
                "available_seats": trip.seats_limit_snapshot - booked_seats_count,
                "passengers": passengers
            })

        return manifests