"""
Integration tests for phone number normalization, automatic user creation, and blocked passenger validation.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import (
    Trip, TripStatus, Booking, BookingType, BookingSource, 
    BookingStatus, User, UserRole, Vehicle, Location
)
from app.schemas.admin import AdminManifestBookingCreate
from app.services import admin_use_cases


@pytest.mark.asyncio
async def test_phone_normalization_creates_or_matches_user(db_session: AsyncSession, admin_user: User):
    """
    Перевіряє, що телефон у форматі '0971234567' нормалізується до '+380971234567'
    і створює/знаходить одного і того ж користувача.
    """
    driver = User(phone="+380979002001", full_name="Водій Телефонів", role=UserRole.DRIVER, is_active=True)
    from_loc = Location(name="Drohobych_Phone1")
    to_loc = Location(name="Lviv_Phone1")
    vehicle = Vehicle(model="Sprinter Phone", plate_number="BC9003AA", total_seats=18, total_standing=5)

    db_session.add_all([driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=admin_use_cases._combine_date_time("2026-12-05", "08:00"),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(trip)
    await db_session.commit()

    # 1. Створюємо бронювання з телефоном без коду країни '0971112233'
    b1 = AdminManifestBookingCreate(
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        phone="0971112233",
        full_name="Олексій Телефонний",
        seats=1,
    )
    resp1 = await admin_use_cases.create_manifest_booking_use_case(db_session, trip.id, b1, actor=admin_user)
    assert resp1.passenger_id is not None

    # Перевіряємо, що у базі сформувався формат '+380971112233'
    passenger = await db_session.get(User, resp1.passenger_id)
    assert passenger.phone == "+380971112233"

    # 2. Створюємо друге бронювання з тим самим номером, але у форматі '380971112233'
    b2 = AdminManifestBookingCreate(
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        phone="380971112233",
        full_name="Олексій Оновлений",
        seats=1,
    )
    resp2 = await admin_use_cases.create_manifest_booking_use_case(db_session, trip.id, b2, actor=admin_user)

    # Використано того самого пасажира (passenger_id збігається)
    assert resp2.passenger_id == passenger.id


@pytest.mark.asyncio
async def test_blocked_passenger_booking_prevention(db_session: AsyncSession, admin_user: User):
    """
    Перевіряє, що для заблокованого пасажира (is_active=False) створити бронювання неможливо.
    """
    driver = User(phone="+380979002002", full_name="Водій Блоку", role=UserRole.DRIVER, is_active=True)
    blocked_passenger = User(
        phone="+380979990000",
        full_name="Заблокований Пасажир",
        role=UserRole.PASSENGER,
        is_active=False,
    )
    from_loc = Location(name="Drohobych_Block1")
    to_loc = Location(name="Lviv_Block1")
    vehicle = Vehicle(model="Sprinter Block", plate_number="BC9004AA", total_seats=18, total_standing=5)

    db_session.add_all([driver, blocked_passenger, from_loc, to_loc, vehicle])
    await db_session.commit()

    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=admin_use_cases._combine_date_time("2026-12-06", "09:00"),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(trip)
    await db_session.commit()

    b_blocked = AdminManifestBookingCreate(
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        phone="0979990000",
        full_name="Заблокований Пасажир",
        seats=1,
    )

    with pytest.raises(HTTPException) as exc_info:
        await admin_use_cases.create_manifest_booking_use_case(db_session, trip.id, b_blocked, actor=admin_user)

    assert exc_info.value.status_code == 400
