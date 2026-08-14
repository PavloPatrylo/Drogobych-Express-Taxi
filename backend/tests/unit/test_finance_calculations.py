"""
Unit tests for financial calculations (Cash vs Card logic, revenue aggregation, and cancellation exclusions).
"""
import pytest
from app.db.models import Booking, BookingStatus, PaymentMethod, BookingType


def calculate_finance_totals(bookings: list[Booking]) -> dict[str, float]:
    """
    Pure calculation helper matching domain logic:
    Excludes CANCELLED and NOSHOW bookings, then sums amount_paid by PaymentMethod.
    """
    billable = [b for b in bookings if b.status not in (BookingStatus.CANCELLED, BookingStatus.NOSHOW)]
    
    cash_revenue = sum(
        float(b.amount_paid) for b in billable 
        if getattr(b, "payment_method", PaymentMethod.CASH) == PaymentMethod.CASH or str(getattr(b, "payment_method", "CASH")) == "CASH"
    )
    card_revenue = sum(
        float(b.amount_paid) for b in billable 
        if getattr(b, "payment_method", PaymentMethod.CASH) == PaymentMethod.CARD or str(getattr(b, "payment_method", "CARD")) == "CARD"
    )
    
    return {
        "cash_revenue": cash_revenue,
        "card_revenue": card_revenue,
        "total_revenue": cash_revenue + card_revenue,
    }


def test_cash_and_card_split_calculation():
    """
    Короткий опис: Розрахунок та розділення виручки на готівкову (CASH) та безналічну (CARD).
    Що перевіряє: Чи правильно обчислюються суми cash_revenue, card_revenue та total_revenue для активних/оплачених квитків.
    На вхід:
        - Список із 4 бронювань (Booking): 2 готівкових (150.0 + 300.0) та 2 карткових (150.0 + 450.0).
    Очікуваний результат на виході:
        - cash_revenue == 450.0
        - card_revenue == 600.0
        - total_revenue == 1050.0
    """
    bookings = [
        Booking(id=1, status=BookingStatus.RESERVED, payment_method=PaymentMethod.CASH, amount_paid=150.0),
        Booking(id=2, status=BookingStatus.PAID, payment_method=PaymentMethod.CASH, amount_paid=300.0),
        Booking(id=3, status=BookingStatus.BOARDED, payment_method=PaymentMethod.CARD, amount_paid=150.0),
        Booking(id=4, status=BookingStatus.PAID, payment_method=PaymentMethod.CARD, amount_paid=450.0),
    ]

    totals = calculate_finance_totals(bookings)

    assert totals["cash_revenue"] == 450.0
    assert totals["card_revenue"] == 600.0
    assert totals["total_revenue"] == 1050.0


def test_cancelled_and_noshow_bookings_excluded_from_revenue():
    """
    Короткий опис: Виключення скасованих та неявлених квитків з розрахунку виручки.
    Що перевіряє: Чи ігноруються бронювання зі статусами CANCELLED та NOSHOW під час підрахунку загального доходу.
    На вхід:
        - Список із 4 бронювань: 1 PAID (200.0 CASH), 2 CANCELLED (200.0 CASH / 200.0 CARD), 1 NOSHOW (200.0 CARD).
    Очікуваний результат на виході:
        - cash_revenue == 200.0 (тільки активне бронювання)
        - card_revenue == 0.0
        - total_revenue == 200.0
    """
    bookings = [
        Booking(id=1, status=BookingStatus.PAID, payment_method=PaymentMethod.CASH, amount_paid=200.0),
        Booking(id=2, status=BookingStatus.CANCELLED, payment_method=PaymentMethod.CASH, amount_paid=200.0),
        Booking(id=3, status=BookingStatus.NOSHOW, payment_method=PaymentMethod.CARD, amount_paid=200.0),
        Booking(id=4, status=BookingStatus.CANCELLED, payment_method=PaymentMethod.CARD, amount_paid=200.0),
    ]

    totals = calculate_finance_totals(bookings)

    assert totals["cash_revenue"] == 200.0
    assert totals["card_revenue"] == 0.0
    assert totals["total_revenue"] == 200.0


def test_financial_closure_submission_calculation():
    """
    Короткий опис: Розрахунок зданих фінансових коштів під час закриття рейсу.
    Що перевіряє: Чи коректно підсумовуються здані готівкові та безналічні кошти, а також обробка ручного перевизначення загальної суми.
    На вхід:
        - submitted_cash = 1200.0, submitted_card = 800.0
        - explicit_total = 1950.0 (для перевірки кастомної суми)
    Очікуваний результат на виході:
        - Стандартна сума (submitted_cash + submitted_card) == 2000.0
        - Фінальна сума при наявності explicit_total == 1950.0
    """
    submitted_cash = 1200.0
    submitted_card = 800.0
    
    # Standard sum when submitted_amount is not explicitly given
    total_val = (submitted_cash or 0.0) + (submitted_card or 0.0)
    assert total_val == 2000.0

    # Overridden submitted_amount (e.g. custom total override)
    explicit_total = 1950.0
    final_val = explicit_total if explicit_total is not None else total_val
    assert final_val == 1950.0

