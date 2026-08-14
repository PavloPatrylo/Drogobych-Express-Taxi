
import asyncio
from app.db.database import async_session_maker
from app.db.models import Trip, Location
from sqlalchemy import select

async def check():
    async with async_session_maker() as s:
        locs = (await s.execute(select(Location))).scalars().all()
        print("Locations:")
        for l in locs:
            print(f"ID={l.id}: {l.name}")

        trips = (await s.execute(select(Trip))).scalars().all()
        print(f"\nTotal trips in DB: {len(trips)}")
        for t in trips:
            print(f"Trip #{t.id}: from_id={t.from_location_id} to_id={t.to_location_id} time={t.departure_time} status={t.status}")

if __name__ == "__main__":
    asyncio.run(check())
