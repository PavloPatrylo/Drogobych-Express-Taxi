from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import date, datetime, time
from typing import List

from app.db.database import async_session_maker
from app.db.models import Trip, Location, Booking, TripStatus, BookingStatus, BookingType
from app.schemas.trip import TripReadPassenger, LocationRead

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