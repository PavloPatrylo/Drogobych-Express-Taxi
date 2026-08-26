import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    ReplyKeyboardRemove, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    WebAppInfo
)
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

# Імпортуємо налаштування та моделі
from app.core.config import settings
from app.db.database import async_session_maker
from app.db.models import User, UserStats, UserRole, Booking, AuditLog

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

# Посилання на Telegram MiniApp у Ngrok
WEB_APP_URL = "https://fletcher-inordinate-leontine.ngrok-free.dev"

# --- 1. Визначаємо стани (FSM) ---
class AuthStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_password = State()

# --- Клавіатури ---
def get_registration_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поділитися номером", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_main_menu_kb(telegram_id: int = None):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚕 Запустити Express Taxi", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])

# --- 2. Обробка команди /start ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    async with async_session_maker() as session:
        # Шукаємо юзера за його telegram_id
        stmt = select(User).options(selectinload(User.stats)).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user and user.phone:
            if not user.is_active:
                await state.clear()
                await message.answer("❌ Ваш обліковий запис заблоковано адміністратором.")
                return
            # Якщо юзер вже є і має телефон — пускаємо в застосунок
            await state.clear()
            await message.answer(
                f"З поверненням, {user.full_name}! 👋",
                reply_markup=get_main_menu_kb(message.from_user.id)
            )
        else:
            # Якщо новий — просимо телефон
            await state.set_state(AuthStates.waiting_for_phone)
            await message.answer(
                "Вітаємо в Drogobych Express Taxi! 🚕\n\n"
                "Натисніть кнопку нижче або просто напишіть свій номер телефону (наприклад, +380991234567):",
                reply_markup=get_registration_kb()
            )

from app.core.security import verify_password

# --- 3. Обробка номеру телефону (Контакт АБО Текст) ---
@dp.message(F.contact)
@dp.message(AuthStates.waiting_for_phone, F.text)
async def process_phone(message: types.Message, state: FSMContext):
    # Отримуємо номер з контакту або з тексту
    if message.contact:
        raw_phone = message.contact.phone_number
    else:
        raw_phone = message.text

    # Очищаємо номер від усіх символів крім цифр
    digits = re.sub(r'\D', '', raw_phone)
    if not digits:
        await message.answer("❌ Некоректний номер телефону. Спробуйте ще раз або скористайтеся кнопкою внизу.")
        return

    phone = '+' + digits

    async with async_session_maker() as session:
        # 1. Спершу шукаємо користувача за номером телефону (наприклад, ВОДІЯ, створеного Адміном)
        stmt_phone = select(User).options(selectinload(User.stats)).where(User.phone == phone)
        user_by_phone = (await session.execute(stmt_phone)).scalar_one_or_none()

        # 2. Шукаємо користувача за telegram_id (який міг створитися тимчасово в WebApp)
        stmt_tg = select(User).options(selectinload(User.stats)).where(User.telegram_id == message.from_user.id)
        user_by_tg = (await session.execute(stmt_tg)).scalar_one_or_none()

        user = None
        if user_by_phone:
            user = user_by_phone
            # Якщо існує дублікат без телефону з таким ж telegram_id - видаляємо його
            if user_by_tg and user_by_tg.id != user_by_phone.id and not user_by_tg.phone:
                await session.delete(user_by_tg)
                await session.flush()
        else:
            user = user_by_tg

        if user:
            if not user.is_active:
                await state.clear()
                await message.answer("❌ Ваш обліковий запис заблоковано адміністратором.")
                return

            if user.role == UserRole.DRIVER:
                # ВОДІЙ: Вимагаємо пароль
                await state.set_state(AuthStates.waiting_for_password)
                await state.update_data(user_id=user.id)
                await message.answer(
                    f"🚖 **Вітаємо, {user.full_name}!**\n"
                    f"Знайдено обліковий запис водія. Введіть ваш пароль для входу:"
                )
                return
            else:
                # Пасажир: оновлюємо дані
                user.telegram_id = message.from_user.id
                user.phone = phone
                user.full_name = message.from_user.full_name or user.full_name
                if not user.stats:
                    user.stats = UserStats(total_trips=0, total_noshows=0, trust_score_cached=100)
                await session.commit()
        else:
            # Створюємо нового пасажира
            new_user = User(
                telegram_id=message.from_user.id,
                phone=phone,
                full_name=message.from_user.full_name or "Пасажир",
                role=UserRole.PASSENGER,
                stats=UserStats(total_trips=0, total_noshows=0, trust_score_cached=100)
            )
            session.add(new_user)
            await session.commit()

    # Завершуємо реєстрацію для пасажира
    await state.clear()
    await message.answer(
        "✅ Реєстрацію успішно завершено!",
        reply_markup=get_main_menu_kb(message.from_user.id)
    )

# --- 4. Обробка пароля для ВОДІЯ ---
@dp.message(AuthStates.waiting_for_password, F.text)
async def process_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")

    if not user_id:
        await state.clear()
        await message.answer("❌ Сесія авторизації застаріла. Спробуйте ввести номер телефону знову за допомогою /start.")
        return

    async with async_session_maker() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            await state.clear()
            await message.answer("❌ Користувача не знайдено.")
            return

        # Перевіряємо пароль через bcrypt
        if user.password and verify_password(message.text.strip(), user.password):
            # Перевіряємо, чи є в базі дублікат акаунта без телефону з таким tg_id (напр. створений при відкритті WebApp)
            existing_tg_user = (await session.execute(
                select(User).where(User.telegram_id == message.from_user.id, User.id != user.id)
            )).scalar_one_or_none()

            if existing_tg_user:
                await session.execute(delete(Booking).where(Booking.passenger_id == existing_tg_user.id))
                await session.execute(delete(UserStats).where(UserStats.user_id == existing_tg_user.id))
                await session.execute(delete(AuditLog).where(AuditLog.actor_id == existing_tg_user.id))
                await session.delete(existing_tg_user)
                await session.flush()

            # Успіх! Прив'язуємо tg_id до акаунта водія
            user.telegram_id = message.from_user.id
            user.full_name = message.from_user.full_name or user.full_name
            await session.commit()
            
            await state.clear()
            await message.answer(
                "✅ Пароль прийнято! Авторизація водія успішна.\n"
                "Гарної зміни! Відкрийте панель керування:",
                reply_markup=get_main_menu_kb(message.from_user.id)
            )
        else:
            await message.answer("❌ Невірний пароль. Спробуйте ще раз:")

# --- 5. Захист: будь-яке інше повідомлення від незареєстрованого користувача ---
@dp.message()
async def unauth_message_handler(message: types.Message, state: FSMContext):
    async with async_session_maker() as session:
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user and user.phone:
            await message.answer("Оберіть потрібну дію в меню нижче:", reply_markup=get_main_menu_kb(message.from_user.id))
        else:
            if message.contact or (message.text and re.search(r'\d{7,}', message.text)):
                await process_phone(message, state)
                return

            await state.set_state(AuthStates.waiting_for_phone)
            await message.answer(
                "⚠️ **Для користування сервісом Express Taxi необхідно завершити реєстрацію!**\n\n"
                "Будь ласка, натисніть кнопку «📱 Поділитися номером» внизу або введіть ваш номер телефону:",
                reply_markup=get_registration_kb()
            )

async def main():
    logging.info("🚀 Бот з FSM Авторизацією запущений")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот зупинений")