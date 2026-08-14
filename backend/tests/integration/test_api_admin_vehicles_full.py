import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, Vehicle, Trip, TripStatus
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_admin_vehicles_crud_and_validation(db_session: AsyncSession, admin_user: User, sample_trip: Trip):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. GET /api/admin/vehicles
        resp_list = await client.get("/api/admin/vehicles", headers=headers)
        assert resp_list.status_code == 200

        # 2. POST /api/admin/vehicles (Create)
        resp_create = await client.post(
            "/api/admin/vehicles",
            json={
                "plate_number": "BC7788KX",
                "model": "Mercedes Benz",
                "total_seats": 19,
                "total_standing": 4,
                "is_active": True,
            },
            headers=headers,
        )
        assert resp_create.status_code == 200
        v_id = resp_create.json()["id"]

        # Duplicate plate error
        resp_dup = await client.post(
            "/api/admin/vehicles",
            json={
                "plate_number": "BC7788KX",
                "model": "Duplicate",
                "total_seats": 10,
                "total_standing": 2,
                "is_active": True,
            },
            headers=headers,
        )
        assert resp_dup.status_code == 400

        # 3. PUT /api/admin/vehicles/{id} (Update)
        resp_upd = await client.put(
            f"/api/admin/vehicles/{v_id}",
            json={
                "plate_number": "BC7788KX",
                "model": "Mercedes Benz Sprinter 316",
                "total_seats": 20,
                "total_standing": 5,
                "is_active": True,
            },
            headers=headers,
        )
        assert resp_upd.status_code == 200
        assert resp_upd.json()["model"] == "Mercedes Benz Sprinter 316"

        # Update vehicle duplicate plate error (matching sample_trip vehicle plate number "BC1234AB")
        resp_upd_dup = await client.put(
            f"/api/admin/vehicles/{v_id}",
            json={
                "plate_number": "BC1234AB",
                "model": "Mercedes Benz Sprinter 316",
                "total_seats": 20,
                "total_standing": 5,
                "is_active": True,
            },
            headers=headers,
        )
        assert resp_upd_dup.status_code == 400

        # Update vehicle 404
        resp_upd_404 = await client.put(
            "/api/admin/vehicles/99999",
            json={
                "plate_number": "BC9999ZZ",
                "model": "Ghost Bus",
                "total_seats": 20,
                "total_standing": 5,
                "is_active": True,
            },
            headers=headers,
        )
        assert resp_upd_404.status_code == 404

        # 4. PATCH /api/admin/vehicles/{id}/toggle-active
        resp_toggle = await client.patch(f"/api/admin/vehicles/{v_id}/toggle-active", headers=headers)
        assert resp_toggle.status_code == 200
        assert resp_toggle.json()["is_active"] is False

        # Toggle 404
        resp_toggle_404 = await client.patch("/api/admin/vehicles/99999/toggle-active", headers=headers)
        assert resp_toggle_404.status_code == 404

        # Delete 404
        resp_del_404 = await client.delete("/api/admin/vehicles/99999", headers=headers)
        assert resp_del_404.status_code == 404

        # 5. DELETE /api/admin/vehicles/{id} (Delete vehicle without trip)
        resp_del = await client.delete(f"/api/admin/vehicles/{v_id}", headers=headers)
        assert resp_del.status_code == 200

        # 6. DELETE vehicle with linked trip fails
        v_linked = Vehicle(model="Linked Bus", plate_number="BC0011XX", total_seats=15, total_standing=2, is_active=True)
        db_session.add(v_linked)
        await db_session.commit()

        sample_trip.vehicle_id = v_linked.id
        await db_session.commit()

        resp_del_linked = await client.delete(f"/api/admin/vehicles/{v_linked.id}", headers=headers)
        assert resp_del_linked.status_code == 400
