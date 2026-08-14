import asyncio
from app.db.database import async_session_maker
from sqlalchemy import text

async def clear_user_3():
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM audit_logs WHERE actor_id=3 OR passenger_id=3"))
        await session.execute(text("DELETE FROM bookings WHERE passenger_id=3 OR created_by_id=3 OR validated_by_id=3"))
        await session.execute(text("DELETE FROM user_stats WHERE user_id=3"))
        await session.execute(text("DELETE FROM users WHERE id=3 OR telegram_id=1254047332"))
        await session.commit()
        print("✅ User ID 3 (telegram_id 1254047332) completely deleted from DB!")

if __name__ == "__main__":
    asyncio.run(clear_user_3())
