"""
Integration tests for driver and vehicle assignment conflict validations.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole, Vehicle, Location, Trip, TripStatus
from app.schemas.admin import AdminTripCreate
from app.services import admin_use_cases


@pytest.mark.asyncio
async def test_driver_and_vehicle_conflict_prevention(db_session: AsyncSession, admin_user: User):
    """
    Перевіряє:
    1. Заборону призначення одного і того ж водія на 2 різні активні рейси в один і той самий час.
    2. Заборону призначення одного і того ж автобуса на 2 різні активні рейси в один і той самий час.
    """
    driver1 = User(phone="+380976001001", full_name="Водій Конфлікту", role=UserRole.DRIVER, is_active=True)
    driver2 = User(phone="+380976001002", full_name="Водій Вільний", role=UserRole.DRIVER, is_active=True)

    vehicle1 = Vehicle(model="Bus 1", plate_number="BC6001AA", total_seats=18, total_standing=5)
    vehicle2 = Vehicle(model="Bus 2", plate_number="BC6002AA", total_seats=18, total_standing=5)

    from_loc = Location(name="Drohobych_Conf")
    to_loc = Location(name="Lviv_Conf")

    db_session.add_all([driver1, driver2, vehicle1, vehicle2, from_loc, to_loc])
    await db_session.commit()

    date_str = "2026-12-20"
    time_str = "07:00"

    # 1. Створюємо Перший рейс з driver1 та vehicle1
    payload1 = AdminTripCreate(
        driver_id=driver1.id,
        vehicle_id=vehicle1.id,
        route="drohobych-lviv",
        date=date_str,
        departure_time=time_str,
        arrival_time="08:30",
    )
    trip1 = await admin_use_cases.create_trip(db_session, payload1, actor=admin_user)
    assert trip1.id is not None

    # 2. Спроба створити другий рейс з тим самим водієм (driver1) має викликати HTTP 409 Conflict
    payload_same_driver = AdminTripCreate(
        driver_id=driver1.id,
        vehicle_id=vehicle2.id,
        route="lviv-drohobych",
        date=date_str,
        departure_time=time_str,
        arrival_time="08:30",
    )
    with pytest.raises(HTTPException) as exc_info_driver:
        await admin_use_cases.create_trip(db_session, payload_same_driver, actor=admin_user)

    assert exc_info_driver.value.status_code == 409

    # 3. Спроба створити другий рейс з тим самим автобусом (vehicle1) має викликати HTTP 409 Conflict
    payload_same_vehicle = AdminTripCreate(
        driver_id=driver2.id,
        vehicle_id=vehicle1.id,
        route="lviv-drohobych",
        date=date_str,
        departure_time=time_str,
        arrival_time="08:30",
    )
    with pytest.raises(HTTPException) as exc_info_vehicle:
        await admin_use_cases.create_trip(db_session, payload_same_vehicle, actor=admin_user)

    assert exc_info_vehicle.value.status_code == 409
