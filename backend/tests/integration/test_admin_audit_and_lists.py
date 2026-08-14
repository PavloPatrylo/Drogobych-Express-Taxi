import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole, AuditLog, Trip, Booking, BookingStatus, BookingType, BookingSource, PaymentMethod
from app.services.admin_use_cases import (
    record_audit_log,
    list_audit_logs,
    list_staff,
    list_passengers,
    list_trips,
    list_bookings,
    toggle_passenger,
    refresh_user_stats,
)


@pytest.mark.asyncio
async def test_audit_logs_record_and_list(db_session: AsyncSession, admin_user: User):
    record_audit_log(
        db_session,
        admin_user,
        action="TEST_ACTION",
        entity_type="user",
        entity_id=admin_user.id,
        message="Recorded test log",
    )
    await db_session.commit()

    logs = await list_audit_logs(db_session, limit=10)
    assert len(logs) >= 1
    assert logs[0].action == "TEST_ACTION"
    assert logs[0].by == admin_user.full_name


@pytest.mark.asyncio
async def test_list_staff_and_passengers(db_session: AsyncSession, admin_user: User, passenger_user: User):
    driver = User(phone="+380971112233", full_name="Driver Joe", role=UserRole.DRIVER, is_active=True)
    db_session.add(driver)
    await db_session.commit()

    staff_list = await list_staff(db_session)
    staff_ids = [s.id for s in staff_list]

    assert admin_user.id in staff_ids
    assert driver.id in staff_ids
    assert passenger_user.id not in staff_ids

    passengers_list = await list_passengers(db_session)
    passenger_ids = [p.id for p in passengers_list]

    assert passenger_user.id in passenger_ids
    assert admin_user.id not in passenger_ids


@pytest.mark.asyncio
async def test_list_trips_and_bookings(db_session: AsyncSession, sample_trip: Trip, passenger_user: User, admin_user: User):
    booking = Booking(
        trip_id=sample_trip.id,
        passenger_id=passenger_user.id,
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

    trips = await list_trips(db_session)
    assert len(trips) >= 1
    assert trips[0].id == sample_trip.id

    bookings = await list_bookings(db_session)
    assert len(bookings) >= 1
    assert bookings[0].id == booking.id


@pytest.mark.asyncio
async def test_toggle_passenger_status(db_session: AsyncSession, admin_user: User, passenger_user: User):
    assert passenger_user.is_active is True

    # Ensure user stats created to prevent lazy-load MissingGreenlet
    await refresh_user_stats(db_session, passenger_user.id)
    await db_session.commit()

    # Block passenger
    updated = await toggle_passenger(db_session, passenger_user.id, is_active=False, actor=admin_user)
    assert updated.is_active is False

    # Unblock passenger
    updated2 = await toggle_passenger(db_session, passenger_user.id, is_active=True, actor=admin_user)
    assert updated2.is_active is True


@pytest.mark.asyncio
async def test_toggle_passenger_forbidden_for_non_admin(db_session: AsyncSession, passenger_user: User):
    with pytest.raises(HTTPException) as exc_info:
        await toggle_passenger(db_session, passenger_user.id, is_active=False, actor=passenger_user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_toggle_passenger_not_found(db_session: AsyncSession, admin_user: User):
    with pytest.raises(HTTPException) as exc_info:
        await toggle_passenger(db_session, 999999, is_active=False, actor=admin_user)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
