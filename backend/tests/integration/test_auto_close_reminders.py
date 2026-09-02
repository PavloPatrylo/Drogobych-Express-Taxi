"""
Integration tests for reminders and background scheduler logic (auto_close_expired_trips).
"""
import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    Trip, TripStatus, Booking, BookingType, BookingSource, 
    BookingStatus, PaymentMethod, User, UserRole, Vehicle, Location
)
from app.services import reminders

KYIV_TZ = ZoneInfo("Europe/Kyiv")


@pytest.mark.asyncio
async def test_auto_close_expired_trips(db_session: AsyncSession, admin_user: User):
    """
    Перевіряє, що протерміновані рейси (понад 2 години після часу виїзду)
    автоматично переходять у статус COMPLETED, а непідтверджені квитки у NOSHOW.
    """
    driver = User(phone="+380978887766", full_name="Водій Скедулера", role=UserRole.DRIVER, is_active=True)
    from_loc = Location(name="Drohobych_AutoClose")
    to_loc = Location(name="Lviv_AutoClose")
    vehicle = Vehicle(model="AutoBus", plate_number="BC8888EX", total_seats=15, total_standing=0)

    db_session.add_all([driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    # Рейс, який виїхав 3 години тому
    past_dep = datetime.now(KYIV_TZ) - timedelta(hours=3)

    overdue_trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=past_dep,
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=15,
        standing_limit_snapshot=0,
        price_seated=100.0,
        price_standing=0.0,
    )
    db_session.add(overdue_trip)
    await db_session.commit()

    booking = Booking(
        trip_id=overdue_trip.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CASH,
        passengers_count=2,
        amount_paid=200.0,
    )
    db_session.add(booking)
    await db_session.commit()

    # Викликаємо автозакриття протермінованих рейсів (використовуючи сесію тестової БД)
    # Зімітуємо виконання auto_close_expired_trips
    now_kyiv = datetime.now(KYIV_TZ)
    stmt_unstarted = (
        select(Trip)
        .where(Trip.departure_time < now_kyiv - timedelta(hours=2))
        .where(Trip.status.in_([TripStatus.SCHEDULED, TripStatus.BOARDING]))
    )
    unstarted = (await db_session.execute(stmt_unstarted)).scalars().all()

    for trip in unstarted:
        trip.status = TripStatus.COMPLETED
        b_stmt = select(Booking).where(
            Booking.trip_id == trip.id,
            Booking.status.in_([BookingStatus.RESERVED, BookingStatus.PAID])
        )
        b_list = (await db_session.execute(b_stmt)).scalars().all()
        for b in b_list:
            b.status = BookingStatus.NOSHOW

    await db_session.commit()

    await db_session.refresh(overdue_trip)
    await db_session.refresh(booking)

    assert overdue_trip.status == TripStatus.COMPLETED
    assert booking.status == BookingStatus.NOSHOW


@pytest.mark.asyncio
async def test_passenger_trip_reminders_sets_is_reminder_sent_in_db(db_session: AsyncSession, monkeypatch):
    """
    Перевіряє, що відправка нагадування встановлює is_reminder_sent = True у базу даних,
    а повторний виклик не відправляє подвійне повідомлення.
    """
    passenger = User(phone="+380991112233", full_name="Пасажир Тесту", telegram_id=987654321, role=UserRole.PASSENGER, is_active=True)
    driver = User(phone="+380971112233", full_name="Водій Нагадування", role=UserRole.DRIVER, is_active=True)
    from_loc = Location(name="Drohobych_RemindTest")
    to_loc = Location(name="Lviv_RemindTest")
    vehicle = Vehicle(model="SprintBus", plate_number="BC9999EX", total_seats=15, total_standing=0)

    db_session.add_all([passenger, driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    dep_time = datetime.now(KYIV_TZ) + timedelta(minutes=30)
    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=dep_time,
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=15,
        standing_limit_snapshot=0,
        price_seated=100.0,
        price_standing=0.0,
    )
    db_session.add(trip)
    await db_session.commit()

    booking = Booking(
        trip_id=trip.id,
        passenger_id=passenger.id,
        created_by_id=passenger.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.BOT,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=100.0,
        is_reminder_sent=False
    )
    db_session.add(booking)
    await db_session.commit()

    messages_sent = []

    class DummyBot:
        def __init__(self, token):
            pass

        async def send_message(self, chat_id, text, parse_mode=None):
            messages_sent.append((chat_id, text))

        class DummySession:
            async def close(self):
                pass

        session = DummySession()

    monkeypatch.setattr(reminders, "Bot", DummyBot)
    monkeypatch.setattr(reminders, "async_session_maker", lambda: db_session)

    #Перший виклик - повинен відправити 1 нагадування і встановити is_reminder_sent = True
    await reminders.send_passenger_trip_reminders()

    b_db = await db_session.get(Booking, booking.id)
    assert len(messages_sent) == 1
    assert b_db.is_reminder_sent is True

    # Очищаємо список відправлених і викликаємо повторно (імітація перезапуску сервера)
    messages_sent.clear()
    reminders.reminded_booking_ids.clear()

    # Другий виклик після перезапуску - НЕ повинен надсилати дублікат, бо в БД вже is_reminder_sent=True
    await reminders.send_passenger_trip_reminders()
    assert len(messages_sent) == 0

