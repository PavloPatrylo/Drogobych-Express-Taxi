import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, Trip, TripStatus
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_broadcast_preview_and_send_endpoints(db_session: AsyncSession, admin_user: User, sample_trip: Trip):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    passenger = User(phone="+380979991100", full_name="Broadcast Pax", role=UserRole.PASSENGER, telegram_id=1234567, is_active=True)
    driver = User(phone="+380979991101", full_name="Broadcast Driver", role=UserRole.DRIVER, telegram_id=7654321, is_active=True)
    db_session.add_all([passenger, driver])
    await db_session.commit()

    sample_trip.driver_id = driver.id
    await db_session.commit()

    with patch("app.api.admin.broadcast.run_telegram_broadcast", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Preview broadcast for all
            resp_prev_all = await client.post(
                "/api/admin/broadcast/preview",
                json={"target_group": "all", "text": "General Announcement"},
                headers=headers,
            )
            assert resp_prev_all.status_code == 200
            assert resp_prev_all.json()["recipients_count"] >= 2

            # 2. Preview broadcast for drivers
            resp_prev_drivers = await client.post(
                "/api/admin/broadcast/preview",
                json={"target_group": "drivers", "text": "Driver Notice"},
                headers=headers,
            )
            assert resp_prev_drivers.status_code == 200

            # 3. Preview broadcast for specific trip
            resp_prev_trip = await client.post(
                "/api/admin/broadcast/preview",
                json={"trip_id": sample_trip.id, "text": "Trip Notice"},
                headers=headers,
            )
            assert resp_prev_trip.status_code == 200

            # 4. Send broadcast
            resp_send = await client.post(
                "/api/admin/broadcast/send",
                json={"target_group": "drivers", "text": "Official Driver Alert"},
                headers=headers,
            )
            assert resp_send.status_code == 200
            assert resp_send.json()["message"] == "Broadcast queued"


@pytest.mark.asyncio
async def test_publish_schedule_preview_and_send_endpoints(db_session: AsyncSession, admin_user: User, sample_trip: Trip):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    driver = User(phone="+380979992200", full_name="Schedule Driver", role=UserRole.DRIVER, telegram_id=55443322, is_active=True)
    db_session.add(driver)
    await db_session.commit()

    sample_trip.driver_id = driver.id
    sample_trip.status = TripStatus.SCHEDULED
    await db_session.commit()

    target_date_str = sample_trip.departure_time.strftime("%Y-%m-%d")

    with patch("app.api.admin.broadcast.run_telegram_broadcast", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Preview publish schedule
            resp_prev = await client.post(
                "/api/admin/broadcast/publish-schedule/preview",
                json={
                    "date_from": target_date_str,
                    "date_to": target_date_str,
                    "driver_id": driver.id,
                },
                headers=headers,
            )
            assert resp_prev.status_code == 200
            assert resp_prev.json()["trips_count"] >= 1

            # 2. Publish schedule
            resp_pub = await client.post(
                "/api/admin/broadcast/publish-schedule",
                json={
                    "date_from": target_date_str,
                    "date_to": target_date_str,
                    "driver_id": driver.id,
                    "comment": "Be on time",
                },
                headers=headers,
            )
            assert resp_pub.status_code == 200
            assert resp_pub.json()["success"] is True
