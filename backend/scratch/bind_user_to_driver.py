import asyncio
from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import User, UserRole
from app.core.security import hash_password

async def main():
    async with async_session_maker() as session:
        # Find user 33 with real telegram_id 1685900931
        stmt = select(User).where(User.telegram_id == 1685900931)
        user = (await session.execute(stmt)).scalar_one_or_none()

        if user:
            user.role = UserRole.DRIVER
            user.password = hash_password("Driver1234")
            user.is_active = True
            user.is_driver_activated = False  # <--- Очікує введення пароля в Mini App!
            await session.commit()
            print(f"✅ User id={user.id} (telegram_id={user.telegram_id}, phone={user.phone}) updated to DRIVER! Pending activation with password 'Driver1234'.")
        else:
            print("❌ User 1685900931 not found")

if __name__ == "__main__":
    asyncio.run(main())
