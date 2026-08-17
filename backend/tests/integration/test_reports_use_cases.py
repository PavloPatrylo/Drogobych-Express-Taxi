"""
Integration tests for driver and vehicle reports (driver_report_use_case, vehicle_report_use_case).
"""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Trip, TripStatus, Booking, BookingType, BookingSource, 
    BookingStatus, PaymentMethod, User, UserRole, Vehicle, Location
)
from app.services import admin_use_cases


@pytest.mark.asyncio
async def test_driver_report_use_case(db_session: AsyncSession, admin_user: User):
    """
    Тест звіту по водіях (driver_report_use_case).
    Перевіряє:
        1. Підрахунок кількості рейсів та завершених рейсів водія.
        2. Розподіл виручки за готівку та карткою.
        3. Обчислення середньої каси на рейс (avg_revenue_per_trip).
    """
    # Створюємо водія з унікальним телефоном
    driver = User(
        phone="+380971110001",
        full_name="Іван Водій",
        role=UserRole.DRIVER,
        is_active=True,
    )
    from_loc = Location(name="Drohobych_R1")
    to_loc = Location(name="Lviv_R1")
    vehicle = Vehicle(model="Sprinter 1", plate_number="BC1111AA", total_seats=18, total_standing=5)

    db_session.add_all([driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    # Створюємо 2 рейси для водія
    trip1 = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=datetime(2026, 8, 15, 8, 0, tzinfo=timezone.utc),
        status=TripStatus.COMPLETED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    trip2 = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=18,
        standing_limit_snapshot=5,
        price_seated=150.0,
        price_standing=100.0,
    )
    db_session.add_all([trip1, trip2])
    await db_session.commit()

    # Бронювання 1: 2 місця, Готівка 300 грн на trip1
    b1 = Booking(
        trip_id=trip1.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.WEB,
        status=BookingStatus.PAID,
        payment_method=PaymentMethod.CASH,
        passengers_count=2,
        amount_paid=300.0,
    )
    # Бронювання 2: 1 місце, Картка 150 грн на trip2
    b2 = Booking(
        trip_id=trip2.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.WEB,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CARD,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add_all([b1, b2])
    await db_session.commit()

    # Викликаємо звіт по даному водію
    reports = await admin_use_cases.driver_report_use_case(db_session, driver_id=driver.id)

    assert len(reports) == 1
    rep = reports[0]
    assert rep.driver_id == driver.id
    assert rep.driver_name == "Іван Водій"
    assert rep.trips_count == 2
    assert rep.completed_trips_count == 1
    assert rep.total_passengers == 3
    assert rep.cash_revenue == 300.0
    assert rep.card_revenue == 150.0
    assert rep.total_revenue == 450.0
    assert rep.avg_revenue_per_trip == 225.0


@pytest.mark.asyncio
async def test_vehicle_report_use_case(db_session: AsyncSession, admin_user: User):
    """
    Тест звіту по авто (vehicle_report_use_case).
    Перевіряє:
        1. Підрахунок місткості та заповнюваності (occupancy_rate).
        2. Розрахунок середнього чека авто на рейс.
    """
    driver = User(
        phone="+380971110002",
        full_name="Петро Водій",
        role=UserRole.DRIVER,
        is_active=True,
    )
    from_loc = Location(name="Drohobych_V1")
    to_loc = Location(name="Lviv_V1")
    vehicle = Vehicle(model="Mercedes Crafter", plate_number="BC2222BB", total_seats=20, total_standing=10)

    db_session.add_all([driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    # Рейс 1 для авто
    trip = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=datetime(2026, 8, 16, 9, 0, tzinfo=timezone.utc),
        status=TripStatus.SCHEDULED,
        seats_limit_snapshot=20,
        standing_limit_snapshot=10,
        price_seated=200.0,
        price_standing=100.0,
    )
    db_session.add(trip)
    await db_session.commit()

    # Заброньовано 10 сидячих місць з 20 (заповнюваність має бути 50%)
    booking = Booking(
        trip_id=trip.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CASH,
        passengers_count=10,
        amount_paid=2000.0,
    )
    db_session.add(booking)
    await db_session.commit()

    # Отримуємо звіт по авто
    reports = await admin_use_cases.vehicle_report_use_case(db_session, vehicle_id=vehicle.id)

    assert len(reports) == 1
    rep = reports[0]
    assert rep.vehicle_id == vehicle.id
    assert rep.plate_number == "BC2222BB"
    assert rep.model == "Mercedes Crafter"
    assert rep.trips_count == 1
    assert rep.total_passengers == 10
    assert rep.total_seats_capacity == 20
    assert rep.occupancy_rate == 50.0
    assert rep.cash_revenue == 2000.0
    assert rep.card_revenue == 0.0
    assert rep.total_revenue == 2000.0
    assert rep.avg_revenue_per_trip == 2000.0


@pytest.mark.asyncio
async def test_reports_date_filtering(db_session: AsyncSession, admin_user: User):
    """
    Перевірка фільтрації звітів водіїв та авто за датами (date_from, date_to).
    """
    driver = User(
        phone="+380971110003",
        full_name="Степан Водій",
        role=UserRole.DRIVER,
        is_active=True,
    )
    from_loc = Location(name="Drohobych_F1")
    to_loc = Location(name="Lviv_F1")
    vehicle = Vehicle(model="Transit", plate_number="BC3333CC", total_seats=15, total_standing=0)

    db_session.add_all([driver, from_loc, to_loc, vehicle])
    await db_session.commit()

    # Рейс 1: 10 серпня
    now_utc = datetime.now(timezone.utc)
    t1_dt = now_utc - timedelta(days=7)
    t2_dt = now_utc + timedelta(days=3)

    t1 = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=t1_dt,
        status=TripStatus.COMPLETED,
        seats_limit_snapshot=15,
        standing_limit_snapshot=0,
        price_seated=100.0,
        price_standing=0.0,
    )
    t2 = Trip(
        driver_id=driver.id,
        vehicle_id=vehicle.id,
        from_location_id=from_loc.id,
        to_location_id=to_loc.id,
        departure_time=t2_dt,
        status=TripStatus.COMPLETED,
        seats_limit_snapshot=15,
        standing_limit_snapshot=0,
        price_seated=100.0,
        price_standing=0.0,
    )
    db_session.add_all([t1, t2])
    await db_session.commit()

    b1 = Booking(
        trip_id=t1.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.PAID,
        payment_method=PaymentMethod.CASH,
        passengers_count=5,
        amount_paid=500.0,
    )
    b2 = Booking(
        trip_id=t2.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.PAID,
        payment_method=PaymentMethod.CARD,
        passengers_count=8,
        amount_paid=800.0,
    )
    db_session.add_all([b1, b2])
    await db_session.commit()

    # Фільтруємо лише по датах рейсу 2
    t2_date_from = (t2_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    t2_date_to = (t2_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    driver_reports = await admin_use_cases.driver_report_use_case(
        db_session, date_from=t2_date_from, date_to=t2_date_to, driver_id=driver.id
    )
    assert len(driver_reports) == 1
    d_rep = driver_reports[0]
    assert d_rep.trips_count == 1
    assert d_rep.total_revenue == 800.0
    assert d_rep.card_revenue == 800.0
    assert d_rep.cash_revenue == 0.0

    t1_date_from = (t1_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    t1_date_to = (t1_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    vehicle_reports = await admin_use_cases.vehicle_report_use_case(
        db_session, date_from=t1_date_from, date_to=t1_date_to, vehicle_id=vehicle.id
    )
    assert len(vehicle_reports) == 1
    v_rep = vehicle_reports[0]
    assert v_rep.trips_count == 1
    assert v_rep.total_revenue == 500.0
    assert v_rep.cash_revenue == 500.0
