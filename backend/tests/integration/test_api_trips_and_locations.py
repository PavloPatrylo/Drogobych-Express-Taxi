import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import Location, Trip, User, UserRole, Vehicle, TripStatus


@pytest.mark.asyncio
async def test_get_locations_api(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    loc1 = Location(name="Drohobych")
    loc2 = Location(name="Lviv")
    db_session.add_all([loc1, loc2])
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    from unittest.mock import patch, AsyncMock

    with patch("app.db.database.async_session_maker", return_value=SessionContext()), \
         patch("app.api.trips.async_session_maker", return_value=SessionContext()), \
         patch("app.services.reminders.auto_close_expired_trips", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/trips/locations")
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list)
            names = [item["name"] for item in data]
            assert "Drohobych" in names
            assert "Lviv" in names

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_trips_and_detail_api(db_session: AsyncSession, sample_trip: Trip):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    from unittest.mock import patch, AsyncMock

    with patch("app.db.database.async_session_maker", return_value=SessionContext()), \
         patch("app.api.trips.async_session_maker", return_value=SessionContext()), \
         patch("app.services.reminders.auto_close_expired_trips", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Search trips endpoint
            resp_search = await client.get(
                "/api/trips/search",
                params={
                    "from_id": sample_trip.from_location_id,
                    "to_id": sample_trip.to_location_id,
                    "travel_date": "2026-08-15",
                },
            )
            assert resp_search.status_code == 200
            data_search = resp_search.json()
            assert len(data_search) >= 1
            assert data_search[0]["id"] == sample_trip.id

            # Driver manifest endpoint
            driver = User(phone="+380970009988", full_name="Manifest Driver", role=UserRole.DRIVER, telegram_id=888777, is_active=True)
            db_session.add(driver)
            await db_session.commit()

            sample_trip.driver_id = driver.id
            await db_session.commit()

            resp_manifest = await client.get(f"/api/trips/driver/{driver.telegram_id}/manifest?target_date=2026-08-15")
            assert resp_manifest.status_code == 200
            manifest_data = resp_manifest.json()
            assert len(manifest_data) >= 1

            # 403 for non-existent driver
            resp_403 = await client.get("/api/trips/driver/99999999/manifest")
            assert resp_403.status_code == 403

    app.dependency_overrides.clear()
