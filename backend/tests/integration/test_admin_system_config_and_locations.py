import pytest
import pytest_asyncio
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, User, UserRole, SystemConfig, DayType
from app.schemas.admin import SystemConfigUpdate, ScheduleTemplateCreate
from app.services.admin_use_cases import (
    list_locations_use_case,
    get_system_config_use_case,
    update_system_config_use_case,
    dashboard,
    finance_summary,
    driver_report_use_case,
    vehicle_report_use_case,
    create_schedule_template_use_case,
    delete_schedule_template_use_case,
)


@pytest.mark.asyncio
async def test_list_locations_filters_invalid_names(db_session: AsyncSession):
    # Setup locations: valid and invalid
    loc1 = Location(name="Drohobych")
    loc2 = Location(name="Lviv")
    loc3 = Location(name="?")
    loc4 = Location(name=" A ")
    loc5 = Location(name="")

    db_session.add_all([loc1, loc2, loc3, loc4, loc5])
    await db_session.commit()

    locations = await list_locations_use_case(db_session)
    loc_names = [loc.name for loc in locations]

    assert "Drohobych" in loc_names
    assert "Lviv" in loc_names
    assert "?" not in loc_names
    assert "" not in loc_names


@pytest.mark.asyncio
async def test_get_system_config_creates_default(db_session: AsyncSession):
    config = await get_system_config_use_case(db_session)
    assert config.id == 1
    assert config.price_seated == 120.0
    assert config.price_standing == 80.0
    assert config.price_parcel == 50.0


@pytest.mark.asyncio
async def test_update_system_config_success(db_session: AsyncSession, admin_user: User):
    update_payload = SystemConfigUpdate(
        price_seated=160.0,
        price_standing=110.0,
        price_parcel=90.0,
    )
    updated = await update_system_config_use_case(db_session, update_payload, admin_user)

    assert updated.price_seated == 160.0
    assert updated.price_standing == 110.0
    assert updated.price_parcel == 90.0

    # Verify db persistence
    config_in_db = await get_system_config_use_case(db_session)
    assert config_in_db.price_seated == 160.0


@pytest.mark.asyncio
async def test_update_system_config_forbidden_for_non_admin(db_session: AsyncSession, passenger_user: User):
    update_payload = SystemConfigUpdate(
        price_seated=200.0,
        price_standing=150.0,
        price_parcel=100.0,
    )
    with pytest.raises(HTTPException) as exc_info:
        await update_system_config_use_case(db_session, update_payload, passenger_user)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_dashboard_and_reports(db_session: AsyncSession):
    dash_res = await dashboard(db_session)
    assert "trips" in dash_res
    assert "bookings" in dash_res

    fin_res = await finance_summary(db_session, date_from="2026-08-01", date_to="2026-08-31")
    assert "total_revenue" in fin_res

    driver_rep = await driver_report_use_case(db_session)
    assert isinstance(driver_rep, list)

    vehicle_rep = await vehicle_report_use_case(db_session)
    assert isinstance(vehicle_rep, list)


@pytest.mark.asyncio
async def test_schedule_template_permissions_and_errors(db_session: AsyncSession, admin_user: User, passenger_user: User):
    loc1 = Location(name="Drohobych")
    loc2 = Location(name="Lviv")
    db_session.add_all([loc1, loc2])
    await db_session.commit()

    tmpl_payload = ScheduleTemplateCreate(
        day_type=DayType.WEEKDAY,
        from_location_id=loc1.id,
        to_location_id=loc2.id,
        departure_time="08:00",
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_schedule_template_use_case(db_session, tmpl_payload, passenger_user)
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    with pytest.raises(HTTPException) as exc_info2:
        await delete_schedule_template_use_case(db_session, 999999, admin_user)
    assert exc_info2.value.status_code == status.HTTP_404_NOT_FOUND
