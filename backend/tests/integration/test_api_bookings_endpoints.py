import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, Location, Vehicle, Trip, TripStatus, Booking, BookingType, BookingSource, BookingStatus, PaymentMethod


from app.services.auth_service import create_access_token

@pytest.mark.asyncio
async def test_create_booking_api_success_and_errors(db_session: AsyncSession, sample_trip: Trip):
    passenger = User(
        phone="+380979991122",
        full_name="Bot Passenger",
        role=UserRole.PASSENGER,
        telegram_id=777888999,
        is_active=True,
    )
    db_session.add(passenger)
    await db_session.commit()
    token = create_access_token(passenger.id, passenger.role)
    headers = {"Authorization": f"Bearer {token}"}

    def get_session_ctx():
        class SessionContext:
            async def __aenter__(self):
                return db_session
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return SessionContext()

    with patch("app.api.deps.async_session_maker", side_effect=get_session_ctx), \
         patch("app.api.bookings.async_session_maker", side_effect=get_session_ctx), \
         patch("app.api.bookings.manager.broadcast", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                # 1. Create booking success
                resp = await client.post(
                    "/api/bookings/",
                    json={
                        "telegram_id": passenger.telegram_id,
                        "trip_id": sample_trip.id,
                        "requested_seats": 2,
                    },
                    headers=headers
                )
                assert resp.status_code == 200
                assert "message" in resp.json()

                # 2. Error: Unauthenticated passenger (missing token header)
                resp_err_user = await client.post(
                    "/api/bookings/",
                    json={
                        "telegram_id": 999000111,
                        "trip_id": sample_trip.id,
                        "requested_seats": 1,
                    },
                )
                assert resp_err_user.status_code == 401

                # 3. Error: Requested seats exceed capacity
                resp_err_seats = await client.post(
                    "/api/bookings/",
                    json={
                        "telegram_id": passenger.telegram_id,
                        "trip_id": sample_trip.id,
                        "requested_seats": 100,
                    },
                    headers=headers
                )
                assert resp_err_seats.status_code == 400


@pytest.mark.asyncio
async def test_quick_sales_standing_parcel_seated_api(db_session: AsyncSession, sample_trip: Trip):
    driver = User(
        phone="+380978881122",
        full_name="Driver Quick",
        role=UserRole.DRIVER,
        telegram_id=555444333,
        is_active=True,
    )
    db_session.add(driver)
    await db_session.commit()
    token = create_access_token(driver.id, driver.role)
    headers = {"Authorization": f"Bearer {token}"}

    sample_trip.driver_id = driver.id
    sample_trip.status = TripStatus.BOARDING
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.api.deps.async_session_maker", return_value=SessionContext()), \
         patch("app.api.bookings.async_session_maker", return_value=SessionContext()), \
         patch("app.api.bookings.manager.broadcast", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                # Add seated passenger
                resp_seated = await client.post(
                    "/api/bookings/seated",
                    json={
                        "telegram_id": driver.telegram_id,
                        "trip_id": sample_trip.id,
                    },
                    headers=headers
                )
                assert resp_seated.status_code == 200

                # Add parcel
                resp_parcel = await client.post(
                    "/api/bookings/parcel",
                    json={
                        "telegram_id": driver.telegram_id,
                        "trip_id": sample_trip.id,
                        "price": 100.0,
                        "description": "Express Parcel",
                    },
                    headers=headers
                )
                assert resp_parcel.status_code == 200

                # Standing error because seated seats still available
                resp_standing_err = await client.post(
                    "/api/bookings/standing",
                    json={
                        "telegram_id": driver.telegram_id,
                        "trip_id": sample_trip.id,
                    },
                    headers=headers
                )
                assert resp_standing_err.status_code == 400


@pytest.mark.asyncio
async def test_interactive_choice_standing_and_waitlist_api(db_session: AsyncSession, sample_trip: Trip):
    passenger = User(
        phone="+380979998877",
        full_name="Interactive Pax",
        role=UserRole.PASSENGER,
        telegram_id=666555444,
        is_active=True,
    )
    db_session.add(passenger)
    await db_session.commit()
    token = create_access_token(passenger.id, passenger.role)
    headers = {"Authorization": f"Bearer {token}"}

    sample_trip.seats_limit_snapshot = 1
    sample_trip.standing_limit_snapshot = 2
    await db_session.commit()

    def get_session_ctx():
        class SessionContext:
            async def __aenter__(self):
                return db_session
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return SessionContext()

    with patch("app.api.deps.async_session_maker", side_effect=get_session_ctx), \
         patch("app.api.bookings.async_session_maker", side_effect=get_session_ctx), \
         patch("app.api.bookings.manager.broadcast", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # 1. Book the 1 seated place
            r1 = await client.post("/api/bookings/", json={"telegram_id": passenger.telegram_id, "trip_id": sample_trip.id, "requested_seats": 1}, headers=headers)
            assert r1.status_code == 200

            # 2. Try booking SEATED again -> Returns 409 Conflict with offer
            r2 = await client.post("/api/bookings/", json={"telegram_id": passenger.telegram_id, "trip_id": sample_trip.id, "requested_seats": 1, "preferred_type": "SEATED"}, headers=headers)
            assert r2.status_code == 409
            assert "STANDING" in r2.json()["detail"]

            # 3. User chooses STANDING -> Returns 200 OK with STANDING booking
            r3 = await client.post("/api/bookings/", json={"telegram_id": passenger.telegram_id, "trip_id": sample_trip.id, "requested_seats": 1, "preferred_type": "STANDING"}, headers=headers)
            assert r3.status_code == 200

            # 4. User chooses WAITLIST -> Returns 200 OK with WAITLIST status
            r4 = await client.post("/api/bookings/", json={"telegram_id": passenger.telegram_id, "trip_id": sample_trip.id, "requested_seats": 1, "preferred_type": "WAITLIST"}, headers=headers)
            assert r4.status_code == 200
            assert "Waitlist" in r4.json()["message"]
