import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.models import User, UserStats, UserRole


@pytest.mark.asyncio
async def test_users_api_get_and_update_profile(db_session: AsyncSession):
    user = User(
        phone="+380971110099",
        full_name="Profile User",
        role=UserRole.PASSENGER,
        telegram_id=44556677,
        is_active=True,
    )
    stats = UserStats(user=user, total_trips=0)
    db_session.add_all([user, stats])
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.api.users.async_session_maker", return_value=SessionContext()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. GET /api/users/{telegram_id}
            resp_get = await client.get(f"/api/users/{user.telegram_id}")
            assert resp_get.status_code == 200
            assert resp_get.json()["full_name"] == "Profile User"

            # 404 for unknown user
            resp_404 = await client.get("/api/users/999999999")
            assert resp_404.status_code == 404

            # 2. PUT /api/users/{telegram_id} (Update Profile)
            resp_put = await client.put(
                f"/api/users/{user.telegram_id}",
                json={"full_name": "Updated Profile User", "phone": "+380971110099"},
            )
            assert resp_put.status_code == 200
            assert resp_put.json()["full_name"] == "Updated Profile User"

            # 404 for update unknown user
            resp_put_404 = await client.put(
                "/api/users/999999999",
                json={"full_name": "Ghost"},
            )
            assert resp_put_404.status_code == 404
