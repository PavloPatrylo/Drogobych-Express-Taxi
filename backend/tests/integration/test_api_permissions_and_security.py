"""
Integration tests for RBAC permissions and security access controls.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole, Location, Trip, TripStatus, Vehicle
from app.schemas.admin import ScheduleTemplateCreate, SystemConfigUpdate
from app.services import admin_use_cases


@pytest.mark.asyncio
async def test_passenger_cannot_access_admin_use_cases(db_session: AsyncSession):
    """
    Перевіряє, що пасажир без адмін-прав отримує HTTP 403 при спробі:
    1. Створити шаблон розкладу.
    2. Закрити рейс (фінансове закриття).
    """
    passenger = User(
        phone="+380974001001",
        full_name="Звичайний Пасажир",
        role=UserRole.PASSENGER,
        is_active=True,
    )
    db_session.add(passenger)
    await db_session.commit()

    # 1. Спроба створити шаблон
    tpl_payload = ScheduleTemplateCreate(
        day_type="WEEKDAY",
        from_location_id=1,
        to_location_id=2,
        departure_time="09:00",
    )
    with pytest.raises(HTTPException) as exc_tpl:
        await admin_use_cases.create_schedule_template_use_case(db_session, tpl_payload, actor=passenger)
    assert exc_tpl.value.status_code == 403

    # 2. Спроба фінансового закриття рейсу водієм або пасажиром
    driver = User(phone="+380974001002", full_name="Водій 403", role=UserRole.DRIVER, is_active=True)
    from_loc = Location(name="Drohobych_Perm")
    to_loc = Location(name="Lviv_Perm")
    vehicle = Vehicle(model="Sprinter Perm", plate_number="BC4003AA", total_seats=18, total_standing=5)

    db_session.add_all([driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=admin_use_cases._combine_date_time("2026-12-25", "10:00"),
        status=TripStatus.COMPLETED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add(trip)
    await db_session.commit()

    # Водій НЕ має права закривати рейс фінансово (лише Диспетчер/Адмін)
    with pytest.raises(HTTPException) as exc_close:
        await admin_use_cases.update_trip_status(db_session, trip.id, new_status=TripStatus.CLOSED, actor=driver)

    assert exc_close.value.status_code == 403
