import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole, Location, Vehicle, Trip, TripStatus, BookingSource, PaymentMethod, DayType
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_admin_schedule_all_routes_api(
    db_session: AsyncSession, admin_user: User, sample_trip: Trip
):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Locations
        resp_locs = await client.get("/api/admin/locations", headers=headers)
        assert resp_locs.status_code == 200

        # 2. Dashboard
        resp_dash = await client.get("/api/admin/dashboard", headers=headers)
        assert resp_dash.status_code == 200

        # 3. System Config GET & PUT
        resp_sys_get = await client.get("/api/admin/system-config", headers=headers)
        assert resp_sys_get.status_code == 200

        resp_sys_put = await client.put(
            "/api/admin/system-config",
            json={
                "price_seated": 150.0,
                "price_standing": 100.0,
                "price_parcel": 80.0,
            },
            headers=headers,
        )
        assert resp_sys_put.status_code == 200

        # 4. Schedule Templates
        resp_tmpl_post = await client.post(
            "/api/admin/templates",
            json={
                "day_type": "weekday",
                "from_location_id": sample_trip.from_location_id,
                "to_location_id": sample_trip.to_location_id,
                "departure_time": "08:30",
                "seats_limit": 15,
                "standing_limit": 4,
                "price_seated": 120.0,
                "price_standing": 90.0,
                "price_parcel": 80.0,
            },
            headers=headers,
        )
        assert resp_tmpl_post.status_code == 200
        tmpl_id = resp_tmpl_post.json()["id"]

        resp_tmpl_del = await client.delete(f"/api/admin/templates/{tmpl_id}", headers=headers)
        assert resp_tmpl_del.status_code == 200

        # 5. List Trips
        resp_trips = await client.get("/api/admin/trips", headers=headers)
        assert resp_trips.status_code == 200

        # 6. Create Driver & Vehicle for Trip
        driver = User(phone="+380979998811", full_name="Assign Driver", role=UserRole.DRIVER, is_active=True)
        vehicle = Vehicle(model="Man Bus", plate_number="BC9999ZZ", total_seats=20, total_standing=5, is_active=True)
        db_session.add_all([driver, vehicle])
        await db_session.commit()

        resp_trip_create = await client.post(
            "/api/admin/trips",
            json={
                "driver_id": driver.id,
                "vehicle_id": vehicle.id,
                "route": "drohobych-lviv",
                "date": "2027-01-01",
                "departure_time": "10:00",
                "price_seated": 150.0,
                "price_standing": 100.0,
                "price_parcel": 100.0,
            },
            headers=headers,
        )
        assert resp_trip_create.status_code == 200, resp_trip_create.text
        new_trip_id = resp_trip_create.json()["id"]

        # 7. Batch Trip Create
        resp_batch = await client.post(
            "/api/admin/trips/batch",
            json={
                "trips": [
                    {
                        "driver_id": driver.id,
                        "vehicle_id": vehicle.id,
                        "route": "drohobych-lviv",
                        "date": "2027-01-02",
                        "departure_time": "09:00",
                    },
                    {
                        "driver_id": driver.id,
                        "vehicle_id": vehicle.id,
                        "route": "drohobych-lviv",
                        "date": "2027-01-03",
                        "departure_time": "09:00",
                    },
                ]
            },
            headers=headers,
        )
        assert resp_batch.status_code == 200, resp_batch.text
        assert len(resp_batch.json()) == 2

        # 8. Update Trip
        resp_trip_upd = await client.put(
            f"/api/admin/trips/{new_trip_id}",
            json={
                "driver_id": driver.id,
                "vehicle_id": vehicle.id,
                "route": "drohobych-lviv",
                "date": "2027-01-01",
                "departure_time": "10:30",
                "price_seated": 160.0,
                "price_standing": 110.0,
                "price_parcel": 100.0,
            },
            headers=headers,
        )
        assert resp_trip_upd.status_code == 200, resp_trip_upd.text

        # 9. Change Status
        resp_status = await client.patch(
            f"/api/admin/trips/{new_trip_id}/status",
            json={"status": "BOARDING"},
            headers=headers,
        )
        assert resp_status.status_code == 200

        # 10. Assign Driver & Vehicle
        driver_assign = User(phone="+380971112233", full_name="Assignee Driver", role=UserRole.DRIVER, is_active=True)
        vehicle_assign = Vehicle(model="Sprinter Bus", plate_number="BC1122YY", total_seats=20, total_standing=5, is_active=True)
        db_session.add_all([driver_assign, vehicle_assign])
        await db_session.commit()

        resp_assign = await client.patch(
            f"/api/admin/trips/{new_trip_id}/assign",
            json={"driver_id": driver_assign.id, "vehicle_id": vehicle_assign.id},
            headers=headers,
        )
        assert resp_assign.status_code == 200

        # 11. Manifest & Manifest Booking
        resp_manifest = await client.get(f"/api/admin/trips/{new_trip_id}/manifest", headers=headers)
        assert resp_manifest.status_code == 200

        resp_m_booking = await client.post(
            f"/api/admin/trips/{new_trip_id}/manifest/booking",
            json={
                "phone": "+380975554433",
                "full_name": "Manifest Pax",
                "seats": 1,
                "booking_type": "SEATED",
                "payment_method": "CASH",
            },
            headers=headers,
        )
        assert resp_m_booking.status_code == 200
        booking_id = resp_m_booking.json()["id"]

        # 12. Booking status update & cancel
        resp_b_status = await client.patch(
            f"/api/admin/bookings/{booking_id}/status",
            json={"status": "BOARDED"},
            headers=headers,
        )
        assert resp_b_status.status_code == 200

        # 13. Offline Booking
        resp_offline = await client.post(
            "/api/admin/bookings/offline",
            json={
                "trip_id": new_trip_id,
                "phone": "+380976665544",
                "full_name": "Offline Pax",
                "source": "PHONE",
                "seats": 1,
                "payment_method": "CASH",
            },
            headers=headers,
        )
        assert resp_offline.status_code == 200
        off_booking_id = resp_offline.json()["id"]

        # Cancel booking
        resp_b_cancel = await client.patch(f"/api/admin/bookings/{off_booking_id}/cancel", headers=headers)
        assert resp_b_cancel.status_code == 200

        # Set status to COMPLETED first before closing
        resp_status_comp = await client.patch(
            f"/api/admin/trips/{new_trip_id}/status",
            json={"status": "COMPLETED"},
            headers=headers,
        )
        assert resp_status_comp.status_code == 200

        # 14. Close Trip
        resp_close = await client.post(
            f"/api/admin/trips/{new_trip_id}/close",
            json={
                "submitted_cash": 160.0,
                "submitted_card": 0.0,
                "comment": "Closed via API test",
            },
            headers=headers,
        )
        assert resp_close.status_code == 200, resp_close.text
        assert resp_close.json()["status"] == "CLOSED"

        # 15. Staff users list
        resp_users = await client.get("/api/admin/users", headers=headers)
        assert resp_users.status_code == 200

    app.dependency_overrides.clear()
