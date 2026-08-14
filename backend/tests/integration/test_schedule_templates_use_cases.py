"""
Integration tests for Schedule Templates management use cases.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserRole, Location, ScheduleTemplate, DayType
from app.schemas.admin import ScheduleTemplateCreate
from app.services import admin_use_cases


@pytest.mark.asyncio
async def test_schedule_templates_crud(db_session: AsyncSession, admin_user: User):
    loc1 = Location(name="Drohobych_TPL1")
    loc2 = Location(name="Lviv_TPL1")
    db_session.add_all([loc1, loc2])
    await db_session.commit()

    # 1. Create Template
    payload = ScheduleTemplateCreate(
        day_type=DayType.WEEKDAY,
        from_location_id=loc1.id,
        to_location_id=loc2.id,
        departure_time="07:30",
    )

    created_tpl = await admin_use_cases.create_schedule_template_use_case(db_session, payload, actor=admin_user)
    assert created_tpl.id is not None
    assert created_tpl.departure_time == "07:30"
    assert created_tpl.day_type == DayType.WEEKDAY

    # 2. List Templates
    templates = await admin_use_cases.list_schedule_templates_use_case(db_session, day_type=DayType.WEEKDAY.value)
    assert any(t.id == created_tpl.id for t in templates)

    # 3. Delete Template
    del_res = await admin_use_cases.delete_schedule_template_use_case(db_session, created_tpl.id, actor=admin_user)
    assert del_res["message"] == "Template deleted"

    # Verify deletion
    remaining = await admin_use_cases.list_schedule_templates_use_case(db_session)
    assert not any(t.id == created_tpl.id for t in remaining)


@pytest.mark.asyncio
async def test_create_template_same_location_error(db_session: AsyncSession, admin_user: User):
    loc1 = Location(name="Drohobych_SameLoc")
    db_session.add(loc1)
    await db_session.commit()

    payload = ScheduleTemplateCreate(
        day_type=DayType.SATURDAY,
        from_location_id=loc1.id,
        to_location_id=loc1.id,
        departure_time="10:00",
    )

    with pytest.raises(HTTPException) as exc_info:
        await admin_use_cases.create_schedule_template_use_case(db_session, payload, actor=admin_user)

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail is not None
