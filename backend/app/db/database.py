from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Створюємо асинхронний двигун (echo=True виводить SQL-запити в консоль)
engine = create_async_engine(settings.database_url, echo=True)

# Фабрика сесій
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Залежність для FastAPI, щоб брати сесію в роутерах
async def get_db():
    async with async_session_maker() as session:
        yield session