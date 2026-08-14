import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.models import User, UserRole, Trip, TripStatus, Booking, BookingType, BookingSource, BookingStatus, Location, Vehicle


@pytest.mark.asyncio
async def test_trips_public_locations_and_search(db_session: AsyncSession, sample_trip: Trip):
    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.api.trips.async_session_maker", return_value=SessionContext()):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. GET /api/trips/locations
            resp_locs = await client.get("/api/trips/locations")
            assert resp_locs.status_code == 200
            assert len(resp_locs.json()) >= 2

            # 2. GET /api/trips/search
            travel_date = sample_trip.departure_time.strftime("%Y-%m-%d")
            resp_search = await client.get(
                "/api/trips/search",
                params={
                    "from_id": sample_trip.from_location_id,
                    "to_id": sample_trip.to_location_id,
                    "travel_date": travel_date,
                },
            )
            assert resp_search.status_code == 200
            assert isinstance(resp_search.json(), list)


@pytest.mark.asyncio
async def test_driver_manifest_summary_and_schedule(db_session: AsyncSession, sample_trip: Trip):
    driver = User(
        phone="+380971239988",
        full_name="Driver Manifest",
        role=UserRole.DRIVER,
        telegram_id=987654321,
        is_active=True,
    )
    vehicle = Vehicle(model="Mercedes Sprinter", plate_number="BC5544AA", total_seats=18, total_standing=4, is_active=True)
    db_session.add_all([driver, vehicle])
    await db_session.commit()

    sample_trip.driver_id = driver.id
    sample_trip.vehicle_id = vehicle.id
    sample_trip.status = TripStatus.SCHEDULED
    await db_session.commit()

    booking = Booking(
        trip_id=sample_trip.id,
        passenger_id=None,
        created_by_id=driver.id,
        source=BookingSource.DRIVER,
        booking_type=BookingType.SEATED,
        status=BookingStatus.BOARDED,
        passengers_count=2,
        amount_paid=240.0,
    )
    db_session.add(booking)
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    target_date_str = sample_trip.departure_time.strftime("%Y-%m-%d")

    with patch("app.api.trips.async_session_maker", return_value=SessionContext()), \
         patch("app.services.reminders.auto_close_expired_trips", new_callable=AsyncMock), \
         patch("app.api.trips.manager.broadcast", new_callable=AsyncMock):

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Driver Manifest GET
            resp_man = await client.get(
                f"/api/trips/driver/{driver.telegram_id}/manifest",
                params={"target_date": target_date_str},
            )
            assert resp_man.status_code == 200
            assert len(resp_man.json()) >= 1

            # 403 for non-existent driver
            resp_man_403 = await client.get("/api/trips/driver/99999999/manifest")
            assert resp_man_403.status_code == 403

            # 2. Driver Status Update PATCH
            resp_status = await client.patch(
                f"/api/trips/{sample_trip.id}/status",
                params={"telegram_id": driver.telegram_id},
                json={"status": "BOARDING"},
            )
            assert resp_status.status_code == 200

            # 3. Driver Summary GET
            sample_trip.status = TripStatus.COMPLETED
            await db_session.commit()

            resp_sum = await client.get(
                f"/api/trips/driver/{driver.telegram_id}/summary",
                params={"target_date": target_date_str},
            )
            assert resp_sum.status_code == 200
            assert resp_sum.json()["total_sum"] >= 0

            # 4. Driver Published Schedule GET
            resp_pub = await client.get(
                f"/api/trips/driver/{driver.telegram_id}/published-schedule",
                params={"date_from": target_date_str, "date_to": target_date_str},
            )
            assert resp_pub.status_code == 200
            assert resp_pub.json()["driver_name"] == driver.full_name
