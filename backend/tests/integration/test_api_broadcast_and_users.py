import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, UserStats, Trip
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_users_api_get_and_update(db_session: AsyncSession, passenger_user: User):
    passenger_user.telegram_id = 99887766
    await db_session.commit()
    stats = UserStats(user_id=passenger_user.id, total_trips=2, total_noshows=0)
    db_session.add(stats)
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.api.users.async_session_maker", return_value=SessionContext()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # GET user profile by telegram_id
            resp_get = await client.get(f"/api/users/{passenger_user.telegram_id}")
            assert resp_get.status_code == 200
            assert resp_get.json()["telegram_id"] == passenger_user.telegram_id

            # GET non-existent -> 404
            resp_404 = await client.get("/api/users/99999999")
            assert resp_404.status_code == 404

            # PUT update user profile
            resp_put = await client.put(
                f"/api/users/{passenger_user.telegram_id}",
                json={"full_name": "Updated Passenger Name"},
            )
            assert resp_put.status_code == 200
            assert resp_put.json()["full_name"] == "Updated Passenger Name"


@pytest.mark.asyncio
async def test_admin_broadcast_preview_and_send(db_session: AsyncSession, admin_user: User):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    admin_token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Preview broadcast
        resp_preview = await client.post(
            "/api/admin/broadcast/preview",
            json={"target_group": "ALL", "text": "Test broadcast message"},
            headers=headers,
        )
        assert resp_preview.status_code == 200
        assert resp_preview.json()["text"] == "Test broadcast message"

        # Send broadcast
        with patch("app.api.admin.broadcast.run_telegram_broadcast", new_callable=AsyncMock):
            resp_send = await client.post(
                "/api/admin/broadcast/send",
                json={"target_group": "ALL", "text": "Test broadcast message"},
                headers=headers,
            )
            assert resp_send.status_code == 200

    app.dependency_overrides.clear()
