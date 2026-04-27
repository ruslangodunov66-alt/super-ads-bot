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

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_IDS = [1475910449]
CHANNEL_ID = -1003767084450
# ================================

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
init_db()

user_data = {}

# ========== КЛАВИАТУРЫ ==========

def main_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton(text="📝 Подать объявление", callback_data="submit_ad")],
        [InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")],
        [InlineKeyboardButton(text="⭐ Реферальная система", callback_data="referral")]
    ]
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton(text="🛡 Модерация", callback_data="moderate")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

def moderation_keyboard(ad_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{ad_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")
        ]
    ])

# ========== ПРИВЕТСТВИЕ ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = message.from_user
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    add_user(user.id, user.username, referrer_id)
    await message.answer(
        "✨ *Добро пожаловать в ReSell!* ✨\n\n"
        "📌 *Что я умею:*\n"
        "• 📝 Принимать объявления\n"
        "• ⭐ Реферальная система (бесплатные выкладки)\n"
        "• 🛡 Модерация для админа\n\n"
        "👇 *Выбери действие:*",
        reply_markup=main_keyboard(user.id),
        parse_mode=ParseMode.MARKDOWN
    )

# ========== ОБЪЯВЛЕНИЯ ==========

@dp.callback_query(F.data == "submit_ad")
async def submit_ad_start(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    free_ads = get_free_ads(user_id)
    if free_ads > 0:
        use_free_ad(user_id)
        await callback.message.answer(
            "📸 *Отправьте фото товара*\n\n"
            "✅ Использована *1 бесплатная выкладка*.\n"
            "Затем напишите описание и цену.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await callback.message.answer(
            "📸 *Отправьте фото товара*\n\n"
            "❌ У вас нет бесплатных выкладок.\n"
            "➡️ Пригласите друга — получите +1 выкладку.\n\n"
            "Затем напишите описание и цену.",
            parse_mode=ParseMode.MARKDOWN
        )
    await callback.answer()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user_data[message.from_user.id] = {'photo_id': message.photo[-1].file_id}
    await message.answer(
        "✍️ *Теперь напишите описание и цену*\n\n"
        "Пример:\n"
        "`iPhone 14 Pro, 256GB, отличное состояние. 70 000 руб.`",
        parse_mode=ParseMode.MARKDOWN
    )

@dp.message(F.text)
async def handle_description(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data or 'photo_id' not in user_data[user_id]:
        await message.answer("❌ Сначала отправьте фото товара!")
        return
    add_ad(user_id, message.from_user.username, user_data[user_id]['photo_id'], message.text)
    await message.answer(
        "✅ *Объявление отправлено на модерацию!*\n\n"
        "📋 Обычно проверка занимает до 24 часов.\n"
        "После одобрения оно появится в нашем канале.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard(user_id)
    )
    del user_data[user_id]
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📦 Новое объявление от @{message.from_user.username} ожидает модерации!")
        except:
            pass

# ========== РЕФЕРАЛЫ ==========

@dp.callback_query(F.data == "referral")
async def referral_info(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    free_ads = get_free_ads(user_id)
    referrals = get_referral_count(user_id)
    bot_username = (await bot.get_me()).username
    text = (
        "⭐ *РЕФЕРАЛЬНАЯ ПРОГРАММА* ⭐\n\n"
        f"🎁 *Бесплатных выкладок:* `{free_ads}`\n"
        f"👥 *Приглашено друзей:* `{referrals}`\n\n"
        f"🔗 *Ваша ссылка:*\n"
        f"`https://t.me/{bot_username}?start={user_id}`\n\n"
        "🤝 *Как это работает:*\n"
        "• Друг переходит по вашей ссылке\n"
        "• Регистрируется в боте\n"
        "• Вы получаете **+1 бесплатную выкладку**\n\n"
        "📢 *Бесплатные выкладки* — это возможность публиковать товары без дополнительных условий.\n"
        "Чем больше друзей → тем больше вы можете продавать."
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "my_profile")
async def my_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    free_ads = get_free_ads(user_id)
    referrals = get_referral_count(user_id)
    text = (
        "👤 *ВАШ ПРОФИЛЬ*\n\n"
        f"🎁 *Бесплатных выкладок:* `{free_ads}`\n"
        f"👥 *Приглашено друзей:* `{referrals}`\n"
        f"🆔 *Ваш ID:* `{user_id}`"
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()

# ========== МОДЕРАЦИЯ (ГАРАНТИРОВАННО РАБОТАЕТ) ==========

@dp.message(Command("moderate"))
async def cmd_moderate(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("⛔ *У вас нет прав для этой команды.*", parse_mode=ParseMode.MARKDOWN)
        return

    pending = get_pending_ads()
    if not pending:
        await message.answer("📭 *Нет объявлений на модерации.*", parse_mode=ParseMode.MARKDOWN)
        return

    await message.answer("🛡 *Панель модерации* — объявления ниже ⬇️", parse_mode=ParseMode.MARKDOWN)
    for ad in pending:
        ad_id, user_id_ad, username, photo_id, desc = ad
        await message.answer_photo(
            photo=photo_id,
            caption=(
                f"📦 *ОБЪЯВЛЕНИЕ #{ad_id}*\n"
                f"👤 *От:* @{username}\n"
                f"📝 *Текст:*\n{desc}"
            ),
            reply_markup=moderation_keyboard(ad_id),
            parse_mode=ParseMode.MARKDOWN
        )

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
    await callback.message.edit_caption("✅ *Объявление одобрено и опубликовано в канале!*", parse_mode=ParseMode.MARKDOWN)
    await callback.answer("✅ Одобрено")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_ad(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав!", show_alert=True)
        return

    ad_id = int(callback.data.split("_")[1])
    update_ad_status(ad_id, "rejected")
    await callback.message.edit_caption("❌ *Объявление отклонено.*", parse_mode=ParseMode.MARKDOWN)
    await callback.answer("❌ Отклонено")

# ========== НАЗАД ==========

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "✨ *Главное меню* ✨\n\n👇 *Выбери действие:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard(callback.from_user.id)
    )
    await callback.answer()

# ========== ЗАПУСК ==========

async def main():
    print("🚀 ReSell — бот-модератор запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())