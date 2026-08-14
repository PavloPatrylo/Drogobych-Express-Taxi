"""
Integration tests for trip creation & update validations (e.g. past departure time blocking).
"""
import pytest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole, Vehicle, Location
from app.schemas.admin import AdminTripCreate, AdminTripUpdate
from app.services import admin_use_cases

KYIV = ZoneInfo("Europe/Kyiv")


@pytest.mark.asyncio
async def test_create_trip_in_past_raises_error(db_session: AsyncSession, admin_user: User):
    """
    Перевіряє, що спроба створити рейс на дату/час у минулому повертає помилку HTTP 400.
    """
    driver = User(
        phone="+380979998811",
        full_name="Тестовий Водій",
        role=UserRole.DRIVER,
        is_active=True,
    )
    from_loc = Location(name="Drohobych_Past1")
    to_loc = Location(name="Lviv_Past1")
    vehicle = Vehicle(model="Sprinter Past", plate_number="BC0000PA", total_seats=18, total_standing=5)

    db_session.add_all([driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    past_date_str = "2020-01-01"
    past_time_str = "08:00"

    trip_payload = AdminTripCreate(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        route="drohobych-lviv",
        date=past_date_str,
        departure_time=past_time_str,
        arrival_time="09:30",
    )

    with pytest.raises(HTTPException) as exc_info:
        await admin_use_cases.create_trip(db_session, trip_payload, actor=admin_user)

    assert exc_info.value.status_code == 400
    assert "минули" in exc_info.value.detail.lower()
