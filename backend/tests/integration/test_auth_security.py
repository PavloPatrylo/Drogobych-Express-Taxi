import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app
from app.db.models import User, UserRole
from app.services.auth_service import create_access_token
from tests.unit.test_telegram_auth import generate_valid_init_data
from app.core.config import settings


@pytest.mark.asyncio
async def test_telegram_webapp_auth_endpoint(db_session):
    user_dict = {"id": 888777666, "first_name": "Anna", "last_name": "Test"}
    init_data_str = generate_valid_init_data(settings.BOT_TOKEN, user_dict)

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.db.database.async_session_maker", return_value=SessionContext()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.post("/api/auth/telegram-webapp", json={"init_data": init_data_str})
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["user"]["role"].upper() == "PASSENGER"
            assert data["user"]["telegram_id"] == 888777666


@pytest.mark.asyncio
async def test_endpoint_security_matrix(db_session, passenger_user, driver_user):
    passenger_token = create_access_token(passenger_user.id, passenger_user.role)
    driver_token = create_access_token(driver_user.id, driver_user.role)

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.api.deps.async_session_maker", return_value=SessionContext()), \
         patch("app.api.users.async_session_maker", return_value=SessionContext()), \
         patch("app.api.bookings.async_session_maker", return_value=SessionContext()), \
         patch("app.api.trips.async_session_maker", return_value=SessionContext()):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Anonymous access to protected endpoint -> 401
            resp_anon = await client.get("/api/users/me")
            assert resp_anon.status_code == 401

            # 2. Authenticated passenger access to /users/me -> 200
            resp_pass = await client.get(
                "/api/users/me",
                headers={"Authorization": f"Bearer {passenger_token}"}
            )
            assert resp_pass.status_code == 200
            assert resp_pass.json()["id"] == passenger_user.id

            # 3. Passenger trying to access driver manifest -> 403
            resp_drv_man = await client.get(
                "/api/trips/driver/manifest?target_date=2026-08-25",
                headers={"Authorization": f"Bearer {passenger_token}"}
            )
            assert resp_drv_man.status_code == 403

            # 4. Driver accessing driver manifest -> 200
            resp_drv_ok = await client.get(
                "/api/trips/driver/manifest?target_date=2026-08-25",
                headers={"Authorization": f"Bearer {driver_token}"}
            )
            assert resp_drv_ok.status_code == 200

            # Sensitive booking mutations must never accept a caller-supplied Telegram ID.
            resp_status_anon = await client.patch("/api/bookings/1/status", json={"status": "BOARDED"})
            assert resp_status_anon.status_code == 401

            resp_seated_anon = await client.post("/api/bookings/seated", json={"trip_id": 1})
            assert resp_seated_anon.status_code == 401

            resp_quick_sale_anon = await client.delete("/api/bookings/1/quick-sale")
            assert resp_quick_sale_anon.status_code == 401
