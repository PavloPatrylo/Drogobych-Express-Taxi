import pytest
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import User, UserRole, Vehicle, Location, Trip, TripStatus, Booking, BookingStatus, BookingType, BookingSource, PaymentMethod
from app.services.admin_use_cases import (
    close_trip,
    drivers_cash_reconciliation_use_case,
    export_drivers_cash_csv,
    export_trips_register_csv,
)

KYIV_TZ = ZoneInfo("Europe/Kyiv")

@pytest.mark.asyncio
async def test_close_trip_permissions_and_statuses(db_session, admin_user, driver_user, vehicle, locations):
    from_loc, to_loc = locations

    # 1. Non-admin actor raises 403
    with pytest.raises(HTTPException) as exc_info:
        await close_trip(
            db=db_session,
            trip_id=999,
            actor=driver_user,
        )
    assert exc_info.value.status_code == 403

    # 2. Non-existent trip raises 404
    with pytest.raises(HTTPException) as exc_info:
        await close_trip(
            db=db_session,
            trip_id=999999,
            actor=admin_user,
        )
    assert exc_info.value.status_code == 404

    # 3. Trip in SCHEDULED status raises 400 (cannot close uncompleted trip)
    trip = Trip(
        driver_id=driver_user.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=datetime.now(KYIV_TZ) + timedelta(hours=2),
        arrival_time=datetime.now(KYIV_TZ) + timedelta(hours=4),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=vehicle.total_seats,
        standing_limit_snapshot=vehicle.total_standing,
        price_seated=150.0,
        price_standing=100.0,
        price_parcel=50.0,
    )
    db_session.add(trip)
    await db_session.commit()
    await db_session.refresh(trip)

    with pytest.raises(HTTPException) as exc_info:
        await close_trip(
            db=db_session,
            trip_id=trip.id,
            actor=admin_user,
        )
    assert exc_info.value.status_code == 400

    # 4. Update status to COMPLETED and successfully close financially
    trip.status = TripStatus.COMPLETED
    await db_session.commit()

    closed_trip_res = await close_trip(
        db=db_session,
        trip_id=trip.id,
        actor=admin_user,
        submitted_cash=300.0,
        submitted_card=150.0,
        comment="Каса здана в повному обсязі",
    )
    assert closed_trip_res.status == TripStatus.CLOSED
    assert closed_trip_res.submitted_cash == 300.0
    assert closed_trip_res.submitted_card == 150.0
    assert closed_trip_res.submitted_amount == 450.0
    assert closed_trip_res.close_comment == "Каса здана в повному обсязі"


@pytest.mark.asyncio
async def test_drivers_cash_reconciliation_use_case_deep(db_session, admin_user, driver_user, vehicle, locations, passenger_user):
    from_loc, to_loc = locations
    today_str = datetime.now(KYIV_TZ).date().isoformat()

    # Create completed trip for driver with CASH and CARD bookings
    trip = Trip(
        driver_id=driver_user.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=datetime.now(KYIV_TZ),
        arrival_time=datetime.now(KYIV_TZ) + timedelta(hours=2),
        status=TripStatus.COMPLETED,
        seats_limit_snapshot=vehicle.total_seats,
        standing_limit_snapshot=vehicle.total_standing,
        price_seated=200.0,
        price_standing=120.0,
        price_parcel=60.0,
    )
    db_session.add(trip)
    await db_session.flush()

    b_cash = Booking(
        trip_id=trip.id,
        passenger_id=passenger_user.id,
        created_by_id=passenger_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.BOT,
        status=BookingStatus.BOARDED,
        payment_method=PaymentMethod.CASH,
        passengers_count=2,
        amount_paid=400.0,
    )
    b_card = Booking(
        trip_id=trip.id,
        passenger_id=passenger_user.id,
        created_by_id=passenger_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.WEB,
        status=BookingStatus.BOARDED,
        payment_method=PaymentMethod.CARD,
        passengers_count=1,
        amount_paid=200.0,
    )
    db_session.add_all([b_cash, b_card])
    await db_session.commit()

    # Test cash reconciliation for today
    recon = await drivers_cash_reconciliation_use_case(
        db=db_session,
        target_date=today_str,
    )
    assert recon["date_from"] == today_str
    assert recon["date_to"] == today_str
    assert "drivers" in recon
    assert len(recon["drivers"]) >= 1

    driver_data = next((d for d in recon["drivers"] if d["driver_id"] == driver_user.id), None)
    assert driver_data is not None
    assert driver_data["expected_total"] == 600.0
    assert len(driver_data["trips"]) >= 1

    # Test with invalid date range fallbacks
    recon_invalid = await drivers_cash_reconciliation_use_case(
        db=db_session,
        date_from="invalid-date",
        date_to="invalid-date",
    )
    assert recon_invalid["date_from"] == today_str


@pytest.mark.asyncio
async def test_csv_exports_output(db_session, driver_user, vehicle, locations, passenger_user):
    from_loc, to_loc = locations
    today_str = date.today().isoformat()

    # Export drivers cash csv
    drivers_csv = await export_drivers_cash_csv(
        db=db_session,
        date_from=today_str,
        date_to=today_str,
    )
    assert isinstance(drivers_csv, str)
    assert len(drivers_csv) > 0

    # Export trips register csv
    trips_csv = await export_trips_register_csv(
        db=db_session,
        date_from=today_str,
        date_to=today_str,
    )
    assert isinstance(trips_csv, str)
    assert len(trips_csv) > 0
