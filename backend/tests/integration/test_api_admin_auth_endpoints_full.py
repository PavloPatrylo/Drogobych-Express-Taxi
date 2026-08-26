from datetime import datetime
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, Trip, TripStatus, Vehicle
from app.core.security import hash_password
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_admin_auth_full_routes(db_session: AsyncSession, admin_user: User):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # 1. Login POST /api/admin/auth/login
    admin_user.password = hash_password("secret123")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        resp_login = await client.post(
            "/api/admin/auth/login",
            data={"username": admin_user.phone, "password": "secret123"},
        )
        assert resp_login.status_code == 200
        token = resp_login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. GET /api/admin/auth/me
        resp_me = await client.get("/api/admin/auth/me", headers=headers)
        assert resp_me.status_code == 200
        assert resp_me.json()["id"] == admin_user.id

        # 3. GET /api/admin/auth/staff
        resp_staff = await client.get("/api/admin/auth/staff", headers=headers)
        assert resp_staff.status_code == 200

        # 4. POST /api/admin/auth/staff (Create Staff)
        resp_create = await client.post(
            "/api/admin/auth/staff",
            json={
                "full_name": "New Dispatcher",
                "phone": "0975556677",
                "role": "dispatcher",
                "password": "pass12345",
            },
            headers=headers,
        )
        assert resp_create.status_code == 200
        staff_id = resp_create.json()["id"]

        # Duplicate phone error
        resp_dup = await client.post(
            "/api/admin/auth/staff",
            json={
                "full_name": "Duplicate Dispatcher",
                "phone": "0975556677",
                "role": "dispatcher",
                "password": "pass12345",
            },
            headers=headers,
        )
        assert resp_dup.status_code == 400

        # 5. PUT /api/admin/auth/staff/{id} (Update Staff)
        resp_upd = await client.put(
            f"/api/admin/auth/staff/{staff_id}",
            json={
                "full_name": "Senior Dispatcher",
                "phone": "0975556677",
                "role": "dispatcher",
            },
            headers=headers,
        )
        assert resp_upd.status_code == 200
        assert resp_upd.json()["full_name"] == "Senior Dispatcher"

        # Update staff duplicate phone error (phone matching another user admin_user.phone)
        resp_upd_dup = await client.put(
            f"/api/admin/auth/staff/{staff_id}",
            json={
                "full_name": "Senior Dispatcher",
                "phone": admin_user.phone,
                "role": "dispatcher",
            },
            headers=headers,
        )
        assert resp_upd_dup.status_code == 400

        # Update staff 404
        resp_upd_404 = await client.put(
            "/api/admin/auth/staff/99999",
            json={
                "full_name": "Ghost",
                "phone": "0970009999",
                "role": "dispatcher",
            },
            headers=headers,
        )
        assert resp_upd_404.status_code == 404

        # 6. POST /api/admin/auth/staff/{id}/block
        resp_block = await client.post(f"/api/admin/auth/staff/{staff_id}/block", headers=headers)
        assert resp_block.status_code == 200
        assert resp_block.json()["is_active"] is False

        # Block 404
        resp_block_404 = await client.post("/api/admin/auth/staff/99999/block", headers=headers)
        assert resp_block_404.status_code == 404

        # 7. POST /api/admin/auth/staff/{id}/unblock
        resp_unblock = await client.post(f"/api/admin/auth/staff/{staff_id}/unblock", headers=headers)
        assert resp_unblock.status_code == 200
        assert resp_unblock.json()["is_active"] is True

        # Unblock 404
        resp_unblock_404 = await client.post("/api/admin/auth/staff/99999/unblock", headers=headers)
        assert resp_unblock_404.status_code == 404

        # 8. Delete driver with assigned trip conflict
        driver_with_trip = User(
            full_name="Driver With Trip",
            phone="+380975558899",
            role=UserRole.DRIVER,
            is_active=True,
        )
        db_session.add(driver_with_trip)
        await db_session.commit()

        vehicle_del = Vehicle(model="Del Bus", plate_number="BC9999DL", total_seats=18, total_standing=4, is_active=True)
        db_session.add(vehicle_del)
        await db_session.commit()

        trip = Trip(
            driver_id=driver_with_trip.id,
            vehicle_id=vehicle_del.id,
            from_location_id=1,
            to_location_id=2,
            departure_time=datetime(2027, 5, 1, 10, 0),
            arrival_time=datetime(2027, 5, 1, 12, 0),
            status=TripStatus.SCHEDULED,
            seats_limit_snapshot=18,
            standing_limit_snapshot=4,
            price_seated=150.0,
            price_standing=100.0,
            price_parcel=80.0,
        )
        db_session.add(trip)
        await db_session.commit()

        resp_del_conflict = await client.delete(f"/api/admin/auth/staff/{driver_with_trip.id}", headers=headers)
        assert resp_del_conflict.status_code == 200
        assert resp_del_conflict.json()["is_active"] is False

        # 9. DELETE /api/admin/auth/staff/{id}
        resp_del = await client.delete(f"/api/admin/auth/staff/{staff_id}", headers=headers)
        assert resp_del.status_code == 200

        # 404 for deleted staff
        resp_404 = await client.delete(f"/api/admin/auth/staff/{staff_id}", headers=headers)
        assert resp_404.status_code == 404
