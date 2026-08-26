from pydantic import BaseModel, Field
from typing import Optional
from app.db.models import UserRole

# --- Схеми для Статистики ---
class UserStatsBase(BaseModel):
    total_trips: int = 0
    total_noshows: int = 0
    trust_score_cached: int = 100

class UserStatsRead(UserStatsBase):
    id: int

    class Config:
        from_attributes = True

# --- Базові поля користувача (спільні для всіх) ---
class UserBase(BaseModel):
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: UserRole = UserRole.PASSENGER
    avatar_url: Optional[str] = None

# --- 1. Схема для СТВОРЕННЯ (Create) ---
# Використовується, коли диспетчер додає водія через адмінку
class UserCreate(UserBase):
    telegram_id: Optional[int] = None
    password: Optional[str] = None  # Водію пароль потрібен, пасажиру - ні

# --- 2. Схема для ОНОВЛЕННЯ (Update) ---
# Всі поля Optional, бо ми можемо оновити тільки щось одне (наприклад, тільки аватарку)
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    password: Optional[str] = None

# --- 3. Схема для ВІДДАЧІ НА ФРОНТЕНД (Read) ---
# Зверни увагу: тут НЕМАЄ поля password! Це для безпеки.
class UserRead(UserBase):
    id: int
    telegram_id: Optional[int]
    stats: Optional[UserStatsRead] = None

    class Config:
        from_attributes = True

class TelegramWebAppAuth(BaseModel):
    init_data: str

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead