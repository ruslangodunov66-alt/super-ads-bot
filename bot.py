import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_IDS = [1475910449]  # ← твой ID
CHANNEL_ID = -1003767084450

if not BOT_TOKEN:
    raise ValueError("Токен не найден!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_data = {}

def moderation_keyboard(ad_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{ad_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Бот работает. Команда: /moderate")

@dp.message(Command("moderate"))
async def moderate(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет прав")
        return
    # Здесь должна быть логика получения объявлений из БД
    # Если объявлений нет, ответить "Нет объявлений"
    await message.answer("🛡 Модерация (демо). Добавьте логику БД")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    await message.answer("Фото получено. Теперь напиши описание.")

@dp.message(F.text)
async def handle_text(message: types.Message):
    await message.answer("Текст получен. Объявление отправлено на модерацию.")

async def main():
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())