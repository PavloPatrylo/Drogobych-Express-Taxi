import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, Vehicle, Location
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_admin_api_endpoints_permissions_and_success(
    db_session: AsyncSession, admin_user: User, passenger_user: User
):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    admin_token = create_access_token(admin_user.id, admin_user.role)
    passenger_token = create_access_token(passenger_user.id, passenger_user.role)

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_passenger = {"Authorization": f"Bearer {passenger_token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. No token -> 401 Unauthorized
        resp_no_token = await client.get("/api/admin/vehicles")
        assert resp_no_token.status_code == 401

        # 2. Invalid token -> 401 Unauthorized
        resp_invalid_token = await client.get("/api/admin/vehicles", headers={"Authorization": "Bearer invalid.jwt.token"})
        assert resp_invalid_token.status_code == 401

        # 3. Passenger token -> 403 Forbidden
        resp_forbidden = await client.get("/api/admin/vehicles", headers=headers_passenger)
        assert resp_forbidden.status_code == 403

        # 4. Admin token -> 200 OK for vehicles
        resp_vehicles = await client.get("/api/admin/vehicles", headers=headers_admin)
        assert resp_vehicles.status_code == 200

        # Add vehicle via admin POST
        resp_add_vehicle = await client.post(
            "/api/admin/vehicles",
            json={
                "model": "Ford Transit",
                "plate_number": "BC0001AA",
                "total_seats": 16,
                "total_standing": 4,
            },
            headers=headers_admin,
        )
        assert resp_add_vehicle.status_code == 200
        assert resp_add_vehicle.json()["model"] == "Ford Transit"

        # 5. CRM Passengers endpoint
        resp_crm = await client.get("/api/admin/passengers", headers=headers_admin)
        assert resp_crm.status_code == 200

        # 6. Finance summary endpoint
        resp_finance = await client.get("/api/admin/finance/summary", headers=headers_admin)
        assert resp_finance.status_code == 200

        # 7. Audit log endpoint
        resp_audit = await client.get("/api/admin/audit/log", headers=headers_admin)
        assert resp_audit.status_code == 200

        # 8. Schedule templates endpoint
        resp_schedule = await client.get("/api/admin/templates", headers=headers_admin)
        assert resp_schedule.status_code == 200

    app.dependency_overrides.clear()
