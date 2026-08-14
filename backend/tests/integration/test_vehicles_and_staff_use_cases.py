"""
Integration tests for vehicles and staff management functionality.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import User, UserRole, Vehicle
from app.core.security import hash_password
from app.services import admin_use_cases, auth_service


@pytest.mark.asyncio
async def test_vehicles_use_cases(db_session: AsyncSession, admin_user: User):
    # 1. Create Vehicle
    vehicle = Vehicle(
        plate_number="BC9876XX",
        model="Mercedes Sprinter 316",
        total_seats=18,
        total_standing=5,
        is_active=True,
    )
    db_session.add(vehicle)
    await db_session.commit()
    await db_session.refresh(vehicle)

    assert vehicle.id is not None
    assert vehicle.plate_number == "BC9876XX"

    # 2. List Vehicles
    vehicles = await admin_use_cases.list_vehicles(db_session)
    assert any(v.id == vehicle.id for v in vehicles)

    # 3. Update Vehicle
    vehicle.model = "Mercedes Sprinter 319 (Updated)"
    vehicle.total_seats = 20
    vehicle.is_active = False
    await db_session.commit()

    vehicles_updated = await admin_use_cases.list_vehicles(db_session)
    updated_v = next(v for v in vehicles_updated if v.id == vehicle.id)
    assert updated_v.model == "Mercedes Sprinter 319 (Updated)"
    assert updated_v.total_seats == 20
    assert updated_v.is_active is False


@pytest.mark.asyncio
async def test_staff_use_cases(db_session: AsyncSession, admin_user: User):
    # 1. Create Staff Driver
    driver = User(
        full_name="Максим Водієнко",
        phone="+380975554433",
        role=UserRole.DRIVER,
        password=hash_password("DriverPassword123"),
        is_active=True,
    )
    db_session.add(driver)
    await db_session.commit()

    # 2. List Staff
    staff_list = await auth_service.get_staff_list(db_session)
    assert any(s.id == driver.id for s in staff_list)

    # 3. Update Staff Role & Status
    driver.role = UserRole.DISPATCHER
    driver.full_name = "Максим Водієнко (Диспетчер)"
    await db_session.commit()

    staff_updated = await auth_service.get_staff_list(db_session)
    updated_member = next(s for s in staff_updated if s.id == driver.id)
    assert updated_member.full_name == "Максим Водієнко (Диспетчер)"
    assert updated_member.role == UserRole.DISPATCHER
