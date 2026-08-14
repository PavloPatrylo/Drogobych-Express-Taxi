import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, Vehicle, Trip, Location, TripStatus
from app.core.security import hash_password
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_admin_auth_endpoints_login_me_staff(db_session: AsyncSession, admin_user: User):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    admin_user.password = hash_password("Secret123!")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Login success
        resp_login = await client.post(
            "/api/admin/auth/login",
            data={"username": admin_user.phone, "password": "Secret123!"},
        )
        assert resp_login.status_code == 200
        token = resp_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Login invalid password -> 401
        resp_bad_login = await client.post(
            "/api/admin/auth/login",
            data={"username": admin_user.phone, "password": "WrongPassword"},
        )
        assert resp_bad_login.status_code == 401

        # 3. GET /api/admin/auth/me
        resp_me = await client.get("/api/admin/auth/me", headers=headers)
        assert resp_me.status_code == 200
        assert resp_me.json()["phone"] == admin_user.phone

        # 4. GET /api/admin/auth/staff
        resp_staff = await client.get("/api/admin/auth/staff", headers=headers)
        assert resp_staff.status_code == 200
        assert isinstance(resp_staff.json(), list)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_admin_vehicles_crud_api(db_session: AsyncSession, admin_user: User):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    admin_token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Create vehicle
        resp_create = await client.post(
            "/api/admin/vehicles",
            json={
                "model": "Mercedes Sprinter",
                "plate_number": "BC7777EX",
                "total_seats": 18,
                "total_standing": 5,
            },
            headers=headers,
        )
        assert resp_create.status_code == 200
        v_id = resp_create.json()["id"]

        # Duplicate plate -> 400
        resp_dup = await client.post(
            "/api/admin/vehicles",
            json={
                "model": "Mercedes Sprinter",
                "plate_number": "BC7777EX",
                "total_seats": 18,
                "total_standing": 5,
            },
            headers=headers,
        )
        assert resp_dup.status_code == 400

        # Update vehicle
        resp_update = await client.put(
            f"/api/admin/vehicles/{v_id}",
            json={
                "model": "Mercedes Sprinter VIP",
                "plate_number": "BC7777EX",
                "total_seats": 20,
                "total_standing": 5,
                "is_active": True,
            },
            headers=headers,
        )
        assert resp_update.status_code == 200
        assert resp_update.json()["model"] == "Mercedes Sprinter VIP"

        # Toggle active status
        resp_toggle = await client.patch(f"/api/admin/vehicles/{v_id}/toggle-active", headers=headers)
        assert resp_toggle.status_code == 200
        assert resp_toggle.json()["is_active"] is False

        # Delete vehicle success
        resp_del = await client.delete(f"/api/admin/vehicles/{v_id}", headers=headers)
        assert resp_del.status_code == 200

        # Delete non-existent -> 404
        resp_del_404 = await client.delete(f"/api/admin/vehicles/{v_id}", headers=headers)
        assert resp_del_404.status_code == 404

    app.dependency_overrides.clear()
