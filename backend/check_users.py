import asyncio
from app.db.database import async_session_maker
from app.db.models import User
from sqlalchemy import select

async def check_users():
    async with async_session_maker() as session:
        users = (await session.execute(select(User))).scalars().all()
        print(f"Total Users in DB: {len(users)}")
        for u in users:
            print(f"User ID={u.id}, telegram_id={u.telegram_id}, phone={u.phone}, full_name='{u.full_name}', role={u.role}")

if __name__ == "__main__":
    asyncio.run(check_users())
