import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from database import (
    init_db, add_user, add_ad, get_pending_ads, update_ad_status,
    get_free_ads, use_free_ad, get_referral_count, is_admin, get_ad_by_id
)

BOT_TOKEN = os.environ.get("8792353409:AAElSEym-1092XLoSL5bIlwfNqySymIlvKE")
ADMIN_IDS = [1475910449]
CHANNEL_ID = -1003767084450

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
init_db()
user_data = {}

# ========== КЛАВИАТУРЫ ==========
def moderation_keyboard(ad_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{ad_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")]
    ])

# ========== КОМАНДЫ (СНАЧАЛА!) ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    add_user(user.id, user.username, referrer_id)
    await message.answer(
        "✨ *Добро пожаловать в ReSell!* ✨\n\n"
        "👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(Command("moderate"))
async def cmd_moderate(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ *У вас нет прав.*", parse_mode=ParseMode.MARKDOWN)
        return

    pending = get_pending_ads()
    if not pending:
        await message.answer("📭 *Нет объявлений.*", parse_mode=ParseMode.MARKDOWN)
        return

    for ad in pending:
        ad_id, user_id_ad, username, photo_id, desc = ad
        await message.answer_photo(
            photo=photo_id,
            caption=f"📦 *Объявление #{ad_id}*\n👤 @{username}\n📝 {desc}",
            reply_markup=moderation_keyboard(ad_id),
            parse_mode=ParseMode.MARKDOWN
        )

# ========== ОБЪЯВЛЕНИЯ ==========
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user_data[message.from_user.id] = {'photo_id': message.photo[-1].file_id}
    await message.answer("✍️ *Теперь напишите описание и цену.*", parse_mode=ParseMode.MARKDOWN)

@dp.message(F.text)
async def handle_description(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data or 'photo_id' not in user_data[user_id]:
        await message.answer("❌ Сначала отправьте фото!")
        return
    add_ad(user_id, message.from_user.username, user_data[user_id]['photo_id'], message.text)
    await message.answer("✅ *Объявление отправлено на модерацию!*", parse_mode=ParseMode.MARKDOWN)
    del user_data[user_id]

    # Уведомление админу
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, "📦 Новое объявление ожидает модерации! Отправь /moderate")
        except:
            pass

# ========== КНОПКИ МОДЕРАЦИИ ==========
@dp.callback_query(F.data.startswith("approve_"))
async def approve_ad(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    ad_id = int(callback.data.split("_")[1])
    ad = get_ad_by_id(ad_id)
    if ad:
        await bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=ad['photo_id'],
            caption=f"✨ *НОВОЕ ОБЪЯВЛЕНИЕ!* ✨\n\n{ad['description']}",
            parse_mode=ParseMode.MARKDOWN
        )
    update_ad_status(ad_id, "approved")
    await callback.message.edit_caption("✅ *Одобрено и опубликовано в канале!*", parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_ad(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return
    ad_id = int(callback.data.split("_")[1])
    update_ad_status(ad_id, "rejected")
    await callback.message.edit_caption("❌ *Отклонено.*", parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.callback_query(F.data == "moderate")
async def moderate_button(callback: types.CallbackQuery):
    """Обработчик кнопки 'Модерация' из главного меню"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав для модерации.", show_alert=True)
        return

    pending = get_pending_ads()
    if not pending:
        await callback.message.answer("📭 *Нет объявлений на модерации.*", parse_mode=ParseMode.MARKDOWN)
        await callback.answer()
        return

    await callback.message.answer("🛡 *Панель модерации* — объявления ниже ⬇️", parse_mode=ParseMode.MARKDOWN)
    for ad in pending:
        ad_id, user_id_ad, username, photo_id, desc = ad
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{ad_id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")]
        ])
        await callback.message.answer_photo(
            photo=photo_id,
            caption=f"📦 *Объявление #{ad_id}*\n👤 От: @{username}\n📝 {desc}",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    await callback.answer()

async def main():
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())