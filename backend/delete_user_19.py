import asyncio
from app.db.database import async_session_maker
from sqlalchemy import text, select
from app.db.models import User

async def delete_user_19():
    async with async_session_maker() as session:
        # Перевіряємо наявність
        user = (await session.execute(select(User).where(User.id == 19))).scalar_one_or_none()
        if not user:
            # Шукаємо останнього створеного пасажира
            users = (await session.execute(select(User).order_by(User.id.desc()))).scalars().all()
            print("Current users in DB:")
            for u in users:
                print(f"ID={u.id}, telegram_id={u.telegram_id}, phone={u.phone}, name={u.full_name}")
            return

        u_id = user.id
        tg_id = user.telegram_id
        print(f"Deleting User ID={u_id}, telegram_id={tg_id}, name={user.full_name}...")

        await session.execute(text("DELETE FROM audit_logs WHERE actor_id=:id OR passenger_id=:id"), {"id": u_id})
        await session.execute(text("DELETE FROM bookings WHERE passenger_id=:id OR created_by_id=:id OR validated_by_id=:id"), {"id": u_id})
        await session.execute(text("DELETE FROM user_stats WHERE user_id=:id"), {"id": u_id})
        await session.execute(text("DELETE FROM users WHERE id=:id"), {"id": u_id})
        await session.commit()
        print(f"Successfully deleted user ID={u_id} from database!")

if __name__ == "__main__":
    asyncio.run(delete_user_19())
