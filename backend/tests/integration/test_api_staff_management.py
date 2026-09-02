import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.database import get_db
from app.db.models import User, UserRole
from app.services.auth_service import create_access_token


@pytest.mark.asyncio
async def test_staff_management_crud_api(db_session: AsyncSession, admin_user: User):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Create staff member (Driver)
        resp_create = await client.post(
            "/api/admin/auth/staff",
            json={
                "full_name": "New Staff Driver",
                "phone": "+380971239900",
                "role": "driver",
                "password": "Password123!",
            },
            headers=headers,
        )
        assert resp_create.status_code == 200
        staff_id = resp_create.json()["id"]

        # 2. Duplicate staff phone error -> 400
        resp_dup = await client.post(
            "/api/admin/auth/staff",
            json={
                "full_name": "Updated Driver 2",
                "phone": "+380971239900",
                "role": "driver",
                "password": "Password123!",
            },
            headers=headers,
        )
        assert resp_dup.status_code == 400

        # 2.5 Promote existing PASSENGER to DRIVER via staff creation endpoint -> 200
        p_user = User(full_name="Passenger To Driver", phone="+380971112233", role=UserRole.PASSENGER, is_active=True)
        db_session.add(p_user)
        await db_session.commit()

        resp_promote = await client.post(
            "/api/admin/auth/staff",
            json={
                "full_name": "Passenger Now Driver",
                "phone": "+380971112233",
                "role": "driver",
                "password": "NewDriverPassword123!",
            },
            headers=headers,
        )
        assert resp_promote.status_code == 200
        assert resp_promote.json()["id"] == p_user.id
        assert resp_promote.json()["role"] == "driver"

        # 2.6 Driver activation via POST /api/users/activate-driver
        driver_token = create_access_token(p_user.id, p_user.role)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}
        
        # Wrong password -> 400
        resp_act_bad = await client.post("/api/users/activate-driver", json={"password": "WrongPassword!"}, headers=driver_headers)
        assert resp_act_bad.status_code == 400

        # Correct password -> 200 OK
        resp_act_good = await client.post("/api/users/activate-driver", json={"password": "NewDriverPassword123!"}, headers=driver_headers)
        assert resp_act_good.status_code == 200
        assert resp_act_good.json()["is_driver_activated"] is True

        # 3. Update staff member
        resp_update = await client.put(
            f"/api/admin/auth/staff/{staff_id}",
            json={
                "full_name": "Updated Staff Dispatcher",
                "phone": "+380971239900",
                "role": "dispatcher",
            },
            headers=headers,
        )
        assert resp_update.status_code == 200
        assert resp_update.json()["full_name"] == "Updated Staff Dispatcher"

        # 4. Block staff member
        resp_block = await client.post(f"/api/admin/auth/staff/{staff_id}/block", headers=headers)
        assert resp_block.status_code == 200
        assert resp_block.json()["is_active"] is False

        # 5. Unblock staff member
        resp_unblock = await client.post(f"/api/admin/auth/staff/{staff_id}/unblock", headers=headers)
        assert resp_unblock.status_code == 200
        assert resp_unblock.json()["is_active"] is True

        # 5.5 Demote staff member to passenger
        resp_demote = await client.post(f"/api/admin/auth/staff/{staff_id}/demote-to-passenger", headers=headers)
        assert resp_demote.status_code == 200
        assert resp_demote.json()["role"] == "passenger"

        # 6. Delete staff member
        resp_del = await client.delete(f"/api/admin/auth/staff/{staff_id}", headers=headers)
        assert resp_del.status_code == 200

        # 7. Delete non-existent -> 404
        resp_del_404 = await client.delete(f"/api/admin/auth/staff/{staff_id}", headers=headers)
        assert resp_del_404.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_driver_with_trips_hides_trips_from_passengers(db_session: AsyncSession, admin_user: User, sample_trip):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token(admin_user.id, admin_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    # Assign sample_trip to a specific driver
    driver = User(phone="+380979990011", full_name="Driver To Delete", role=UserRole.DRIVER, is_active=True)
    db_session.add(driver)
    await db_session.commit()

    sample_trip.driver_id = driver.id
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Before deletion, passenger can find trip via search
        travel_date_str = sample_trip.departure_time.strftime("%Y-%m-%d")
        resp_before = await client.get(
            "/api/trips/search",
            params={"from_id": sample_trip.from_location_id, "to_id": sample_trip.to_location_id, "travel_date": travel_date_str}
        )
        assert resp_before.status_code == 200
        trip_ids_before = [t["id"] for t in resp_before.json()]
        assert sample_trip.id in trip_ids_before

        # 2. Delete driver who has active trips
        resp_del = await client.delete(f"/api/admin/auth/staff/{driver.id}", headers=headers)
        assert resp_del.status_code == 200
        assert resp_del.json()["is_active"] is False

        # 3. Driver account is deactivated in DB
        await db_session.refresh(driver)
        assert driver.is_active is False

        # 4. After driver deletion, trip is HIDDEN from passenger search results
        resp_after = await client.get(
            "/api/trips/search",
            params={"from_id": sample_trip.from_location_id, "to_id": sample_trip.to_location_id, "travel_date": travel_date_str}
        )
        assert resp_after.status_code == 200
        trip_ids_after = [t["id"] for t in resp_after.json()]
        assert sample_trip.id not in trip_ids_after

    app.dependency_overrides.clear()
