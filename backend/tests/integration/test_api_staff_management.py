import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_staff_management_crud_api(db_session: AsyncSession, admin_user: User):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Create staff member (Driver)
        resp_create = await client.post(
            "/api/admin/auth/staff",
            json={
                "full_name": "New Staff Driver",
                "phone": "+380971239900",
                "role": "driver",
                "password": "Password123!",
            },
            headers=headers,
        )
        assert resp_create.status_code == 200
        staff_id = resp_create.json()["id"]

        # 2. Duplicate phone error -> 400
        resp_dup = await client.post(
            "/api/admin/auth/staff",
            json={
                "full_name": "New Staff Driver 2",
                "phone": "+380971239900",
                "role": "driver",
                "password": "Password123!",
            },
            headers=headers,
        )
        assert resp_dup.status_code == 400

        # 3. Update staff member
        resp_update = await client.put(
            f"/api/admin/auth/staff/{staff_id}",
            json={
                "full_name": "Updated Staff Dispatcher",
                "phone": "+380971239900",
                "role": "dispatcher",
            },
            headers=headers,
        )
        assert resp_update.status_code == 200
        assert resp_update.json()["full_name"] == "Updated Staff Dispatcher"

        # 4. Block staff member
        resp_block = await client.post(f"/api/admin/auth/staff/{staff_id}/block", headers=headers)
        assert resp_block.status_code == 200
        assert resp_block.json()["is_active"] is False

        # 5. Unblock staff member
        resp_unblock = await client.post(f"/api/admin/auth/staff/{staff_id}/unblock", headers=headers)
        assert resp_unblock.status_code == 200
        assert resp_unblock.json()["is_active"] is True

        # 6. Delete staff member
        resp_del = await client.delete(f"/api/admin/auth/staff/{staff_id}", headers=headers)
        assert resp_del.status_code == 200

        # 7. Delete non-existent -> 404
        resp_del_404 = await client.delete(f"/api/admin/auth/staff/{staff_id}", headers=headers)
        assert resp_del_404.status_code == 404

    app.dependency_overrides.clear()
