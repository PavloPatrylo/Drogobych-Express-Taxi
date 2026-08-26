from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased, selectinload
from datetime import datetime, timezone, timedelta

from app.api.deps import get_current_user, get_current_driver
from app.db.database import async_session_maker
from app.db.models import Trip, Booking, User, UserRole, BookingType, BookingSource, BookingStatus, Location, PaymentMethod
from app.schemas.booking import BookingCreate, BookingRead, BookingStatusUpdate, StandingBookingCreate, ParcelBookingCreate
from app.services.admin_use_cases import refresh_user_stats, promote_waitlist_bookings_use_case, _get_system_config
from app.websocket_manager import manager

router = APIRouter(prefix="/bookings", tags=["Bookings"])

@router.post("/")
async def create_booking(
    booking_in: BookingCreate,
    current_user: User = Depends(get_current_user)
):
    async with async_session_maker() as session:
        user = current_user

        # 2. Починаємо транзакцію і БЛОКУЄМО рядок рейсу (захист від Race Condition)
        # with_for_update() - це і є той самий SELECT ... FOR UPDATE з SRS
        trip_stmt = select(Trip).options(selectinload(Trip.driver)).where(Trip.id == booking_in.trip_id).with_for_update()
        trip_result = await session.execute(trip_stmt)
        trip = trip_result.scalar_one_or_none()

        if not trip or (trip.driver and not trip.driver.is_active):
            raise HTTPException(status_code=404, detail="Рейс не знайдено")

        # Перевірка: чи не виїхав рейс раніше поточного часу
        now_kyiv = datetime.now(timezone.utc)
        dep_time = trip.departure_time.replace(tzinfo=timezone.utc) if (trip.departure_time and trip.departure_time.tzinfo is None) else trip.departure_time
        if dep_time and dep_time < now_kyiv:
            raise HTTPException(status_code=400, detail="Цей рейс вже виїхав. Бронювання минулих рейсів неможливе!")

        # 3. Рахуємо вже зайняті місця (сидячі та стоячі)
        booked_seated_stmt = (
            select(func.sum(Booking.passengers_count))
            .where(Booking.trip_id == trip.id)
            .where(Booking.booking_type == BookingType.SEATED)
            .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
        )
        booked_seated_result = await session.execute(booked_seated_stmt)
        booked_seats = booked_seated_result.scalar() or 0
        available_seats = max(0, trip.seats_limit_snapshot - booked_seats)

        booked_standing_stmt = (
            select(func.sum(Booking.passengers_count))
            .where(Booking.trip_id == trip.id)
            .where(Booking.booking_type == BookingType.STANDING)
            .where(Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.BOARDED]))
        )
        booked_standing_result = await session.execute(booked_standing_stmt)
        booked_standing = booked_standing_result.scalar() or 0
        available_standing = max(0, (trip.standing_limit_snapshot or 0) - booked_standing)

        # 4. Інтерактивна логіка: Сидяче -> Запит підтвердження на Стояче / Waitlist -> Waitlist
        total_vehicle_capacity = trip.seats_limit_snapshot + (trip.standing_limit_snapshot or 0)
        pref_type = str(getattr(booking_in, "preferred_type", "SEATED") or "SEATED").upper()

        if booking_in.requested_seats > total_vehicle_capacity:
            raise HTTPException(
                status_code=400,
                detail=f"Кількість місць у замовленні ({booking_in.requested_seats}) перевищує місткість авто ({total_vehicle_capacity})."
            )

        if pref_type == "STANDING":
            if available_standing >= booking_in.requested_seats:
                target_type = BookingType.STANDING
                target_status = BookingStatus.RESERVED
                price_per_ticket = float(trip.price_standing)
                message_text = f"Успішно заброньовано {booking_in.requested_seats} стоячих місць!"
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"На жаль, стоячі місця щойно закінчилися. Доступно: {available_standing} стоячих місць."
                )
        elif pref_type == "WAITLIST":
            target_type = BookingType.SEATED
            target_status = BookingStatus.WAITLIST
            price_per_ticket = 0.0
            message_text = f"Успішно додано у Список очікування (Waitlist) на {booking_in.requested_seats} місць!"
        else: # Default: "SEATED"
            if available_seats >= booking_in.requested_seats:
                target_type = BookingType.SEATED
                target_status = BookingStatus.RESERVED
                price_per_ticket = float(trip.price_seated)
                message_text = f"Успішно заброньовано {booking_in.requested_seats} місць!"
            elif available_standing >= booking_in.requested_seats:
                # Сидячі місця закінчилися, але є стоячі: даємо вибір пасажиру
                raise HTTPException(
                    status_code=409,
                    detail=f"Сидячі місця щойно закінчилися. Доступно {available_standing} стоячих місць. Оберіть 'STANDING' для бронювання стоячого місця або 'WAITLIST' для запису в чергу."
                )
            elif available_seats == 0 and available_standing == 0 and booking_in.requested_seats <= total_vehicle_capacity:
                # Усі місця викуплені: даємо можливість увійти в Waitlist
                raise HTTPException(
                    status_code=409,
                    detail=f"Усі місця щойно закінчилися. Оберіть 'WAITLIST' для запису в чергу очікування."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"На жаль, місця щойно закінчилися. Доступно: {available_seats} сидячих, {available_standing} стоячих."
                )

        # Перевірка статусу рейсу
        current_status = trip.status.name if hasattr(trip.status, 'name') else str(trip.status)
        
        if current_status not in ["SCHEDULED", "BOARDING"]:
            raise HTTPException(
                status_code=400, 
                detail="Бронювання неможливе: рейс вже вирушив або завершений."
            )

        pm_val = str(getattr(booking_in, "payment_method", "CASH") or "CASH").upper()
        pm = PaymentMethod.CARD if pm_val == "CARD" else PaymentMethod.CASH

        # 5. Створюємо окремі квитки
        for _ in range(booking_in.requested_seats):
            new_booking = Booking(
                trip_id=trip.id,
                passenger_id=user.id,
                created_by_id=user.id,
                booking_type=target_type,
                source=BookingSource.BOT,
                status=target_status,
                payment_method=pm,
                passengers_count=1,
                amount_paid=price_per_ticket
            )
            session.add(new_booking)
        
        # 6. Зберігаємо всі квитки разом (транзакція)
        try:
            await session.commit()
            await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip.id})
            return {"message": message_text}
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=500, detail="Помилка бази даних при бронюванні")
        
# === 1. ОТРИМАТИ МОЇ КВИТКИ (UC-P4) ===
@router.get("/my", response_model=list[BookingRead])
async def get_my_bookings(current_user: User = Depends(get_current_user)):
    async with async_session_maker() as session:
        FromLoc = aliased(Location)
        ToLoc = aliased(Location)

        stmt = (
            select(Booking, Trip, FromLoc, ToLoc)
            .join(Trip, Booking.trip_id == Trip.id)
            .join(FromLoc, Trip.from_location_id == FromLoc.id)
            .join(ToLoc, Trip.to_location_id == ToLoc.id)
            .where(Booking.passenger_id == current_user.id)
            .order_by(Booking.created_at.desc())
        )
        
        result = await session.execute(stmt)
        rows = result.all()

        response = []
        for booking, trip, from_loc, to_loc in rows:
            pos = None
            if booking.status == BookingStatus.WAITLIST:
                pos_stmt = (
                    select(func.count(Booking.id))
                    .where(Booking.trip_id == booking.trip_id)
                    .where(Booking.status == BookingStatus.WAITLIST)
                    .where(Booking.created_at <= booking.created_at)
                )
                pos = (await session.execute(pos_stmt)).scalar() or 1

            response.append(BookingRead(
                id=booking.id,
                status=booking.status.value,
                passengers_count=booking.passengers_count,
                amount_paid=float(booking.amount_paid),
                payment_method=booking.payment_method.value if hasattr(booking.payment_method, "value") else str(booking.payment_method),
                trip_departure_time=trip.departure_time,
                from_location=from_loc.name,
                to_location=to_loc.name,
                waitlist_position=pos,
            ))
            
        return response


@router.get("/my/{telegram_id}", response_model=list[BookingRead])
async def get_my_bookings_by_telegram_id(
    telegram_id: int,
    current_user: User = Depends(get_current_user)
):
    if current_user.telegram_id != telegram_id and current_user.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
        raise HTTPException(status_code=403, detail="Немає доступу до квитків іншого користувача")
    return await get_my_bookings(current_user=current_user)


# === 2. СКАСУВАТИ КВИТОК (UC-P5) ===
@router.patch("/{booking_id}/cancel")
async def cancel_booking(
    booking_id: int,
    telegram_id: int | None = None,
    current_user: User = Depends(get_current_user)
):
    async with async_session_maker() as session:
        # Шукаємо квиток та рейс
        stmt = select(Booking, Trip).join(Trip, Booking.trip_id == Trip.id).where(Booking.id == booking_id)
        result = (await session.execute(stmt)).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Квиток не знайдено")
            
        booking, trip = result

        # Перевіряємо об'єктний доступ
        if booking.passenger_id != current_user.id and current_user.role not in (UserRole.ADMIN, UserRole.DISPATCHER):
            raise HTTPException(status_code=403, detail="Це не ваш квиток")

        # Перевіряємо статус
        if booking.status not in [BookingStatus.RESERVED, BookingStatus.PAID, BookingStatus.WAITLIST]:
            raise HTTPException(status_code=400, detail="Цей квиток вже не можна скасувати")

        # Скасовуємо у будь-який момент для активного бронювання
        booking.status = BookingStatus.CANCELLED
        if booking.passenger_id:
            await refresh_user_stats(session, booking.passenger_id)
        await session.commit()
        await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip.id})
        
        # Автоматично просуваємо найпершого пасажира зі списку очікування (Waitlist)
        await promote_waitlist_bookings_use_case(session, trip.id)

        return {"message": "Бронювання успішно скасовано"}
    


# === ОНОВЛЕННЯ СТАТУСУ КВИТКА (UC-D5) ===
@router.patch("/{booking_id}/status")
async def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    current_user: User = Depends(get_current_driver),
):
    async with async_session_maker() as session:
        # Шукаємо конкретний квиток
        stmt = select(Booking).where(Booking.id == booking_id)
        booking = (await session.execute(stmt)).scalar_one_or_none()
        
        if not booking:
            raise HTTPException(status_code=404, detail="Квиток не знайдено")

        # Перевіряємо статус рейсу: якщо COMPLETED або CLOSED - редагування заборонено
        trip = await session.get(Trip, booking.trip_id)
        if not trip:
            raise HTTPException(status_code=404, detail="Trip not found")
        if current_user.role == UserRole.DRIVER and trip.driver_id != current_user.id:
            raise HTTPException(status_code=403, detail="This is not your trip")
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
        await manager.broadcast("BOOKING_MUTATED", {"trip_id": booking.trip_id})
        return {"message": f"Статус квитка оновлено на {payload.status}"}


# === ШВИДКИЙ ПРОДАЖ СТОЯЧОГО МІСЦЯ (UC-D3) - БРОНЕБІЙНИЙ ВАРІАНТ ===
# === ШВИДКИЙ ПРОДАЖ СТОЯЧОГО МІСЦЯ (UC-D3) - ОЧИЩЕНИЙ ВАРІАНТ ===
@router.post("/standing")
async def add_standing_passenger(
    payload: StandingBookingCreate,
    current_user: User = Depends(get_current_driver)
):
    async with async_session_maker() as session:
        driver = current_user

        # 2. Блокуємо рейс (SELECT FOR UPDATE)
        trip_stmt = select(Trip).where(Trip.id == payload.trip_id).with_for_update()
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        
        if not trip:
            raise HTTPException(status_code=404, detail="Рейс не знайдено")
        if current_user.role == UserRole.DRIVER and trip.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Це не ваш рейс")

        # 3. Перевіряємо статус рейсу
        current_status = trip.status.name if hasattr(trip.status, 'name') else str(trip.status)
        if current_status not in ["BOARDING", "ACTIVE"]:
            raise HTTPException(status_code=400, detail="Додавати стоячих можна лише під час посадки або в дорозі")

        # 4. Перевіряємо, чи є вільні сидячі місця
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
        await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip.id})
        
        return {"message": "Стоячий пасажир додано"}
    
# === ДОДАВАННЯ ПОСИЛКИ (UC-D4) ===
@router.post("/parcel")
async def add_parcel(
    payload: ParcelBookingCreate,
    current_user: User = Depends(get_current_driver)
):
    async with async_session_maker() as session:
        driver = current_user

        # 2. Перевіряємо рейс
        trip_stmt = select(Trip).where(Trip.id == payload.trip_id)
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        
        if not trip:
            raise HTTPException(status_code=404, detail="Рейс не знайдено")
        if current_user.role == UserRole.DRIVER and trip.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Це не ваш рейс")

        # 3. Створюємо запис посилки
        parcel_type = BookingType.PARCEL if hasattr(BookingType, 'PARCEL') else "PARCEL"
        source_val = BookingSource.DRIVER if hasattr(BookingSource, 'DRIVER') else "DRIVER"

        if payload.price and payload.price > 0:
            parcel_price = float(payload.price)
        elif trip.price_parcel is not None:
            parcel_price = float(trip.price_parcel)
        else:
            sys_cfg = await _get_system_config(session)
            parcel_price = float(sys_cfg.price_parcel)

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
            amount_paid=parcel_price,
            comment=payload.description    # Якщо в БД є поле comment. Якщо ні - просто видали цей рядок
        )
        
        session.add(new_booking)
        await session.commit()
        await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip.id})
        
        return {"message": "Посилку додано"}
    
# === СКАСУВАННЯ ШВИДКОГО ПРОДАЖУ (UC-D7) ===
@router.delete("/{booking_id}/quick-sale")
async def cancel_quick_sale(
    booking_id: int,
    current_user: User = Depends(get_current_driver),
):
    async with async_session_maker() as session:
        # Перевіряємо водія
        driver = current_user

        # Знаходимо бронювання
        stmt = select(Booking, Trip).join(Trip, Booking.trip_id == Trip.id).where(Booking.id == booking_id)
        result = (await session.execute(stmt)).first()
        if not result:
            raise HTTPException(status_code=404, detail="Запис не знайдено")
            
        booking, trip = result

        # Перевіряємо, чи це рейс цього водія і чи це швидкий продаж
        if driver.role == UserRole.DRIVER and trip.driver_id != driver.id:
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
        await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip.id})
        
        return {"message": "Запис успішно видалено"}
    

# === ШВИДКИЙ ПРОДАЖ СИДЯЧОГО МІСЦЯ (ОФЛАЙН) ===
@router.post("/seated")
async def add_seated_passenger(
    payload: StandingBookingCreate,
    current_user: User = Depends(get_current_driver),
):
    async with async_session_maker() as session:
        # 1. Знаходимо водія
        driver = current_user

        # 2. Блокуємо рейс
        trip_stmt = select(Trip).where(Trip.id == payload.trip_id).with_for_update()
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        if not trip or (driver.role == UserRole.DRIVER and trip.driver_id != driver.id):
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
        await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip.id})
        return {"message": "Сидячого пасажира додано"}


# === ШВИДКИЙ ПРОДАЖ СТОЯЧОГО МІСЦЯ ===
@router.post("/standing")
async def add_standing_passenger(
    payload: StandingBookingCreate,
    current_user: User = Depends(get_current_driver),
):
    async with async_session_maker() as session:
        driver = current_user

        trip_stmt = select(Trip).where(Trip.id == payload.trip_id).with_for_update()
        trip = (await session.execute(trip_stmt)).scalar_one_or_none()
        if not trip or (driver.role == UserRole.DRIVER and trip.driver_id != driver.id):
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
        await manager.broadcast("BOOKING_MUTATED", {"trip_id": trip.id})
        return {"message": "Стоячий пасажир додано"}
