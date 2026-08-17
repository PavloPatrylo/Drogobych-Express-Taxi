import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    User,
    UserRole,
    Location,
    Vehicle,
    Trip,
    TripStatus,
    Booking,
    BookingStatus,
    BookingType,
    BookingSource,
    PaymentMethod,
)
from app.services.reminders import (
    send_passenger_trip_reminders,
    auto_close_expired_trips,
    reminded_booking_ids,
)

KYIV_TZ = ZoneInfo("Europe/Kyiv")


@pytest.mark.asyncio
async def test_auto_close_expired_trips(db_session: AsyncSession, admin_user: User):
    from_loc = Location(name="Drohobych")
    to_loc = Location(name="Lviv")
    vehicle = Vehicle(model="Sprinter", plate_number="BC1111EX", total_seats=18, total_standing=5)
    passenger = User(phone="+380971110000", full_name="Overdue Pass", role=UserRole.PASSENGER, telegram_id=12345, is_active=True)

    db_session.add_all([from_loc, to_loc, vehicle, passenger])
    await db_session.commit()

    now_kyiv = datetime.now(KYIV_TZ)
    # Trip departed 3 hours ago
    dep_time = now_kyiv - timedelta(hours=3)
    arr_time = dep_time + timedelta(hours=1, minutes=30)

    overdue_trip = Trip(
        departure_time=dep_time,
        arrival_time=arr_time,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        vehicle_id=vehicle.id,
        driver_id=admin_user.id,
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(overdue_trip)
    await db_session.commit()

    booking = Booking(
        trip_id=overdue_trip.id,
        passenger_id=passenger.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add(booking)
    await db_session.commit()

    # Patch async_session_maker in reminders to use db_session context manager
    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.services.reminders.async_session_maker", return_value=SessionContext()):
        with patch("app.services.reminders.manager.broadcast", new_callable=AsyncMock):
            await auto_close_expired_trips()

    await db_session.refresh(overdue_trip)
    await db_session.refresh(booking)

    assert overdue_trip.status == TripStatus.COMPLETED
    assert booking.status == BookingStatus.NOSHOW


@pytest.mark.asyncio
async def test_send_passenger_trip_reminders(db_session: AsyncSession, admin_user: User):
    from_loc = Location(name="Drohobych")
    to_loc = Location(name="Lviv")
    vehicle = Vehicle(model="Sprinter", plate_number="BC2222EX", total_seats=18, total_standing=5)
    passenger = User(phone="+380972220000", full_name="Reminder Pass", role=UserRole.PASSENGER, telegram_id=987654321, is_active=True)

    db_session.add_all([from_loc, to_loc, vehicle, passenger])
    await db_session.commit()

    now_kyiv = datetime.now(KYIV_TZ)
    dep_time = now_kyiv + timedelta(minutes=30)

    upcoming_trip = Trip(
        departure_time=dep_time,
        arrival_time=dep_time + timedelta(hours=1, minutes=30),
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        vehicle_id=vehicle.id,
        driver_id=admin_user.id,
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(upcoming_trip)
    await db_session.commit()

    booking = Booking(
        trip_id=upcoming_trip.id,
        passenger_id=passenger.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.BOT,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add(booking)
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()
    mock_bot.session = AsyncMock()
    mock_bot.session.close = AsyncMock()

    reminded_booking_ids.clear()

    with patch("app.services.reminders.async_session_maker", return_value=SessionContext()):
        with patch("app.services.reminders.Bot", return_value=mock_bot):
            await send_passenger_trip_reminders()

            # First run should send message
            assert mock_bot.send_message.called
            assert mock_bot.send_message.call_args[1]["chat_id"] == 987654321

            mock_bot.send_message.reset_mock()

            # Second run should skip already reminded booking
            await send_passenger_trip_reminders()
            assert not mock_bot.send_message.called
