"""
Integration tests for admin finance use cases (trip_finance_stats, finance_summary, close_trip).
"""
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Trip, TripStatus, Booking, BookingType, BookingSource, 
    BookingStatus, PaymentMethod, User
)
from app.services import admin_use_cases


@pytest.mark.asyncio
async def test_trip_finance_stats_use_case(db_session: AsyncSession, sample_trip: Trip, admin_user: User):
    """
    Короткий опис: Отримання фінансової статистики рейсу (trip_finance_stats).
    Що перевіряє:
        1. Підрахунок кількості сидячих пасажирів (seated).
        2. Обчислення готівкової (cash_revenue) та карткової (card_revenue) виручки.
        3. Ігнорування скасованих бронювань (CANCELLED) у фінансових показниках.
    На вхід:
        - db_session: Сесія тестової бази даних.
        - sample_trip: Тестовий рейс (Trip).
        - admin_user: Користувач-адміністратор.
        - Бронювання 1: PAID, 2 пасажири, 300.0 CASH.
        - Бронювання 2: RESERVED, 1 пасажир, 150.0 CARD.
        - Бронювання 3: CANCELLED, 1 пасажир, 150.0 CASH.
    Очікуваний результат на виході:
        - stats["seated"] == 3
        - stats["cash_revenue"] == 300.0
        - stats["card_revenue"] == 150.0
        - stats["revenue"] == 450.0
    """
    b1 = Booking(
        trip_id=sample_trip.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.WEB,
        status=BookingStatus.PAID,
        payment_method=PaymentMethod.CASH,
        passengers_count=2,
        amount_paid=300.0,
    )
    b2 = Booking(
        trip_id=sample_trip.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.WEB,
        status=BookingStatus.RESERVED,
        payment_method=PaymentMethod.CARD,
        passengers_count=1,
        amount_paid=150.0,
    )
    b3_cancelled = Booking(
        trip_id=sample_trip.id,
        created_by_id=admin_user.id,
        booking_type=BookingType.SEATED,
        source=BookingSource.WEB,
        status=BookingStatus.CANCELLED,
        payment_method=PaymentMethod.CASH,
        passengers_count=1,
        amount_paid=150.0,
    )
    db_session.add_all([b1, b2, b3_cancelled])
    await db_session.commit()

    stats = await admin_use_cases.trip_finance_stats(db_session, sample_trip.id)

    assert stats["seated"] == 3
    assert stats["cash_revenue"] == 300.0
    assert stats["card_revenue"] == 150.0
    assert stats["revenue"] == 450.0


@pytest.mark.asyncio
async def test_close_trip_use_case_success(db_session: AsyncSession, sample_trip: Trip, admin_user: User):
    """
    Короткий опис: Успішне фінансове закриття завершеного рейсу (close_trip).
    Що перевіряє:
        1. Зміну статусу рейсу на TripStatus.CLOSED.
        2. Запис зданих суми готівки (submitted_cash), картки (submitted_card) та загальної суми (submitted_amount).
        3. Збереження коментаря закриття (close_comment).
    На вхід:
        - db_session: Сесія тестової БД.
        - sample_trip: Рейс зі статусом, переведеним у COMPLETED.
        - admin_user: Адміністратор.
        - submitted_cash = 500.0, submitted_card = 300.0, comment = "Closed cleanly after evening route".
    Очікуваний результат на виході:
        - closed_trip.status == TripStatus.CLOSED
        - closed_trip.submitted_cash == 500.0
        - closed_trip.submitted_card == 300.0
        - closed_trip.submitted_amount == 800.0
        - closed_trip.close_comment == "Closed cleanly after evening route"
    """
    # First transition trip to COMPLETED
    sample_trip.status = TripStatus.COMPLETED
    await db_session.commit()

    closed_trip = await admin_use_cases.close_trip(
        db=db_session,
        trip_id=sample_trip.id,
        actor=admin_user,
        submitted_cash=500.0,
        submitted_card=300.0,
        comment="Closed cleanly after evening route",
    )

    assert closed_trip.status == TripStatus.CLOSED
    assert closed_trip.submitted_cash == 500.0
    assert closed_trip.submitted_card == 300.0
    assert closed_trip.submitted_amount == 800.0
    assert closed_trip.close_comment == "Closed cleanly after evening route"


@pytest.mark.asyncio
async def test_close_trip_fails_if_not_completed(db_session: AsyncSession, sample_trip: Trip, admin_user: User):
    """
    Короткий опис: Заборона закриття рейсу, який не є завершеним (COMPLETED).
    Що перевіряє: Чи викидається HTTPException(400), якщо спробувати закрити рейс зі статусом SCHEDULED.
    На вхід:
        - db_session: Сесія тестової БД.
        - sample_trip: Рейс зі статусом SCHEDULED.
        - admin_user: Адміністратор.
        - submitted_cash = 200.0, submitted_card = 100.0.
    Очікуваний результат на виході:
        - Викидається HTTPException із status_code == 400.
        - Деталі помилки містять фразовий фрагмент "Закрити рейс".
    """
    sample_trip.status = TripStatus.SCHEDULED
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await admin_use_cases.close_trip(
            db=db_session,
            trip_id=sample_trip.id,
            actor=admin_user,
            submitted_cash=200.0,
            submitted_card=100.0,
        )

    assert exc_info.value.status_code == 400
    assert "Закрити рейс" in exc_info.value.detail

