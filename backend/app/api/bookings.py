from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from datetime import datetime, timezone, timedelta

from app.db.database import async_session_maker
from app.db.models import Trip, Booking, User, BookingType, BookingSource, BookingStatus, Location
from app.schemas.booking import BookingCreate, BookingRead

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("/")
async def create_booking(booking_in: BookingCreate):
    async with async_session_maker() as session:
        # 1. Знаходимо пасажира за telegram_id
        user_stmt = select(User).where(User.telegram_id == booking_in.telegram_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="Користувача не знайдено")

        # 2. Починаємо транзакцію і БЛОКУЄМО рядок рейсу (захист від Race Condition)
        # with_for_update() - це і є той самий SELECT ... FOR UPDATE з SRS
        trip_stmt = select(Trip).where(Trip.id == booking_in.trip_id).with_for_update()
        trip_result = await session.execute(trip_stmt)
        trip = trip_result.scalar_one_or_none()

        if not trip:
            raise HTTPException(status_code=404, detail="Рейс не знайдено")

        # 3. Рахуємо вже зайняті місця
        booked_stmt = (
            select(func.sum(Booking.passengers_count))
            .where(Booking.trip_id == trip.id)
            .where(Booking.booking_type == BookingType.SEATED)
            .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
        )
        booked_result = await session.execute(booked_stmt)
        booked_seats = booked_result.scalar() or 0

        # 4. Перевіряємо, чи вистачає місць
        available_seats = trip.seats_limit_snapshot - booked_seats
        
        if available_seats < booking_in.requested_seats:
            raise HTTPException(
                status_code=400, 
                detail=f"На жаль, місця щойно закінчилися. Доступно: {available_seats}"
            )

        # 5. Створюємо бронювання
        new_booking = Booking(
            trip_id=trip.id,
            passenger_id=user.id,
            created_by_id=user.id, # Пасажир сам створив запис
            booking_type=BookingType.SEATED,
            source=BookingSource.BOT,
            status=BookingStatus.RESERVED,
            passengers_count=booking_in.requested_seats,
            amount_paid=trip.price_seated * booking_in.requested_seats
        )
        
        session.add(new_booking)
        
        # 6. Зберігаємо зміни
        try:
            await session.commit()
            return {"message": "Бронювання успішне!", "booking_id": new_booking.id}
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=500, detail="Помилка бази даних при бронюванні")
        
# === 1. ОТРИМАТИ МОЇ КВИТКИ (UC-P4) ===
@router.get("/my/{telegram_id}", response_model=list[BookingRead])
async def get_my_bookings(telegram_id: int):
    async with async_session_maker() as session:
        # Шукаємо користувача
        user_stmt = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Користувача не знайдено")

        # Оскільки ми не прописували relationship між Booking і Trip у models.py, 
        # ми об'єднаємо таблиці (JOIN) прямо тут, щоб дістати назви міст і час.
        FromLoc = aliased(Location)
        ToLoc = aliased(Location)

        stmt = (
            select(Booking, Trip, FromLoc, ToLoc)
            .join(Trip, Booking.trip_id == Trip.id)
            .join(FromLoc, Trip.from_location_id == FromLoc.id)
            .join(ToLoc, Trip.to_location_id == ToLoc.id)
            .where(Booking.passenger_id == user.id)
            .order_by(Booking.created_at.desc())
        )
        
        result = await session.execute(stmt)
        rows = result.all()

        response = []
        for booking, trip, from_loc, to_loc in rows:
            response.append(BookingRead(
                id=booking.id,
                status=booking.status.value,
                passengers_count=booking.passengers_count,
                amount_paid=float(booking.amount_paid),
                trip_departure_time=trip.departure_time,
                from_location=from_loc.name,
                to_location=to_loc.name
            ))
            
        return response


# === 2. СКАСУВАТИ КВИТОК (UC-P5) ===
@router.patch("/{booking_id}/cancel")
async def cancel_booking(booking_id: int, telegram_id: int):
    async with async_session_maker() as session:
        # Шукаємо квиток та рейс
        stmt = select(Booking, Trip).join(Trip, Booking.trip_id == Trip.id).where(Booking.id == booking_id)
        result = (await session.execute(stmt)).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Квиток не знайдено")
            
        booking, trip = result

        # Перевіряємо, чи це квиток саме цього користувача
        user_stmt = select(User).where(User.telegram_id == telegram_id)
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not user or booking.passenger_id != user.id:
            raise HTTPException(status_code=403, detail="Це не ваш квиток")

        # Перевіряємо статус
        if booking.status not in [BookingStatus.RESERVED, BookingStatus.PAID]:
            raise HTTPException(status_code=400, detail="Цей квиток вже не можна скасувати")

        # ПЕРЕВІРКА ПРАВИЛА 2 ГОДИН (UC-P5)
        now = datetime.now(timezone.utc)
        time_left = trip.departure_time - now
        
        if time_left < timedelta(hours=2):
            raise HTTPException(
                status_code=400, 
                detail="Скасування неможливе — до відправлення залишилося менше 2 годин. Зверніться до диспетчера."
            )

        # Скасовуємо
        booking.status = BookingStatus.CANCELLED
        await session.commit()
        
        return {"message": "Бронювання успішно скасовано"}