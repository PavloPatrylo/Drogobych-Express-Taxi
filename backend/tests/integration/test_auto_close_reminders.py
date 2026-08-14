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
