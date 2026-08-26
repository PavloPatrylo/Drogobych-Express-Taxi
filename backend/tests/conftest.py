import asyncio
from datetime import datetime, timezone
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.db.models import (
    Base, User, UserRole, Location, Vehicle, Trip, TripStatus,
    Booking, BookingType, BookingSource, BookingStatus, PaymentMethod
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class SingleSessionContextManager:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine, monkeypatch):
    async_session_factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session_factory() as session:
        cm = SingleSessionContextManager(session)
        session_factory_wrapper = lambda: cm
        monkeypatch.setattr("app.db.database.async_session_maker", session_factory_wrapper)
        monkeypatch.setattr("app.api.deps.async_session_maker", session_factory_wrapper)
        monkeypatch.setattr("app.api.bookings.async_session_maker", session_factory_wrapper)
        monkeypatch.setattr("app.api.trips.async_session_maker", session_factory_wrapper)
        monkeypatch.setattr("app.services.reminders.async_session_maker", session_factory_wrapper)
        from unittest.mock import AsyncMock
        monkeypatch.setattr("app.services.reminders.start_reminder_scheduler", AsyncMock())
        monkeypatch.setattr("bot.main_bot.dp.start_polling", AsyncMock())
        async def override_get_db():
            yield session

        from app.main import app
        from app.db.database import get_db
        app.dependency_overrides[get_db] = override_get_db

        yield session

        app.dependency_overrides.clear()


# Helper Model Factories
@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    admin = User(
        phone="+380970000001",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def dispatcher_user(db_session: AsyncSession):
    dispatcher = User(
        phone="+380970000002",
        full_name="Dispatcher User",
        role=UserRole.DISPATCHER,
        is_active=True
    )
    db_session.add(dispatcher)
    await db_session.commit()
    await db_session.refresh(dispatcher)
    return dispatcher


@pytest_asyncio.fixture
async def passenger_user(db_session: AsyncSession):
    passenger = User(
        phone="+380970000003",
        full_name="Passenger Test",
        role=UserRole.PASSENGER,
        is_active=True
    )
    db_session.add(passenger)
    await db_session.commit()
    await db_session.refresh(passenger)
    return passenger


@pytest_asyncio.fixture
async def driver_user(db_session: AsyncSession):
    driver = User(
        phone="+380970000004",
        full_name="Driver Test",
        telegram_id=999888777,
        role=UserRole.DRIVER,
        is_active=True
    )
    db_session.add(driver)
    await db_session.commit()
    await db_session.refresh(driver)
    return driver


@pytest_asyncio.fixture
async def locations(db_session: AsyncSession):
    from_loc = Location(name="Drohobych")
    to_loc = Location(name="Lviv")
    db_session.add_all([from_loc, to_loc])
    await db_session.commit()
    await db_session.refresh(from_loc)
    await db_session.refresh(to_loc)
    return from_loc, to_loc


@pytest_asyncio.fixture
async def vehicle(db_session: AsyncSession):
    veh = Vehicle(model="Sprinter 316", plate_number="BC9999EX", total_seats=18, total_standing=5, is_active=True)
    db_session.add(veh)
    await db_session.commit()
    await db_session.refresh(veh)
    return veh


@pytest_asyncio.fixture
async def sample_trip(db_session: AsyncSession, admin_user: User):
    from_loc = Location(name="Drogobych")
    to_loc = Location(name="Lviv")
    vehicle = Vehicle(model="Sprinter", plate_number="BC1234AB", total_seats=18, total_standing=5)
    
    db_session.add_all([from_loc, to_loc, vehicle])
    await db_session.commit()
    
    from datetime import timedelta
    now_utc = datetime.now(timezone.utc)
    departure_dt = now_utc + timedelta(days=1)
    arrival_dt = departure_dt + timedelta(hours=1, minutes=30)
    
    trip = Trip(
        departure_time=departure_dt,
        arrival_time=arrival_dt,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        vehicle_id=vehicle.id,
        driver_id=admin_user.id,
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
        price_parcel=80.0,
    )
    db_session.add(trip)
    await db_session.commit()
    await db_session.refresh(trip)
    return trip
