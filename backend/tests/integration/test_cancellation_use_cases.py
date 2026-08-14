"""
Integration tests for booking cancellation use cases (cancel_booking, permission checks, closed trip protections).
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Trip, TripStatus, Booking, BookingType, BookingSource, 
    BookingStatus, PaymentMethod, User, AuditLog
)
from app.services import admin_use_cases


@pytest.mark.asyncio
async def test_cancel_booking_use_case_success(
    db_session: AsyncSession, sample_trip: Trip, admin_user: User, passenger_user: User
):
    """
    Короткий опис: Успішне скасування бронювання адміністратором через use case.
    Що перевіряє:
        1. Зміну статусу бронювання на BookingStatus.CANCELLED.
        2. Оновлення запису в БД.
        3. Створення відповідного запису в лозі аудиту (AuditLog) із дією BOOKING_CANCELLED.
    На вхід:
        - db_session: Сесія тестової бази даних.
        - sample_trip: Тестовий рейс (Trip).
        - admin_user: Користувач-адміністратор (UserRole.ADMIN).
        - passenger_user: Пасажир (UserRole.PASSENGER).
        - booking: Зареєстроване бронювання зі статусом RESERVED.
    Очікуваний результат на виході:
        - res.status == BookingStatus.CANCELLED
        - У БД booking.status змінюється на CANCELLED.
        - У таблиці AuditLog зберігається запис про дію BOOKING_CANCELLED.
    """
    booking = Booking(
        trip_id=sample_trip.id,
        passenger_id=passenger_user.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add(booking)
    await db_session.commit()
    await db_session.refresh(booking)

    res = await admin_use_cases.cancel_booking(
        db=db_session,
        booking_id=booking.id,
        actor=admin_user,
    )

    assert res.status == BookingStatus.CANCELLED

    # Verify database state
    db_booking = await db_session.get(Booking, booking.id)
    assert db_booking.status == BookingStatus.CANCELLED

    # Verify AuditLog entry
    audit_res = await db_session.execute(
        select(AuditLog).where(
            AuditLog.entity_type == "booking",
            AuditLog.entity_id == booking.id,
            AuditLog.action == "BOOKING_CANCELLED",
        )
    )
    audit_log = audit_res.scalars().first()
    assert audit_log is not None


@pytest.mark.asyncio
async def test_cancel_booking_fails_on_closed_trip(
    db_session: AsyncSession, sample_trip: Trip, admin_user: User
):
    """
    Короткий опис: Заборонити скасування бронювання у закритому рейсі.
    Що перевіряє: Чи викидає сервіс HTTPException(400) при спробі скасувати квиток на рейс із статусом CLOSED.
    На вхід:
        - db_session: Сесія тестової бази даних.
        - sample_trip: Рейс зі статусом, зміненим на TripStatus.CLOSED.
        - admin_user: Адміністратор, що виконує дію.
        - booking: Бронювання у цьому закритому рейсі.
    Очікуваний результат на виході:
        - Викидається HTTPException із status_code == 400.
        - Деталі помилки містять текст "фінансово закритому".
    """
    booking = Booking(
        trip_id=sample_trip.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add(booking)
    sample_trip.status = TripStatus.CLOSED
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await admin_use_cases.cancel_booking(
            db=db_session,
            booking_id=booking.id,
            actor=admin_user,
        )

    assert exc_info.value.status_code == 400
    assert "фінансово закритому" in exc_info.value.detail


@pytest.mark.asyncio
async def test_cancel_booking_permission_denied_for_passenger(
    db_session: AsyncSession, sample_trip: Trip, admin_user: User, passenger_user: User
):
    """
    Короткий опис: Перевірка прав доступу при скасуванні бронювання через admin use case.
    Що перевіряє: Чи викликає спроба пасажира (не адміна і не диспетчера) скасувати бронювання через admin_use_cases помилку 403 Forbidden.
    На вхід:
        - db_session: Сесія тестової БД.
        - sample_trip: Тестовий рейс.
        - admin_user: Адмін, що створив бронювання.
        - passenger_user: Звичайний пасажир, який виступає як actor.
        - booking: Зареєстроване бронювання.
    Очікуваний результат на виході:
        - Викидається HTTPException із status_code == 403.
    """
    booking = Booking(
        trip_id=sample_trip.id,
        passenger_id=passenger_user.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.PHONE,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add(booking)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await admin_use_cases.cancel_booking(
            db=db_session,
            booking_id=booking.id,
            actor=passenger_user,
        )

    assert exc_info.value.status_code == 403

