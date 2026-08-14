"""
Integration tests for trip overbooking, snapshot limits, and vehicle swap validation.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Trip, TripStatus, Booking, BookingType, BookingSource, 
    BookingStatus, PaymentMethod, User, UserRole, Vehicle, Location
)
from app.schemas.admin import AdminManifestBookingCreate, AdminTripUpdate
from app.services import admin_use_cases


@pytest.mark.asyncio
async def test_manifest_overbooking_seated_and_standing_limits(db_session: AsyncSession, admin_user: User):
    """
    Перевіряє заборону овербукінгу:
    1. Заборона перевищення ліміту сидячих місць.
    2. Заборона перевищення ліміту стоячих місць.
    """
    driver = User(phone="+380979001001", full_name="Водій Лімітів", role=UserRole.DRIVER, is_active=True)
    from_loc = Location(name="Drohobych_Lim1")
    to_loc = Location(name="Lviv_Lim1")
    vehicle = Vehicle(model="Small Bus", plate_number="BC9001AA", total_seats=2, total_standing=1)

    db_session.add_all([driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=admin_use_cases._combine_date_time("2026-12-01", "10:00"),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=2,
        standing_limit_snapshot=1,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(trip)
    await db_session.commit()

    # 1. Забронювати 2 сидячих місця (максимум)
    b_seated = AdminManifestBookingCreate(
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        phone="0970001122",
        full_name="Пасажир 1",
        seats=2,
    )
    await admin_use_cases.create_manifest_booking_use_case(db_session, trip.id, b_seated, actor=admin_user)

    # Спроба забронювати ще 1 сидяче місце має викликати HTTP 400
    b_seated_over = AdminManifestBookingCreate(
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        phone="0970001123",
        full_name="Пасажир Зайвий",
        seats=1,
    )
    with pytest.raises(HTTPException) as exc_info:
        await admin_use_cases.create_manifest_booking_use_case(db_session, trip.id, b_seated_over, actor=admin_user)
    assert exc_info.value.status_code == 400
    assert "недостатньо" in exc_info.value.detail.lower()

    # 2. Забронювати 1 стояче місце (максимум)
    b_standing = AdminManifestBookingCreate(
        booking_type=BookingType.STANDING,
        source=BookingSource.PHONE,
        phone="0970001124",
        full_name="Стоячий 1",
        seats=1,
    )
    await admin_use_cases.create_manifest_booking_use_case(db_session, trip.id, b_standing, actor=admin_user)

    # Спроба забронювати друге стояче місце викликає HTTP 400
    b_standing_over = AdminManifestBookingCreate(
        booking_type=BookingType.STANDING,
        source=BookingSource.PHONE,
        phone="0970001125",
        full_name="Стоячий Зайвий",
        seats=1,
    )
    with pytest.raises(HTTPException) as exc_info_st:
        await admin_use_cases.create_manifest_booking_use_case(db_session, trip.id, b_standing_over, actor=admin_user)
    assert exc_info_st.value.status_code == 400
    assert "використано" in exc_info_st.value.detail.lower() or "вихерпано" in exc_info_st.value.detail.lower() or "ліміт" in exc_info_st.value.detail.lower()


@pytest.mark.asyncio
async def test_vehicle_swap_validation_against_booked_seats(db_session: AsyncSession, admin_user: User):
    """
    Перевіряє, що при заміні авто на інше (меншої місткості),
    якщо кількість вже заброньованих місць перевищує нову місткість, операція блокується.
    """
    driver = User(phone="+380979001002", full_name="Водій Свопу", role=UserRole.DRIVER, is_active=True)
    from_loc = Location(name="Drohobych_Swap1")
    to_loc = Location(name="Lviv_Swap1")
    big_vehicle = Vehicle(model="Big Bus", plate_number="BC9002AA", total_seats=20, total_standing=10)
    small_vehicle = Vehicle(model="Tiny Car", plate_number="BC9002BB", total_seats=2, total_standing=0)

    db_session.add_all([driver, from_loc, to_loc, big_vehicle, small_vehicle])
    await db_session.commit()

    trip = Trip(
        driver_id=driver.id,
        vehicle_id=big_vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=admin_use_cases._combine_date_time("2026-12-02", "11:00"),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=20,
        standing_limit_snapshot=10,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(trip)
    await db_session.commit()

    # Забронюємо 5 сидячих місць на великий бус
    b_5 = AdminManifestBookingCreate(
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        phone="0975556677",
        full_name="Група 5 осіб",
        seats=5,
    )
    await admin_use_cases.create_manifest_booking_use_case(db_session, trip.id, b_5, actor=admin_user)

    # Спроба замінити великий бус на маленьке авто з 2 місцями повинна викликати HTTP 400
    update_payload = AdminTripUpdate(
        driver_id=driver.id,
        vehicle_id=small_vehicle.id,
        route="drohobych-lviv",
        date="2026-12-02",
        departure_time="11:00",
        arrival_time="12:30",
        price_seated=150.0,
        price_standing=100.0,
    )

    with pytest.raises(HTTPException) as exc_info:
        await admin_use_cases.update_trip(db_session, trip.id, update_payload, actor=admin_user)

    assert exc_info.value.status_code == 400
    assert "неможливо замінити авто" in exc_info.value.detail.lower()
