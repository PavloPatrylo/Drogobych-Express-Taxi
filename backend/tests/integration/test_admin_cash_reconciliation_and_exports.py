import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.services.admin_use_cases import (
    drivers_cash_reconciliation_use_case,
    confirm_driver_cash_use_case,
    export_drivers_cash_csv,
    export_trips_register_csv,
    export_parcels_register_csv,
    get_finance_closures_history_use_case,
)


@pytest.mark.asyncio
async def test_cash_reconciliation_and_confirm_driver_cash(
    db_session: AsyncSession, admin_user: User, dispatcher_user: User
):
    # Setup Driver, Locations, Vehicle, Completed Trip, Booking
    driver = User(phone="+380971239999", full_name="Driver Dave", role=UserRole.DRIVER, is_active=True)
    from_loc = Location(name="Drohobych")
    to_loc = Location(name="Lviv")
    vehicle = Vehicle(model="Sprinter", plate_number="BC7777EX", total_seats=18, total_standing=5)

    db_session.add_all([driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    dep_time = datetime(2026, 8, 15, 10, 0, tzinfo=timezone.utc)
    trip = Trip(
        departure_time=dep_time,
        arrival_time=datetime(2026, 8, 15, 11, 30, tzinfo=timezone.utc),
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        vehicle_id=vehicle.id,
        driver_id=driver.id,
        status=TripStatus.COMPLETED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
        price_parcel=80.0,
    )
    db_session.add(trip)
    await db_session.commit()

    passenger = User(phone="+380978887766", full_name="Pass One", role=UserRole.PASSENGER, is_active=True)
    db_session.add(passenger)
    await db_session.commit()

    booking = Booking(
        trip_id=trip.id,
        passenger_id=passenger.id,
        created_by_id=dispatcher_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.BOARDED,
        payment_method=PaymentMethod.CASH,
        passengers_count=2,
        amount_paid=300.0,
    )
    db_session.add(booking)
    await db_session.commit()

    target_date = "2026-08-15"

    # Reconciliation before confirm
    recon_before = await drivers_cash_reconciliation_use_case(db_session, target_date=target_date)
    assert recon_before["global"]["expected_revenue"] == 300.0
    assert len(recon_before["drivers"]) == 1
    assert recon_before["drivers"][0]["status"] == "PENDING"

    # Confirm cash submission by dispatcher
    confirmed_res = await confirm_driver_cash_use_case(
        db_session,
        actor=dispatcher_user,
        driver_id=driver.id,
        target_date=target_date,
        received_cash=200.0,
        received_card=100.0,
        comment="Cash matches expected total",
    )
    assert len(confirmed_res["drivers"]) == 1
    assert confirmed_res["drivers"][0]["status"] == "CLOSED"
    assert confirmed_res["drivers"][0]["submitted_cash"] == 200.0
    assert confirmed_res["drivers"][0]["submitted_card"] == 100.0


@pytest.mark.asyncio
async def test_exports_csv_and_history(
    db_session: AsyncSession, admin_user: User, sample_trip: Trip, passenger_user: User
):
    # Add parcel booking to test parcel export
    parcel_booking = Booking(
        trip_id=sample_trip.id,
        passenger_id=passenger_user.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.PARCEL,
        source=BookingSource.PHONE,
        status=BookingStatus.PAID,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=80.0,
        comment="Small box",
    )
    db_session.add(parcel_booking)
    await db_session.commit()

    date_str = "2026-08-15"

    # Drivers cash CSV
    csv_drivers = await export_drivers_cash_csv(db_session, date_from=date_str, date_to=date_str)
    assert "Водій" in csv_drivers

    # Trips register CSV
    csv_trips = await export_trips_register_csv(db_session, date_from=date_str, date_to=date_str)
    assert "Маршрут" in csv_trips
    assert "Drogobych → Lviv" in csv_trips

    # Parcels register CSV
    csv_parcels = await export_parcels_register_csv(db_session, date_from=date_str, date_to=date_str)
    assert "Відправник / Пасажир" in csv_parcels
    assert "Small box" in csv_parcels

    # Closure history
    history = await get_finance_closures_history_use_case(db_session, limit=10)
    assert isinstance(history, list)
