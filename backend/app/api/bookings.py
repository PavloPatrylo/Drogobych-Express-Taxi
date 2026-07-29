from fastapi import APIRouter, HTTPException
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from datetime import datetime, timezone, timedelta

from app.db.database import async_session_maker
from app.db.models import Trip, Booking, User, BookingType, BookingSource, BookingStatus, Location
from app.schemas.booking import BookingCreate, BookingRead, BookingStatusUpdate, StandingBookingCreate, ParcelBookingCreate
from app.services.admin_use_cases import refresh_user_stats

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

# Оновлена перевірка статусу
        current_status = trip.status.name if hasattr(trip.status, 'name') else str(trip.status)
        
        # Тепер дозволяємо SCHEDULED та BOARDING
        if current_status not in ["SCHEDULED", "BOARDING"]:
            raise HTTPException(
                status_code=400, 
                detail="Бронювання неможливе: рейс вже вирушив або завершений."
            )



        # 5. Створюємо окремі бронювання для кожного місця (Згідно з логікою 1 квиток = 1 місце)
        for _ in range(booking_in.requested_seats):
            new_booking = Booking(
                trip_id=trip.id,
                passenger_id=user.id,
                created_by_id=user.id, # Пасажир сам створив запис
                booking_type=BookingType.SEATED,
                source=BookingSource.BOT,
                status=BookingStatus.RESERVED,
                passengers_count=1,            # 👈 ЗАВЖДИ 1 місце на один квиток
                amount_paid=trip.price_seated  # 👈 Ціна вказується за 1 місце
            )
            session.add(new_booking)
        
        # 6. Зберігаємо всі квитки разом (транзакція)
        try:
            await session.commit()
            return {"message": f"Успішно заброньовано {booking_in.requested_seats} місць!"}
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
        if booking.passenger_id:
            await refresh_user_stats(session, booking.passenger_id)
        await session.commit()
        
        return {"message": "Бронювання успішно скасовано"}
    


# === ОНОВЛЕННЯ СТАТУСУ КВИТКА (UC-D5) ===
@router.patch("/{booking_id}/status")
async def update_booking_status(booking_id: int, payload: BookingStatusUpdate):
    async with async_session_maker() as session:
        # Шукаємо конкретний квиток
        stmt = select(Booking).where(Booking.id == booking_id)
        booking = (await session.execute(stmt)).scalar_one_or_none()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Квиток не знайдено")

        # Перевіряємо статус рейсу: якщо COMPLETED або CLOSED - редагування заборонено
        trip = await session.get(Trip, booking.trip_id)
        if trip:
            t_status = trip.status.name if hasattr(trip.status, 'name') else str(trip.status)
            if t_status.upper() in ["COMPLETED", "CLOSED"]:
                raise HTTPException(
                    status_code=400,
                    detail="Зміна посадки неможлива: рейс вже завершений або закритий фінансово."
                )

        # Оновлюємо статус (Додано RESERVED для скасування випадкової посадки)
        if payload.status == "BOARDED":
            booking.status = BookingStatus.BOARDED
        elif payload.status == "NOSHOW":
            booking.status = BookingStatus.NOSHOW
        elif payload.status == "RESERVED":
            booking.status = BookingStatus.RESERVED
        else:
            raise HTTPException(status_code=400, detail="Недійсний статус")

        if booking.passenger_id:
            await refresh_user_stats(session, booking.passenger_id)

        await session.commit()
        return {"message": f"Статус квитка оновлено на {payload.status}"}


# === ШВИДКИЙ ПРОДАЖ СТОЯЧОГО МІСЦЯ (UC-D3) - БРОНЕБІЙНИЙ ВАРІАНТ ===
# === ШВИДКИЙ ПРОДАЖ СТОЯЧОГО МІСЦЯ (UC-D3) - ОЧИЩЕНИЙ ВАРІАНТ ===
@router.post("/standing")
async def add_standing_passenger(payload: StandingBookingCreate):
    async with async_session_maker() as session:
        # 1. Знаходимо водія
        user_stmt = select(User).where(User.telegram_id == payload.telegram_id)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        
        if not driver:
            raise HTTPException(status_code=403, detail="Водія не знайдено")
            
        driver_role = driver.role.name if hasattr(driver.role, 'name') else str(driver.role)
        if driver_role.upper() != "DRIVER":
            raise HTTPException(status_code=403, detail="Ви не водій")

        # 2. Блокуємо рейс (SELECT FOR UPDATE)
        trip_stmt = select(Trip).where(Trip.id == payload.trip_id).with_for_update()
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        
        if not trip:
            raise HTTPException(status_code=404, detail="Рейс не знайдено")
        if trip.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Це не ваш рейс")

        # 3. Перевіряємо статус рейсу
        current_status = trip.status.name if hasattr(trip.status, 'name') else str(trip.status)
        if current_status not in ["BOARDING", "ACTIVE"]:
            raise HTTPException(status_code=400, detail="Додавати стоячих можна лише під час посадки або в дорозі")

        # 4. Перевіряємо ліміт стоячих місць
        standing_type = BookingType.STANDING if hasattr(BookingType, 'STANDING') else "STANDING"
        
        result = await session.execute(
            select(func.sum(Booking.passengers_count))
            .where(Booking.trip_id == trip.id)
            .where(Booking.booking_type == standing_type)
            .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
        )
        booked_standing = result.scalar() or 0
        
        standing_limit = getattr(trip, 'standing_limit_snapshot', 10)
        
        if booked_standing >= standing_limit:
            raise HTTPException(status_code=400, detail="Ліміт стоячих вичерпано")

        # 5. Створюємо запис
        price = getattr(trip, 'price_standing', getattr(trip, 'price_seated', 0))
        source_val = BookingSource.DRIVER if hasattr(BookingSource, 'DRIVER') else "DRIVER"

        new_booking = Booking(
            trip_id=trip.id,
            passenger_id=None,
            created_by_id=driver.id,
            validated_by_id=driver.id,
            validated_at=datetime.now(timezone.utc),
            booking_type=standing_type,
            source=source_val,
            status=BookingStatus.BOARDED,
            passengers_count=1,
            amount_paid=price 
        )
        
        session.add(new_booking)
        await session.commit()
        
        return {"message": "Стоячий пасажир додано"}
    
# === ДОДАВАННЯ ПОСИЛКИ (UC-D4) ===
@router.post("/parcel")
async def add_parcel(payload: ParcelBookingCreate):
    async with async_session_maker() as session:
        # 1. Знаходимо водія
        user_stmt = select(User).where(User.telegram_id == payload.telegram_id)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        
        if not driver:
            raise HTTPException(status_code=403, detail="Водія не знайдено")

        # 2. Перевіряємо рейс
        trip_stmt = select(Trip).where(Trip.id == payload.trip_id)
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        
        if not trip:
            raise HTTPException(status_code=404, detail="Рейс не знайдено")
        if trip.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Це не ваш рейс")

        # 3. Створюємо запис посилки
        parcel_type = BookingType.PARCEL if hasattr(BookingType, 'PARCEL') else "PARCEL"
        source_val = BookingSource.DRIVER if hasattr(BookingSource, 'DRIVER') else "DRIVER"

        new_booking = Booking(
            trip_id=trip.id,
            passenger_id=None,
            created_by_id=driver.id,
            validated_by_id=driver.id,
            validated_at=datetime.now(timezone.utc),
            booking_type=parcel_type,
            source=source_val,
            status=BookingStatus.BOARDED,  # Посилка відразу вважається прийнятою
            passengers_count=1,            # 1 посилка = 1 одиниця
            amount_paid=payload.price,
            comment=payload.description    # Якщо в БД є поле comment. Якщо ні - просто видали цей рядок
        )
        
        session.add(new_booking)
        await session.commit()
        
        return {"message": "Посилку додано"}
    
# === СКАСУВАННЯ ШВИДКОГО ПРОДАЖУ (UC-D7) ===
@router.delete("/{booking_id}/quick-sale")
async def cancel_quick_sale(booking_id: int, telegram_id: int):
    async with async_session_maker() as session:
        # Перевіряємо водія
        user_stmt = select(User).where(User.telegram_id == telegram_id)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        if not driver:
            raise HTTPException(status_code=403, detail="Доступ заборонено")

        # Знаходимо бронювання
        stmt = select(Booking, Trip).join(Trip, Booking.trip_id == Trip.id).where(Booking.id == booking_id)
        result = (await session.execute(stmt)).first()
        if not result:
            raise HTTPException(status_code=404, detail="Запис не знайдено")
            
        booking, trip = result

        # Перевіряємо, чи це рейс цього водія і чи це швидкий продаж
        if trip.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Це не ваш рейс")
            
        booking_type_str = booking.booking_type.name if hasattr(booking.booking_type, 'name') else str(booking.booking_type)
        if booking_type_str not in ["STANDING", "PARCEL"]:
            raise HTTPException(status_code=400, detail="Можна скасовувати лише стоячих та посилки")

        t_status = trip.status.name if hasattr(trip.status, 'name') else str(trip.status)
        if t_status.upper() in ["COMPLETED", "CLOSED"]:
            raise HTTPException(status_code=400, detail="Неможливо видалити запис: рейс вже завершений або закрито фінансово.")

        # Видаляємо запис повністю (або ставимо статус CANCELLED)
        await session.delete(booking)
        await session.commit()
        
        return {"message": "Запис успішно видалено"}
    

# === ШВИДКИЙ ПРОДАЖ СИДЯЧОГО МІСЦЯ (ОФЛАЙН) ===
@router.post("/seated")
async def add_seated_passenger(payload: StandingBookingCreate):
    async with async_session_maker() as session:
        # 1. Знаходимо водія
        user_stmt = select(User).where(User.telegram_id == payload.telegram_id)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        if not driver or driver.role.name.upper() != "DRIVER":
            raise HTTPException(status_code=403, detail="Ви не водій")

        # 2. Блокуємо рейс
        trip_stmt = select(Trip).where(Trip.id == payload.trip_id).with_for_update()
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        if not trip or trip.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Це не ваш рейс")

        # 3. Перевіряємо статус
        current_status = trip.status.name if hasattr(trip.status, 'name') else str(trip.status)
        if current_status not in ["BOARDING", "ACTIVE"]:
            raise HTTPException(status_code=400, detail="Додавати пасажирів можна лише під час посадки або в дорозі")

        # 4. Перевіряємо, чи Є вільні сидячі місця
        seated_type = BookingType.SEATED if hasattr(BookingType, 'SEATED') else "SEATED"
        result = await session.execute(
            select(func.sum(Booking.passengers_count))
            .where(Booking.trip_id == trip.id)
            .where(Booking.booking_type == seated_type)
            .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
        )
        booked_seated = result.scalar() or 0
        available_seats = getattr(trip, 'seats_limit_snapshot', 0) - booked_seated
        
        if available_seats <= 0:
            raise HTTPException(status_code=400, detail="Вільних сидячих місць більше немає")

        # 5. Створюємо запис
        price = getattr(trip, 'price_seated', 0)
        source_val = BookingSource.DRIVER if hasattr(BookingSource, 'DRIVER') else "DRIVER"

        new_booking = Booking(
            trip_id=trip.id,
            passenger_id=None,
            created_by_id=driver.id,
            validated_by_id=driver.id,
            validated_at=datetime.now(timezone.utc),
            booking_type=seated_type,
            source=source_val,
            status=BookingStatus.BOARDED,
            passengers_count=1,
            amount_paid=price 
        )
        
        session.add(new_booking)
        await session.commit()
        return {"message": "Сидячого пасажира додано"}


# === ШВИДКИЙ ПРОДАЖ СТОЯЧОГО МІСЦЯ ===
@router.post("/standing")
async def add_standing_passenger(payload: StandingBookingCreate):
    async with async_session_maker() as session:
        user_stmt = select(User).where(User.telegram_id == payload.telegram_id)
        driver = (await session.execute(user_stmt)).scalar_one_or_none()
        if not driver or driver.role.name.upper() != "DRIVER":
            raise HTTPException(status_code=403, detail="Ви не водій")

        trip_stmt = select(Trip).where(Trip.id == payload.trip_id).with_for_update()
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        if not trip or trip.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Це не ваш рейс")

        current_status = trip.status.name if hasattr(trip.status, 'name') else str(trip.status)
        if current_status not in ["BOARDING", "ACTIVE"]:
            raise HTTPException(status_code=400, detail="Додавати стоячих можна лише під час посадки або в дорозі")

        # НОВА БІЗНЕС-ЛОГІКА: Перевіряємо, чи закінчилися сидячі місця
        seated_type = BookingType.SEATED if hasattr(BookingType, 'SEATED') else "SEATED"
        seated_result = await session.execute(
            select(func.sum(Booking.passengers_count))
            .where(Booking.trip_id == trip.id)
            .where(Booking.booking_type == seated_type)
            .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
        )
        booked_seated = seated_result.scalar() or 0
        if (trip.seats_limit_snapshot - booked_seated) > 0:
            raise HTTPException(status_code=400, detail="Не можна додати стоячого, поки є вільні сидячі місця!")

        # Перевіряємо ліміт стоячих місць
        standing_type = BookingType.STANDING if hasattr(BookingType, 'STANDING') else "STANDING"
        standing_result = await session.execute(
            select(func.sum(Booking.passengers_count))
            .where(Booking.trip_id == trip.id)
            .where(Booking.booking_type == standing_type)
            .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
        )
        booked_standing = standing_result.scalar() or 0
        if booked_standing >= trip.standing_limit_snapshot:
            raise HTTPException(status_code=400, detail="Ліміт стоячих вичерпано")

        price = getattr(trip, 'price_standing', getattr(trip, 'price_seated', 0))
        source_val = BookingSource.DRIVER if hasattr(BookingSource, 'DRIVER') else "DRIVER"

        new_booking = Booking(
            trip_id=trip.id,
            passenger_id=None,
            created_by_id=driver.id,
            validated_by_id=driver.id,
            validated_at=datetime.now(timezone.utc),
            booking_type=standing_type,
            source=source_val,
            status=BookingStatus.BOARDED,
            passengers_count=1,
            amount_paid=price 
        )
        
        session.add(new_booking)
        await session.commit()
        return {"message": "Стоячий пасажир додано"}