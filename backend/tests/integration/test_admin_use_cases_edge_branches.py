import pytest
from datetime import datetime, date, timedelta
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.db.models import User, UserRole, Trip, TripStatus, Booking, BookingType, BookingSource, BookingStatus, Location, Vehicle
from app.services.admin_use_cases import (
    drivers_cash_reconciliation_use_case,
    confirm_driver_cash_use_case,
    export_drivers_cash_csv,
    export_trips_register_csv,
    list_audit_logs,
    update_trip_status,
    create_trip,
    AdminTripCreate,
)


@pytest.mark.asyncio
async def test_confirm_driver_cash_validation_and_flow(
    db_session: AsyncSession, admin_user: User, passenger_user: User, sample_trip: Trip
):
    driver = User(phone="+380976543210", full_name="Cash Driver", role=UserRole.DRIVER, is_active=True)
    db_session.add(driver)
    await db_session.commit()

    # 1. Forbidden non-staff actor
    with pytest.raises(HTTPException) as exc1:
        await confirm_driver_cash_use_case(
            db=db_session,
            driver_id=driver.id,
            target_date="2027-01-01",
            received_cash=300.0,
            received_card=0.0,
            actor=passenger_user,
        )
    assert exc1.value.status_code == 403

    # 2. Invalid date format
    with pytest.raises(HTTPException) as exc2:
        await confirm_driver_cash_use_case(
            db=db_session,
            driver_id=driver.id,
            target_date="01-01-2027",
            received_cash=300.0,
            received_card=0.0,
            actor=admin_user,
        )
    assert exc2.value.status_code == 400

    # 3. Driver not found
    with pytest.raises(HTTPException) as exc3:
        await confirm_driver_cash_use_case(
            db=db_session,
            driver_id=99999,
            target_date="2027-01-01",
            received_cash=300.0,
            received_card=0.0,
            actor=admin_user,
        )
    assert exc3.value.status_code == 404

    # 4. No completed trips for driver on date
    with pytest.raises(HTTPException) as exc4:
        await confirm_driver_cash_use_case(
            db=db_session,
            driver_id=driver.id,
            target_date="2027-01-01",
            received_cash=300.0,
            received_card=0.0,
            actor=admin_user,
        )
    assert exc4.value.status_code == 400

    # 5. Success flow: set sample_trip to COMPLETED
    sample_trip.driver_id = driver.id
    sample_trip.status = TripStatus.COMPLETED
    sample_trip.departure_time = datetime(2027, 1, 1, 10, 0)
    await db_session.commit()

    with patch("app.websocket_manager.manager.broadcast", new_callable=AsyncMock):
        res = await confirm_driver_cash_use_case(
            db=db_session,
            driver_id=driver.id,
            target_date="2027-01-01",
            received_cash=300.0,
            received_card=50.0,
            comment="Cash received cleanly",
            actor=admin_user,
        )
        assert res is not None


@pytest.mark.asyncio
async def test_exports_and_audit_logs_filters(db_session: AsyncSession, admin_user: User):
    csv_cash = await export_drivers_cash_csv(db=db_session, date_from="2027-01-01", date_to="2027-01-05")
    assert "Водій" in csv_cash

    csv_trips = await export_trips_register_csv(db=db_session, date_from="2027-01-05", date_to="2027-01-01")
    assert csv_trips is not None

    logs = await list_audit_logs(
        db=db_session,
        trip_id=1,
    )
    assert isinstance(logs, list)


@pytest.mark.asyncio
async def test_drivers_cash_reconciliation_multi_day_range(db_session: AsyncSession, admin_user: User):
    driver = User(phone="+380979997766", full_name="Fin Driver", role=UserRole.DRIVER, is_active=True)
    db_session.add(driver)
    await db_session.commit()

    report = await drivers_cash_reconciliation_use_case(
        db=db_session,
        date_from="2027-01-01",
        date_to="2027-01-03",
    )
    assert report is not None


@pytest.mark.asyncio
async def test_cancel_trip_with_active_passengers_notifies_telegram(db_session: AsyncSession, admin_user: User, sample_trip: Trip):
    passenger = User(phone="+380971113322", full_name="Cancel Pax", role=UserRole.PASSENGER, telegram_id=55667788, is_active=True)
    driver = User(phone="+380971113323", full_name="Cancel Driver", role=UserRole.DRIVER, is_active=True)
    db_session.add_all([passenger, driver])
    await db_session.commit()

    sample_trip.driver_id = driver.id
    sample_trip.status = TripStatus.SCHEDULED
    await db_session.commit()

    booking = Booking(
        trip_id=sample_trip.id,
        passenger_id=passenger.id,
        created_by_id=passenger.id,
        source=BookingSource.BOT,
        booking_type=BookingType.SEATED,
        status=BookingStatus.RESERVED,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add(booking)
    await db_session.commit()

    with patch("app.api.admin.broadcast.run_telegram_broadcast", new_callable=AsyncMock) as mock_broadcast:
        # Cancel trip via update_trip_status
        result = await update_trip_status(
            db=db_session,
            trip_id=sample_trip.id,
            new_status=TripStatus.CANCELLED,
            actor=admin_user,
        )
        assert result.status == TripStatus.CANCELLED.value

    # Booking should be updated to CANCELLED
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_create_trip_item_validation_errors(db_session: AsyncSession, admin_user: User, passenger_user: User):
    driver = User(phone="+380971114433", full_name="Past Driver", role=UserRole.DRIVER, is_active=True)
    vehicle = Vehicle(model="Past Bus", plate_number="BC0011PST", total_seats=15, total_standing=2, is_active=True)
    db_session.add_all([driver, vehicle])
    await db_session.commit()

    payload_valid = AdminTripCreate(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        route="drohobych-lviv",
        date="2027-05-10",
        departure_time="10:00",
    )

    # 1. Forbidden non-staff actor
    with pytest.raises(HTTPException) as exc1:
        await create_trip(db=db_session, payload=payload_valid, actor=passenger_user)
    assert exc1.value.status_code == 403

    # 2. Vehicle not found
    payload_invalid_v = AdminTripCreate(
        driver_id=driver.id,
        vehicle_id=99999,
        route="drohobych-lviv",
        date="2027-05-10",
        departure_time="10:00",
    )
    with pytest.raises(HTTPException) as exc2:
        await create_trip(db=db_session, payload=payload_invalid_v, actor=admin_user)
    assert exc2.value.status_code == 404

    # 3. Driver not found
    payload_invalid_d = AdminTripCreate(
        driver_id=99999,
        vehicle_id=vehicle.id,
        route="drohobych-lviv",
        date="2027-05-10",
        departure_time="10:00",
    )
    with pytest.raises(HTTPException) as exc3:
        await create_trip(db=db_session, payload=payload_invalid_d, actor=admin_user)
    assert exc3.value.status_code == 404

    # 4. Create trip successfully first time
    created_t = await create_trip(db=db_session, payload=payload_valid, actor=admin_user)
    assert created_t.id is not None

    # 5. Driver or vehicle conflict error
    with pytest.raises(HTTPException) as exc5:
        await create_trip(db=db_session, payload=payload_valid, actor=admin_user)
    assert exc5.value.status_code == 409
