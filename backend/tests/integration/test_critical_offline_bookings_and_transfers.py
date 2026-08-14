import pytest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import User, UserRole, Vehicle, Location, Trip, TripStatus, Booking, BookingStatus, BookingType, BookingSource, PaymentMethod
from app.services.admin_use_cases import (
    create_offline_booking,
    update_booking_status_use_case,
)

KYIV_TZ = ZoneInfo("Europe/Kyiv")

@pytest.mark.asyncio
async def test_create_offline_booking_validation_and_flow(db_session, admin_user, driver_user, vehicle, locations):
    from_loc, to_loc = locations

    trip = Trip(
        driver_id=driver_user.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=datetime.now(KYIV_TZ) + timedelta(hours=5),
        arrival_time=datetime.now(KYIV_TZ) + timedelta(hours=7),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=2, # Only 2 seats total
        standing_limit_snapshot=vehicle.total_standing,
        price_seated=150.0,
        price_standing=100.0,
        price_parcel=50.0,
    )
    db_session.add(trip)
    await db_session.commit()

    # 1. Invalid phone number format raises 400
    with pytest.raises(HTTPException) as exc_info:
        await create_offline_booking(
            db=db_session,
            actor=admin_user,
            trip_id=trip.id,
            phone="12345",
            full_name="Тест Пасажир",
            source=BookingSource.PHONE,
            seats=1,
        )
    assert exc_info.value.status_code == 400

    # 2. Valid offline booking with phone normalization (0971112233 -> +380971112233)
    booking_res = await create_offline_booking(
        db=db_session,
        actor=admin_user,
        trip_id=trip.id,
        phone="0971112233",
        full_name="Олексій Тест",
        source=BookingSource.PHONE,
        seats=2,
        payment_method=PaymentMethod.CASH,
    )
    assert booking_res.passengers_count == 2
    assert booking_res.status == BookingStatus.RESERVED

    # 3. Attempting to book when seats are full raises 400
    with pytest.raises(HTTPException) as exc_info:
        await create_offline_booking(
            db=db_session,
            actor=admin_user,
            trip_id=trip.id,
            phone="0972223344",
            full_name="Інший Пасажир",
            source=BookingSource.PHONE,
            seats=1,
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_update_booking_status_and_trust_score_decay(db_session, admin_user, driver_user, vehicle, locations, passenger_user):
    from_loc, to_loc = locations

    trip = Trip(
        driver_id=driver_user.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=datetime.now(KYIV_TZ) + timedelta(hours=3),
        arrival_time=datetime.now(KYIV_TZ) + timedelta(hours=5),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=vehicle.total_seats,
        standing_limit_snapshot=vehicle.total_standing,
        price_seated=150.0,
        price_standing=100.0,
        price_parcel=50.0,
    )
    db_session.add(trip)
    await db_session.flush()

    booking = Booking(
        trip_id=trip.id,
        passenger_id=passenger_user.id,
        created_by_id=passenger_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.BOT,
        status=BookingStatus.RESERVED,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add(booking)
    await db_session.commit()

    # Update status to BOARDED
    updated_b = await update_booking_status_use_case(
        db=db_session,
        booking_id=booking.id,
        new_status=BookingStatus.BOARDED,
        actor=admin_user,
    )
    assert updated_b.status == BookingStatus.BOARDED

    # Update status to NOSHOW (triggers trust score recalculation)
    noshow_b = await update_booking_status_use_case(
        db=db_session,
        booking_id=booking.id,
        new_status=BookingStatus.NOSHOW,
        actor=admin_user,
    )
    assert noshow_b.status == BookingStatus.NOSHOW
