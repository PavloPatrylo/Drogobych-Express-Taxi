import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import (
    User, UserRole, Trip, Location, Vehicle, Booking, BookingType, BookingStatus, BookingSource, PaymentMethod, TripStatus
)


class SingleSessionContextManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def session_cm(db_session: AsyncSession):
    return SingleSessionContextManager(db_session)


from app.services.auth_service import create_access_token

@pytest.mark.asyncio
async def test_bookings_create_validation_and_errors(db_session: AsyncSession, session_cm):
    with (
        patch("app.api.deps.async_session_maker", return_value=session_cm),
        patch("app.api.bookings.async_session_maker", return_value=session_cm),
        patch("app.api.trips.async_session_maker", return_value=session_cm),
        patch("app.services.reminders.async_session_maker", return_value=session_cm),
        patch("app.websocket_manager.manager.broadcast", AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Unauthenticated request -> 401
            resp_no_user = await client.post(
                "/api/bookings/",
                json={"telegram_id": 999888777, "trip_id": 1, "requested_seats": 1}
            )
            assert resp_no_user.status_code == 401

            # Register user
            user = User(full_name="Booking User", phone="+380971112233", telegram_id=987654321, role=UserRole.PASSENGER, is_active=True)
            db_session.add(user)
            await db_session.commit()
            token = create_access_token(user.id, user.role)
            headers = {"Authorization": f"Bearer {token}"}

            # 2. Trip not found (trip_id does not exist)
            resp_no_trip = await client.post(
                "/api/bookings/",
                json={"telegram_id": 987654321, "trip_id": 99999, "requested_seats": 1},
                headers=headers,
            )
            assert resp_no_trip.status_code == 404
            assert "Рейс не знайдено" in resp_no_trip.json()["detail"]

            # Create locations and vehicle
            loc1 = Location(name="City A")
            loc2 = Location(name="City B")
            veh = Vehicle(model="Sprinter", plate_number="BC1111AA", total_seats=15, total_standing=3, is_active=True)
            db_session.add_all([loc1, loc2, veh])
            await db_session.commit()

            # 3. Trip in the past error
            past_trip = Trip(
                driver_id=user.id,
                vehicle_id=veh.id,
                from_location_id=loc1.id,
                to_location_id=loc2.id,
                departure_time=datetime.now(timezone.utc) - timedelta(hours=2),
                arrival_time=datetime.now(timezone.utc) - timedelta(hours=1),
                status=TripStatus.SCHEDULED,
                seats_limit_snapshot=15,
                standing_limit_snapshot=3,
                price_seated=150.0,
                price_standing=100.0,
                price_parcel=80.0,
            )
            db_session.add(past_trip)
            await db_session.commit()

            resp_past = await client.post(
                "/api/bookings/",
                json={"telegram_id": 987654321, "trip_id": past_trip.id, "requested_seats": 1},
                headers=headers,
            )
            assert resp_past.status_code == 400
            assert "вже виїхав" in resp_past.json()["detail"]

            # 4. Valid future trip but status COMPLETED
            comp_trip = Trip(
                driver_id=user.id,
                vehicle_id=veh.id,
                from_location_id=loc1.id,
                to_location_id=loc2.id,
                departure_time=datetime.now(timezone.utc) + timedelta(hours=5),
                arrival_time=datetime.now(timezone.utc) + timedelta(hours=7),
                status=TripStatus.COMPLETED,
                seats_limit_snapshot=15,
                standing_limit_snapshot=3,
                price_seated=150.0,
                price_standing=100.0,
                price_parcel=80.0,
            )
            db_session.add(comp_trip)
            await db_session.commit()

            resp_comp = await client.post(
                "/api/bookings/",
                json={"telegram_id": 987654321, "trip_id": comp_trip.id, "requested_seats": 1},
                headers=headers,
            )
            assert resp_comp.status_code == 400
            assert "вже вирушив або завершений" in resp_comp.json()["detail"]

            # 5. Future scheduled trip - overbooking seats check
            fut_trip = Trip(
                driver_id=user.id,
                vehicle_id=veh.id,
                from_location_id=loc1.id,
                to_location_id=loc2.id,
                departure_time=datetime.now(timezone.utc) + timedelta(hours=5),
                arrival_time=datetime.now(timezone.utc) + timedelta(hours=7),
                status=TripStatus.SCHEDULED,
                seats_limit_snapshot=2,
                standing_limit_snapshot=3,
                price_seated=150.0,
                price_standing=100.0,
                price_parcel=80.0,
            )
            db_session.add(fut_trip)
            await db_session.commit()

            resp_over = await client.post(
                "/api/bookings/",
                json={"telegram_id": 987654321, "trip_id": fut_trip.id, "requested_seats": 5},
                headers=headers,
            )
            assert resp_over.status_code == 400
            assert "місця щойно закінчилися" in resp_over.json()["detail"]

            # 6. Successful booking with CARD payment method
            resp_ok = await client.post(
                "/api/bookings/",
                json={"telegram_id": 987654321, "trip_id": fut_trip.id, "requested_seats": 2, "payment_method": "CARD"},
                headers=headers,
            )
            assert resp_ok.status_code == 200
            assert "Успішно заброньовано 2 місць" in resp_ok.json()["message"]


@pytest.mark.asyncio
async def test_my_bookings_and_cancel_flow(db_session: AsyncSession, session_cm):
    with (
        patch("app.api.deps.async_session_maker", return_value=session_cm),
        patch("app.api.bookings.async_session_maker", return_value=session_cm),
        patch("app.api.trips.async_session_maker", return_value=session_cm),
        patch("app.services.reminders.async_session_maker", return_value=session_cm),
        patch("app.websocket_manager.manager.broadcast", AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Register user & trip & booking
            user = User(full_name="My Booking User", phone="+380972223344", telegram_id=999111222, role=UserRole.PASSENGER, is_active=True)
            loc1 = Location(name="City A")
            loc2 = Location(name="City B")
            veh = Vehicle(model="Sprinter", plate_number="BC2222BB", total_seats=15, total_standing=3, is_active=True)
            db_session.add_all([user, loc1, loc2, veh])
            await db_session.commit()
            token = create_access_token(user.id, user.role)
            headers = {"Authorization": f"Bearer {token}"}

            trip = Trip(
                driver_id=user.id,
                vehicle_id=veh.id,
                from_location_id=loc1.id,
                to_location_id=loc2.id,
                departure_time=datetime.now(timezone.utc) + timedelta(hours=5),
                arrival_time=datetime.now(timezone.utc) + timedelta(hours=7),
                status=TripStatus.SCHEDULED,
                seats_limit_snapshot=15,
                standing_limit_snapshot=3,
                price_seated=150.0,
                price_standing=100.0,
                price_parcel=80.0,
            )
            db_session.add(trip)
            await db_session.commit()

            booking = Booking(
                trip_id=trip.id,
                passenger_id=user.id,
                created_by_id=user.id,
                booking_type=BookingType.SEATED,
                source=BookingSource.BOT,
                status=BookingStatus.RESERVED,
                payment_method=PaymentMethod.CASH,
                passengers_count=1,
                amount_paid=150.0,
            )
            db_session.add(booking)
            await db_session.commit()

            # Get my bookings - success
            resp_my = await client.get(f"/api/bookings/my/{user.telegram_id}", headers=headers)
            assert resp_my.status_code == 200
            assert len(resp_my.json()) == 1

            # Cancel booking - booking not found 404
            resp_cancel_404 = await client.patch(f"/api/bookings/99999/cancel?telegram_id={user.telegram_id}", headers=headers)
            assert resp_cancel_404.status_code == 404

            # Cancel booking - unauthorized user 403 / 401
            resp_cancel_403 = await client.patch(f"/api/bookings/{booking.id}/cancel?telegram_id=999888000")
            assert resp_cancel_403.status_code in (401, 403)

            # Cancel booking - success
            resp_cancel_ok = await client.patch(f"/api/bookings/{booking.id}/cancel?telegram_id={user.telegram_id}", headers=headers)
            assert resp_cancel_ok.status_code == 200
            assert "скасовано" in resp_cancel_ok.json()["message"]


@pytest.mark.asyncio
async def test_standing_and_parcel_quick_sales(db_session: AsyncSession, session_cm):
    with (
        patch("app.api.deps.async_session_maker", return_value=session_cm),
        patch("app.api.bookings.async_session_maker", return_value=session_cm),
        patch("app.api.trips.async_session_maker", return_value=session_cm),
        patch("app.services.reminders.async_session_maker", return_value=session_cm),
        patch("app.websocket_manager.manager.broadcast", AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            driver = User(full_name="Driver Quick", phone="+380973334455", telegram_id=888777666, role=UserRole.DRIVER, is_active=True)
            loc1 = Location(name="City A")
            loc2 = Location(name="City B")
            veh = Vehicle(model="Sprinter", plate_number="BC3333CC", total_seats=0, total_standing=1, is_active=True)
            db_session.add_all([driver, loc1, loc2, veh])
            await db_session.commit()
            token = create_access_token(driver.id, driver.role)
            headers = {"Authorization": f"Bearer {token}"}

            trip = Trip(
                driver_id=driver.id,
                vehicle_id=veh.id,
                from_location_id=loc1.id,
                to_location_id=loc2.id,
                departure_time=datetime.now(timezone.utc) + timedelta(hours=3),
                arrival_time=datetime.now(timezone.utc) + timedelta(hours=5),
                status=TripStatus.BOARDING,
                seats_limit_snapshot=0,
                standing_limit_snapshot=1,
                price_seated=150.0,
                price_standing=100.0,
                price_parcel=80.0,
            )
            db_session.add(trip)
            await db_session.commit()

            # 1. Add standing passenger - trip not found 404
            resp_st_404 = await client.post(
                "/api/bookings/standing",
                json={"trip_id": 99999, "telegram_id": driver.telegram_id},
                headers=headers,
            )
            assert resp_st_404.status_code == 404

            # 2. Add standing passenger - success
            resp_st_ok = await client.post(
                "/api/bookings/standing",
                json={"trip_id": trip.id, "telegram_id": driver.telegram_id},
                headers=headers,
            )
            assert resp_st_ok.status_code == 200

            # 3. Add standing passenger - limit exceeded 400
            resp_st_exceeded = await client.post(
                "/api/bookings/standing",
                json={"trip_id": trip.id, "telegram_id": driver.telegram_id},
                headers=headers,
            )
            assert resp_st_exceeded.status_code == 400

            # 4. Add parcel - success
            resp_prc_ok = await client.post(
                "/api/bookings/parcel",
                json={"trip_id": trip.id, "telegram_id": driver.telegram_id, "description": "Parcel", "price": 80.0},
                headers=headers,
            )
            assert resp_prc_ok.status_code == 200
            assert "message" in resp_prc_ok.json()


@pytest.mark.asyncio
async def test_trips_search_and_driver_endpoints(db_session: AsyncSession, session_cm):
    with (
        patch("app.api.deps.async_session_maker", return_value=session_cm),
        patch("app.api.bookings.async_session_maker", return_value=session_cm),
        patch("app.api.trips.async_session_maker", return_value=session_cm),
        patch("app.services.reminders.async_session_maker", return_value=session_cm),
        patch("app.websocket_manager.manager.broadcast", AsyncMock()),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            driver = User(full_name="Driver Manifest", phone="+380974445566", telegram_id=777666555, role=UserRole.DRIVER, is_active=True)
            loc1 = Location(name="Drohobych")
            loc2 = Location(name="Lviv")
            veh = Vehicle(model="Sprinter", plate_number="BC4444DD", total_seats=18, total_standing=4, is_active=True)
            db_session.add_all([driver, loc1, loc2, veh])
            await db_session.commit()
            token = create_access_token(driver.id, driver.role)
            headers = {"Authorization": f"Bearer {token}"}

            dep_dt = datetime.now(timezone.utc) + timedelta(days=1)
            trip = Trip(
                driver_id=driver.id,
                vehicle_id=veh.id,
                from_location_id=loc1.id,
                to_location_id=loc2.id,
                departure_time=dep_dt,
                arrival_time=dep_dt + timedelta(hours=2),
                status=TripStatus.SCHEDULED,
                seats_limit_snapshot=18,
                standing_limit_snapshot=4,
                price_seated=150.0,
                price_standing=100.0,
                price_parcel=80.0,
            )
            db_session.add(trip)
            await db_session.commit()

            # 1. GET /api/trips/locations
            resp_locs = await client.get("/api/trips/locations")
            assert resp_locs.status_code == 200
            assert len(resp_locs.json()) >= 2

            # 2. GET /api/trips/search
            target_date_str = dep_dt.strftime("%Y-%m-%d")
            resp_search = await client.get(
                f"/api/trips/search?from_id={loc1.id}&to_id={loc2.id}&travel_date={target_date_str}"
            )
            assert resp_search.status_code == 200
            assert len(resp_search.json()) >= 1

            # 3. GET /api/trips/driver/{telegram_id}/manifest
            resp_manifest = await client.get(f"/api/trips/driver/{driver.telegram_id}/manifest?target_date={target_date_str}", headers=headers)
            assert resp_manifest.status_code == 200

            # Manifest for unauthenticated driver 401
            resp_man_404 = await client.get(f"/api/trips/driver/999000999/manifest?target_date={target_date_str}")
            assert resp_man_404.status_code == 401

            # 4. PATCH /api/trips/{trip_id}/status (Driver updates status)
            resp_st = await client.patch(
                f"/api/trips/{trip.id}/status?telegram_id={driver.telegram_id}",
                json={"status": "BOARDING"},
                headers=headers,
            )
            assert resp_st.status_code == 200
            assert "message" in resp_st.json()

            # Update status 404 trip
            resp_st_404 = await client.patch(
                f"/api/trips/99999/status?telegram_id={driver.telegram_id}",
                json={"status": "BOARDING"},
                headers=headers,
            )
            assert resp_st_404.status_code == 404

            # Update status unauthorized driver 401
            resp_st_403 = await client.patch(
                f"/api/trips/{trip.id}/status?telegram_id=999000999",
                json={"status": "BOARDING"}
            )
            assert resp_st_403.status_code == 401

            # 5. GET /api/trips/driver/{telegram_id}/summary
            resp_sum = await client.get(f"/api/trips/driver/{driver.telegram_id}/summary?target_date={target_date_str}", headers=headers)
            assert resp_sum.status_code == 200
            assert "total_to_hand_in" in resp_sum.json()
