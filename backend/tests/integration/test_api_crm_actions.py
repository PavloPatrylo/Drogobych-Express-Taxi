import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_crm_passenger_block_unblock_toggle_api(
    db_session: AsyncSession, admin_user: User, passenger_user: User
):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Block passenger
        resp_block = await client.post(f"/api/admin/passengers/{passenger_user.id}/block", headers=headers)
        assert resp_block.status_code == 200
        assert resp_block.json()["is_active"] is False

        # Unblock passenger
        resp_unblock = await client.post(f"/api/admin/passengers/{passenger_user.id}/unblock", headers=headers)
        assert resp_unblock.status_code == 200
        assert resp_unblock.json()["is_active"] is True

        # Toggle passenger status
        resp_toggle = await client.post(f"/api/admin/passengers/{passenger_user.id}/toggle-status", headers=headers)
        assert resp_toggle.status_code == 200

        # Change role to driver and back to passenger
        resp_role = await client.post(f"/api/admin/passengers/{passenger_user.id}/role", json={"role": "driver"}, headers=headers)
        assert resp_role.status_code == 200
        assert resp_role.json()["role"] == "driver"

        resp_demote = await client.post(f"/api/admin/passengers/{passenger_user.id}/role", json={"role": "passenger"}, headers=headers)
        assert resp_demote.status_code == 200
        assert resp_demote.json()["role"] == "passenger"

    app.dependency_overrides.clear()
