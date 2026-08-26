import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.models import (
    User,
    UserRole,
    Trip,
    TripStatus,
    Booking,
    BookingType,
    BookingSource,
    BookingStatus,
    Location,
    Vehicle,
    PaymentMethod,
    SystemConfig,
)
from app.core.config import settings


class AsyncSessionContextManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_session_cm(db_session: AsyncSession):
    return AsyncSessionContextManager(db_session)


@pytest.mark.asyncio
async def test_api_trips_search_and_locations(db_session: AsyncSession, mock_session_cm):
    loc_from = Location(name="Drohobych Deep")
    loc_to = Location(name="Lviv Deep")
    db_session.add_all([loc_from, loc_to])
    await db_session.commit()

    driver = User(phone="+380971112233", full_name="Deep Driver", role=UserRole.DRIVER, is_active=True)
    vehicle = Vehicle(model="Sprinter Deep", plate_number="BC9999DP", total_seats=18, total_standing=4, is_active=True)
    db_session.add_all([driver, vehicle])
    await db_session.commit()

    dep = datetime.now(timezone.utc) + timedelta(days=2)
    arr = dep + timedelta(hours=2)
    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=loc_from.id,
        to_location_id=loc_to.id,
        departure_time=dep,
        arrival_time=arr,
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=4,
        price_seated=150.0,
        price_standing=100.0,
        price_parcel=80.0,
    )
    db_session.add(trip)
    await db_session.commit()

    with patch("app.api.trips.async_session_maker", return_value=mock_session_cm):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp1 = await client.get("/api/trips/locations")
            assert resp1.status_code == 200

            travel_date_str = dep.strftime("%Y-%m-%d")
            resp2 = await client.get(f"/api/trips/search?from_id={loc_from.id}&to_id={loc_to.id}&travel_date={travel_date_str}")
            assert resp2.status_code == 200
            data = resp2.json()
            assert len(data) >= 1


from app.services.auth_service import create_access_token

@pytest.mark.asyncio
async def test_api_trips_driver_manifest_and_status_update(db_session: AsyncSession, mock_session_cm):
    loc_from = Location(name="Drohobych M")
    loc_to = Location(name="Lviv M")
    driver = User(phone="+380972223344", full_name="Manifest Driver", telegram_id=990011, role=UserRole.DRIVER, is_active=True)
    vehicle = Vehicle(model="Sprinter M", plate_number="BC8888M", total_seats=18, total_standing=4, is_active=True)
    db_session.add_all([loc_from, loc_to, driver, vehicle])
    await db_session.commit()
    token = create_access_token(driver.id, driver.role)
    headers = {"Authorization": f"Bearer {token}"}

    dep = datetime.now(timezone.utc) + timedelta(hours=3)
    arr = dep + timedelta(hours=2)
    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=loc_from.id,
        to_location_id=loc_to.id,
        departure_time=dep,
        arrival_time=arr,
        status=TripStatus.BOARDING,
        seats_limit_snapshot=18,
        standing_limit_snapshot=4,
        price_seated=150.0,
        price_standing=100.0,
        price_parcel=80.0,
    )
    db_session.add(trip)
    await db_session.commit()

    with (
        patch("app.api.deps.async_session_maker", return_value=mock_session_cm),
        patch("app.api.trips.async_session_maker", return_value=mock_session_cm),
        patch("app.services.reminders.async_session_maker", return_value=mock_session_cm),
        patch("app.websocket_manager.manager.broadcast", AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            target_date_str = dep.strftime("%Y-%m-%d")
            # Get driver manifest
            resp_m = await client.get(f"/api/trips/driver/{driver.telegram_id}/manifest?target_date={target_date_str}", headers=headers)
            assert resp_m.status_code == 200

            # Update status to ACTIVE via PATCH /api/trips/{trip_id}/status
            resp_st1 = await client.patch(f"/api/trips/{trip.id}/status?telegram_id={driver.telegram_id}", json={
                "status": "ACTIVE"
            }, headers=headers)
            assert resp_st1.status_code == 200

            # Get driver summary
            resp_sum = await client.get(f"/api/trips/driver/{driver.telegram_id}/summary", headers=headers)
            assert resp_sum.status_code == 200


@pytest.mark.asyncio
async def test_api_bookings_full_lifecycle(db_session: AsyncSession, mock_session_cm):
    loc_from = Location(name="Drohobych B")
    loc_to = Location(name="Lviv B")
    pax = User(phone="+380973334455", full_name="Pax Booking", telegram_id=881122, role=UserRole.PASSENGER, is_active=True)
    driver = User(phone="+380973334456", full_name="Driver Booking", telegram_id=881123, role=UserRole.DRIVER, is_active=True)
    vehicle = Vehicle(model="Sprinter B", plate_number="BC7777B", total_seats=18, total_standing=4, is_active=True)
    db_session.add_all([loc_from, loc_to, pax, driver, vehicle])
    await db_session.commit()

    pax_token = create_access_token(pax.id, pax.role)
    pax_headers = {"Authorization": f"Bearer {pax_token}"}
    driver_token = create_access_token(driver.id, driver.role)
    driver_headers = {"Authorization": f"Bearer {driver_token}"}

    dep = datetime.now(timezone.utc) + timedelta(days=1)
    arr = dep + timedelta(hours=2)
    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=loc_from.id,
        to_location_id=loc_to.id,
        departure_time=dep,
        arrival_time=arr,
        status=TripStatus.BOARDING,
        seats_limit_snapshot=2,  # set snapshot equal to booked seats so no free seated seats remain
        standing_limit_snapshot=4,
        price_seated=150.0,
        price_standing=100.0,
        price_parcel=80.0,
    )
    db_session.add(trip)
    await db_session.commit()

    with patch("app.api.deps.async_session_maker", return_value=mock_session_cm), \
         patch("app.api.bookings.async_session_maker", return_value=mock_session_cm):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create passenger booking
            payload = {
                "telegram_id": pax.telegram_id,
                "trip_id": trip.id,
                "requested_seats": 2,
                "payment_method": "CASH"
            }
            resp_b = await client.post("/api/bookings/", json=payload, headers=pax_headers)
            assert resp_b.status_code == 200

            # User bookings list
            resp_ub = await client.get(f"/api/bookings/my/{pax.telegram_id}", headers=pax_headers)
            assert resp_ub.status_code == 200
            bookings_list = resp_ub.json()
            assert len(bookings_list) == 2
            booking_id = bookings_list[0]["id"]

            # Quick sale standing by driver (now allowed because 0 free seated seats remain)
            resp_st = await client.post("/api/bookings/standing", json={
                "telegram_id": driver.telegram_id,
                "trip_id": trip.id
            }, headers=driver_headers)
            assert resp_st.status_code == 200

            # Quick sale parcel by driver
            resp_pr = await client.post("/api/bookings/parcel", json={
                "telegram_id": driver.telegram_id,
                "trip_id": trip.id,
                "description": "Box of papers",
                "price": 80.0
            }, headers=driver_headers)
            assert resp_pr.status_code == 200

            # Cancel passenger booking
            resp_can = await client.patch(f"/api/bookings/{booking_id}/cancel?telegram_id={pax.telegram_id}", headers=pax_headers)
            assert resp_can.status_code == 200
