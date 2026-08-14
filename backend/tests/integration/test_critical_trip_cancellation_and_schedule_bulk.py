import pytest
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select

from app.db.models import User, Vehicle, Location, Trip, TripStatus, Booking, BookingStatus, BookingType, BookingSource, ScheduleTemplate
from app.services.admin_use_cases import (
    update_trip_status,
    update_trip,
    create_batch_trips,
)
from app.schemas.admin import AdminTripUpdate, AdminBatchTripCreate, AdminBatchTripItem

KYIV_TZ = ZoneInfo("Europe/Kyiv")

@pytest.mark.asyncio
async def test_cancel_trip_with_active_bookings(db_session, admin_user, driver_user, vehicle, locations, passenger_user):
    from_loc, to_loc = locations

    # Create scheduled trip
    trip = Trip(
        driver_id=driver_user.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=datetime.now(KYIV_TZ) + timedelta(days=2),
        arrival_time=datetime.now(KYIV_TZ) + timedelta(days=2, hours=2),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=vehicle.total_seats,
        standing_limit_snapshot=vehicle.total_standing,
        price_seated=180.0,
        price_standing=120.0,
        price_parcel=60.0,
    )
    db_session.add(trip)
    await db_session.flush()

    # Add passenger booking
    booking = Booking(
        trip_id=trip.id,
        passenger_id=passenger_user.id,
        created_by_id=passenger_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.BOT,
        status=BookingStatus.RESERVED,
        passengers_count=2,
        amount_paid=360.0,
    )
    db_session.add(booking)
    await db_session.commit()

    # Cancel trip as admin via update_trip_status
    cancelled_trip = await update_trip_status(
        db=db_session,
        trip_id=trip.id,
        new_status=TripStatus.CANCELLED,
        actor=admin_user,
    )
    assert cancelled_trip.status == TripStatus.CANCELLED

    # Verify booking status transitioned to CANCELLED
    await db_session.refresh(booking)
    assert booking.status == BookingStatus.CANCELLED


@pytest.mark.asyncio
async def test_create_batch_trips_schedule_bulk(db_session, admin_user, driver_user, vehicle, locations):
    next_date = (date.today() + timedelta(days=2)).isoformat()

    items = [
        AdminBatchTripItem(
            driver_id=driver_user.id,
            vehicle_id=vehicle.id,
            route="drohobych-lviv",
            date=next_date,
            departure_time=t_time,
            arrival_time="18:00",
        )
        for t_time in ["08:00", "12:00", "16:00"]
    ]

    batch_payload = AdminBatchTripCreate(trips=items)

    created_trips = await create_batch_trips(
        db=db_session,
        payload=batch_payload,
        actor=admin_user,
    )
    assert len(created_trips) == 3
    assert all(t.status == TripStatus.SCHEDULED for t in created_trips)


@pytest.mark.asyncio
async def test_update_trip_prices(db_session, admin_user, driver_user, vehicle, locations):
    from_loc, to_loc = locations

    trip = Trip(
        driver_id=driver_user.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=datetime.now(KYIV_TZ) + timedelta(days=1),
        arrival_time=datetime.now(KYIV_TZ) + timedelta(days=1, hours=2),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=vehicle.total_seats,
        standing_limit_snapshot=vehicle.total_standing,
        price_seated=150.0,
        price_standing=100.0,
        price_parcel=50.0,
    )
    db_session.add(trip)
    await db_session.commit()

    trip_update = AdminTripUpdate(
        route="drohobych-lviv",
        date=(date.today() + timedelta(days=1)).isoformat(),
        departure_time="10:00",
        arrival_time="12:00",
        driver_id=driver_user.id,
        vehicle_id=vehicle.id,
        price_seated=220.0,
        price_standing=130.0,
        price_parcel=80.0,
    )

    updated_trip = await update_trip(
        db=db_session,
        trip_id=trip.id,
        payload=trip_update,
        actor=admin_user,
    )
    assert updated_trip.price_seated == 220.0
    assert updated_trip.price_standing == 130.0
    assert updated_trip.price_parcel == 80.0
