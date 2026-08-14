import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, Trip, TripStatus
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_finance_reports_and_csv_exports_api(db_session: AsyncSession, admin_user: User, sample_trip: Trip):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # Drivers report
        resp_drivers = await client.get("/api/admin/finance/reports/drivers", headers=headers)
        assert resp_drivers.status_code == 200

        # Vehicles report
        resp_vehicles = await client.get("/api/admin/finance/reports/vehicles", headers=headers)
        assert resp_vehicles.status_code == 200

        # Drivers reconciliation
        resp_recon = await client.get("/api/admin/finance/reconciliation", headers=headers)
        assert resp_recon.status_code == 200

        # Confirm driver cash
        driver = User(phone="+380971112233", full_name="Fin Driver", role=UserRole.DRIVER, is_active=True)
        db_session.add(driver)
        await db_session.commit()

        sample_trip.driver_id = driver.id
        sample_trip.status = TripStatus.COMPLETED
        await db_session.commit()

        resp_confirm = await client.post(
            "/api/admin/finance/confirm-driver-cash",
            json={
                "driver_id": driver.id,
                "target_date": "2026-08-15",
                "received_cash": 150.0,
                "received_card": 50.0,
                "comment": "Confirmed by dispatcher",
            },
            headers=headers,
        )
        assert resp_confirm.status_code == 200

        # CSV Drivers Export
        resp_csv_drivers = await client.get("/api/admin/finance/export/drivers-csv", headers=headers)
        assert resp_csv_drivers.status_code == 200
        assert "text/csv" in resp_csv_drivers.headers["content-type"]

        # CSV Trips Export
        resp_csv_trips = await client.get("/api/admin/finance/export/trips-csv", headers=headers)
        assert resp_csv_trips.status_code == 200

        # CSV Parcels Export
        resp_csv_parcels = await client.get("/api/admin/finance/export/parcels-csv", headers=headers)
        assert resp_csv_parcels.status_code == 200

        # Trip stats
        resp_stats = await client.get(f"/api/admin/finance/trips/{sample_trip.id}/stats", headers=headers)
        assert resp_stats.status_code == 200

        # Closures history
        resp_closures = await client.get("/api/admin/finance/closures-history", headers=headers)
        assert resp_closures.status_code == 200

    app.dependency_overrides.clear()
