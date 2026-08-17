import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole, Location, Vehicle, Trip, TripStatus
from app.schemas.admin import (
    AdminBatchTripCreate,
    AdminBatchTripItem,
    AdminTripUpdate,
    AdminTripAssignUpdate,
    AdminCloseTripRequest,
)
from app.services.admin_use_cases import (
    create_batch_trips,
    update_trip,
    update_trip_status,
    update_trip_assign_use_case,
    close_trip,
)


@pytest.mark.asyncio
async def test_create_batch_trips(db_session: AsyncSession, admin_user: User):
    from_loc = Location(name="Drohobych")
    to_loc = Location(name="Lviv")
    vehicle = Vehicle(model="Mercedes Sprinter", plate_number="BC5555EX", total_seats=18, total_standing=5)
    db_session.add_all([from_loc, to_loc, vehicle])
    await db_session.commit()

    driver = User(phone="+380973334455", full_name="Batch Driver", role=UserRole.DRIVER, is_active=True)
    db_session.add(driver)
    await db_session.commit()

    from datetime import date, timedelta
    future_date_str = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")

    batch_payload = AdminBatchTripCreate(
        trips=[
            AdminBatchTripItem(
                driver_id=driver.id,
                vehicle_id=vehicle.id,
                route="drohobych-lviv",
                date=future_date_str,
                departure_time="07:00",
                arrival_time="08:30",
            ),
            AdminBatchTripItem(
                driver_id=driver.id,
                vehicle_id=vehicle.id,
                route="drohobych-lviv",
                date=future_date_str,
                departure_time="10:00",
                arrival_time="11:30",
            ),
        ]
    )

    results = await create_batch_trips(db_session, batch_payload, admin_user)
    assert len(results) == 2
    assert results[0].departure_time == "07:00"
    assert results[1].departure_time == "10:00"


@pytest.mark.asyncio
async def test_update_trip_and_status(db_session: AsyncSession, sample_trip: Trip, admin_user: User, dispatcher_user: User):
    driver = User(phone="+380970001122", full_name="Driver Test", role=UserRole.DRIVER, is_active=True)
    db_session.add(driver)
    await db_session.commit()

    dep_date_str = sample_trip.departure_time.strftime("%Y-%m-%d")

    update_payload = AdminTripUpdate(
        driver_id=driver.id,
        vehicle_id=sample_trip.vehicle_id,
        route="drohobych-lviv",
        date=dep_date_str,
        departure_time="09:00",
        arrival_time="10:30",
        price_seated=180.0,
        price_standing=120.0,
        price_parcel=90.0,
    )

    updated = await update_trip(db_session, sample_trip.id, update_payload, admin_user)
    assert updated.departure_time == "09:00"
    assert updated.price_seated == 180.0

    # Status transitions by dispatcher
    s_boarding = await update_trip_status(db_session, sample_trip.id, TripStatus.BOARDING, dispatcher_user)
    assert s_boarding.status == TripStatus.BOARDING

    s_completed = await update_trip_status(db_session, sample_trip.id, TripStatus.COMPLETED, dispatcher_user)
    assert s_completed.status == TripStatus.COMPLETED


@pytest.mark.asyncio
async def test_update_trip_assign(db_session: AsyncSession, sample_trip: Trip, admin_user: User):
    new_driver = User(phone="+380974445566", full_name="New Driver", role=UserRole.DRIVER, is_active=True)
    new_vehicle = Vehicle(model="Crafter", plate_number="BC9999EX", total_seats=20, total_standing=6)
    db_session.add_all([new_driver, new_vehicle])
    await db_session.commit()

    assign_payload = AdminTripAssignUpdate(
        driver_id=new_driver.id,
        vehicle_id=new_vehicle.id,
    )

    assigned = await update_trip_assign_use_case(db_session, sample_trip.id, assign_payload, admin_user)
    assert assigned.driver_id == new_driver.id
    assert assigned.vehicle_id == new_vehicle.id


@pytest.mark.asyncio
async def test_close_trip(db_session: AsyncSession, sample_trip: Trip, admin_user: User):
    sample_trip.status = TripStatus.COMPLETED
    await db_session.commit()

    closed = await close_trip(
        db_session,
        sample_trip.id,
        actor=admin_user,
        submitted_cash=1500.0,
        submitted_card=500.0,
        comment="Shift ended cleanly",
    )
    assert closed.status == TripStatus.CLOSED
    assert closed.submitted_cash == 1500.0
    assert closed.submitted_card == 500.0
    assert closed.submitted_amount == 2000.0
