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
from sqlalchemy import select

# Імпортуємо налаштування та моделі
from app.core.config import settings
from app.db.database import async_session_maker
from app.db.models import User, UserStats, UserRole

logging.basicConfig(level=logging.INFO)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

# УВАГА: Заміни це посилання на своє актуальне з ngrok!
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

def get_main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚕 Запустити Express Taxi", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])

# --- 2. Обробка команди /start ---
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    async with async_session_maker() as session:
        # Шукаємо юзера за його telegram_id
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user and user.phone:
            # Якщо юзер вже є і має телефон — пускаємо в застосунок
            await state.clear()
            await message.answer(
                f"З поверненням, {user.full_name}! 👋",
                reply_markup=get_main_menu_kb()
            )
        else:
            # Якщо новий — просимо телефон
            await state.set_state(AuthStates.waiting_for_phone)
            await message.answer(
                "Вітаємо в Drogobych Express Taxi! 🚕\n\n"
                "Натисніть кнопку нижче, щоб поділитися своїм номером телефону для реєстрації:",
                reply_markup=get_registration_kb()
            )

# --- 3. Обробка номеру телефону (ТІЛЬКИ КОНТАКТ) ---
@dp.message(AuthStates.waiting_for_phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    # БЕЗПЕКА: Перевіряємо, чи це дійсно номер користувача (а не чужий контакт)
    if message.contact.user_id != message.from_user.id:
        await message.answer(
            "❌ З метою безпеки, будь ласка, надішліть САМЕ ВАШ контакт, використовуючи кнопку внизу.",
            reply_markup=get_registration_kb()
        )
        return

    raw_phone = message.contact.phone_number

    # Очищаємо номер від пробілів та дужок
    phone = re.sub(r'[^\d+]', '', raw_phone)
    if not phone.startswith('+'):
        phone = '+' + phone

    async with async_session_maker() as session:
        stmt = select(User).where(User.phone == phone)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            if user.role == UserRole.DRIVER:
                # Це ВОДІЙ! Переводимо в стан очікування пароля
                await state.update_data(user_id=user.id)
                await state.set_state(AuthStates.waiting_for_password)
                await message.answer(
                    "🚖 Система розпізнала вас як Водія.\n"
                    "Будь ласка, введіть ваш пароль для доступу:",
                    reply_markup=ReplyKeyboardRemove() # Прибираємо кнопку контакту
                )
                return
            else:
                # Це існуючий пасажир, оновлюємо його tg_id
                user.telegram_id = message.from_user.id
                user.full_name = message.from_user.full_name
                await session.commit()
        else:
            # Це новий ПАСАЖИР
            new_user = User(
                telegram_id=message.from_user.id,
                phone=phone,
                full_name=message.from_user.full_name,
                role=UserRole.PASSENGER,
                stats=UserStats(total_trips=0, total_noshows=0, trust_score_cached=100)
            )
            session.add(new_user)
            await session.commit()

    # Завершуємо реєстрацію для пасажира
    await state.clear()
    
    # UX ПРАВКА: Спочатку надсилаємо повідомлення, яке ПРИХОВАЄ клавіатуру контакту
    await message.answer("✅ Номер успішно підтверджено!", reply_markup=ReplyKeyboardRemove())
    
    # Потім надсилаємо меню з WebApp
    await message.answer(
        "Реєстрацію завершено! Тепер ви можете бронювати квитки 👇",
        reply_markup=get_main_menu_kb()
    )

# --- 3.1. Захист від хитрощів (Якщо користувач ввів текст замість натискання кнопки) ---
@dp.message(AuthStates.waiting_for_phone)
async def process_phone_invalid(message: types.Message):
    # Тільки сваримо і нагадуємо про кнопку. Стан НЕ очищаємо!
    await message.answer(
        "❌ Будь ласка, використовуйте спеціальну кнопку «📱 Поділитися номером» внизу екрану.\n"
        "(Якщо кнопки немає, натисніть на іконку з 4 квадратиками біля поля вводу тексту).",
        reply_markup=get_registration_kb()
    )

# --- 4. Обробка пароля для ВОДІЯ ---
@dp.message(AuthStates.waiting_for_password, F.text)
async def process_password(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get("user_id")

    async with async_session_maker() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one()

        # Перевіряємо пароль
        if message.text == user.password:
            # Успіх! Прив'язуємо tg_id
            user.telegram_id = message.from_user.id
            user.full_name = message.from_user.full_name
            await session.commit()
            
            await state.clear()
            await message.answer(
                "✅ Пароль прийнято! Авторизація водія успішна.\n"
                "Гарної зміни! Відкрийте панель керування:",
                reply_markup=get_main_menu_kb()
            )
        else:
            await message.answer("❌ Невірний пароль. Спробуйте ще раз:")

from aiogram.types import MenuButtonWebApp, WebAppInfo

async def main():
    # Встановлюємо кнопку меню, яка завжди висітиме зліва від поля вводу
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🚕 Відкрити таксі",
            web_app=WebAppInfo(url=WEB_APP_URL)
        )
    )
    logging.info("🚀 Бот запущений")
    await dp.start_polling(bot)
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот зупинений")