import asyncio
from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import User, UserRole, UserStats
from app.core.security import hash_password

async def main():
    async with async_session_maker() as session:
        phone = "+380979998877"
        stmt = select(User).where(User.phone == phone)
        user = (await session.execute(stmt)).scalar_one_or_none()

        hashed_pwd = hash_password("Driver1234")

        if user:
            user.full_name = "Іван Водійний (Тестовий)"
            user.role = UserRole.DRIVER
            user.password = hashed_pwd
            user.is_active = True
            user.is_driver_activated = False
            print(f"Updated existing user id={user.id} to Test Driver!")
        else:
            user = User(
                full_name="Іван Водійний (Тестовий)",
                phone=phone,
                role=UserRole.DRIVER,
                password=hashed_pwd,
                is_active=True,
                is_driver_activated=False
            )
            session.add(user)
            await session.flush()
            stats = UserStats(user_id=user.id)
            session.add(stats)
            print(f"Created new Test Driver user id={user.id}!")

        await session.commit()
        print("Fake driver account ready!")

if __name__ == "__main__":
    asyncio.run(main())
