import asyncio
from app.db.database import async_session_maker
from app.db.models import Trip
from sqlalchemy import select

async def check_trip():
    async with async_session_maker() as session:
        trip = (await session.execute(select(Trip).where(Trip.id == 177))).scalar_one_or_none()
        if trip:
            print(f"Trip 177: departure_time={trip.departure_time}, status={trip.status}, driver_id={trip.driver_id}")
        else:
            print("Trip 177 not found")

if __name__ == "__main__":
    asyncio.run(check_trip())
