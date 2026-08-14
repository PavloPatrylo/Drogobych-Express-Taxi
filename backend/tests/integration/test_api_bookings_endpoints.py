import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, Location, Vehicle, Trip, TripStatus, Booking, BookingType, BookingSource, BookingStatus, PaymentMethod


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

    def get_session_ctx():
        class SessionContext:
            async def __aenter__(self):
                return db_session
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass
        return SessionContext()

    with patch("app.api.bookings.async_session_maker", side_effect=get_session_ctx):
        with patch("app.api.bookings.manager.broadcast", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                # 1. Create booking success
                resp = await client.post(
                    "/api/bookings/",
                    json={
                        "telegram_id": passenger.telegram_id,
                        "trip_id": sample_trip.id,
                        "requested_seats": 2,
                    },
                )
                assert resp.status_code == 200
                assert "message" in resp.json()

                # 2. Error: Passenger not registered in bot (telegram_id missing in DB)
                resp_err_user = await client.post(
                    "/api/bookings/",
                    json={
                        "telegram_id": 999000111,
                        "trip_id": sample_trip.id,
                        "requested_seats": 1,
                    },
                )
                assert resp_err_user.status_code == 400

                # 3. Error: Requested seats exceed capacity
                resp_err_seats = await client.post(
                    "/api/bookings/",
                    json={
                        "telegram_id": passenger.telegram_id,
                        "trip_id": sample_trip.id,
                        "requested_seats": 100,
                    },
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

    sample_trip.driver_id = driver.id
    sample_trip.status = TripStatus.BOARDING
    await db_session.commit()

    class SessionContext:
        async def __aenter__(self):
            return db_session
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("app.api.bookings.async_session_maker", return_value=SessionContext()):
        with patch("app.api.bookings.manager.broadcast", new_callable=AsyncMock):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                # Add seated passenger
                resp_seated = await client.post(
                    "/api/bookings/seated",
                    json={
                        "telegram_id": driver.telegram_id,
                        "trip_id": sample_trip.id,
                    },
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
                )
                assert resp_parcel.status_code == 200

                # Standing error because seated seats still available
                resp_standing_err = await client.post(
                    "/api/bookings/standing",
                    json={
                        "telegram_id": driver.telegram_id,
                        "trip_id": sample_trip.id,
                    },
                )
                assert resp_standing_err.status_code == 400
