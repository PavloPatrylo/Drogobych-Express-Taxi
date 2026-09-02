import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.database import async_session_maker
from app.db.models import User, Booking, UserStats
from app.services.admin_use_cases import refresh_user_stats, user_to_admin

async def main():
    async with async_session_maker() as session:
        # Get all users with stats
        stmt = select(User).options(selectinload(User.stats))
        users = (await session.execute(stmt)).scalars().all()

        print("=== USER STATS IN DB ===")
        for u in users:
            await refresh_user_stats(session, u.id)
            admin_u = user_to_admin(u)
            # Count bookings for this user
            b_stmt = select(Booking).where(Booking.passenger_id == u.id)
            bookings = (await session.execute(b_stmt)).scalars().all()
            b_statuses = [b.status.value for b in bookings]
            print(f"ID={u.id} | Name={u.full_name} | Role={u.role.value} | Bookings({len(bookings)})={b_statuses} | Trips={admin_u.total_trips} | NoShows={admin_u.total_noshows} | TrustScore={admin_u.trust_score}% | LastTrip={admin_u.last_trip_date}")

if __name__ == "__main__":
    asyncio.run(main())
