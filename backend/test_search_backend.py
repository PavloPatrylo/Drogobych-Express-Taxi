import pytest
import asyncio
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from app.db.database import async_session_maker
from app.db.models import Trip, TripStatus
from sqlalchemy import select

KYIV_TZ = ZoneInfo("Europe/Kyiv")

@pytest.mark.asyncio
async def test_search():
    """
    Короткий опис: Пошук рейсів із порівнянням часових меж (Naive vs Kyiv Timezone).
    Що перевіряє: Порівняння результатів пошуку рейсів за безчасовими межами (Naive datetime) та з урахуванням часового поясу Києва (Europe/Kyiv).
    На вхід:
        - travel_date: дата пошуку (2026-08-01).
        - from_location_id = 18, to_location_id = 19.
        - База даних з рейсами через async_session_maker.
    Очікуваний результат на виході:
        - Виведення кількості знайдених рейсів для Naive та Kyiv timezone запитів.
    """

    travel_date = date(2026, 8, 1)
    
    # 1. Naive bounds (old backend logic)
    start_naive = datetime.combine(travel_date, time.min)
    end_naive = datetime.combine(travel_date, time.max)

    # 2. Kyiv timezone-aware bounds
    start_kyiv = datetime.combine(travel_date, time.min, tzinfo=KYIV_TZ)
    end_kyiv = datetime.combine(travel_date, time.max, tzinfo=KYIV_TZ)

    async with async_session_maker() as session:
        # Query 1: Naive bounds
        stmt_naive = (
            select(Trip)
            .where(Trip.from_location_id == 18)
            .where(Trip.to_location_id == 19)
            .where(Trip.departure_time >= start_naive)
            .where(Trip.departure_time <= end_naive)
            .where(Trip.status.in_([TripStatus.SCHEDULED, TripStatus.BOARDING]))
        )
        trips_naive = (await session.execute(stmt_naive)).scalars().all()

        # Query 2: Kyiv bounds
        stmt_kyiv = (
            select(Trip)
            .where(Trip.from_location_id == 18)
            .where(Trip.to_location_id == 19)
            .where(Trip.departure_time >= start_kyiv)
            .where(Trip.departure_time <= end_kyiv)
            .where(Trip.status.in_([TripStatus.SCHEDULED, TripStatus.BOARDING]))
        )
        trips_kyiv = (await session.execute(stmt_kyiv)).scalars().all()

        print(f"--- SEARCH BACKEND TEST (Date: {travel_date}) ---")
        print(f"Old Naive Search Found: {len(trips_naive)} trips")
        print(f"Timezone-Aware Kyiv Search Found: {len(trips_kyiv)} trips")

if __name__ == "__main__":
    asyncio.run(test_search())
