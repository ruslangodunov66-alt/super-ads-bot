import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from database import init_db, add_user, add_ad, get_pending_ads, update_ad_status, get_user_balance, update_user_balance, get_referral_count, is_admin, get_ad_by_id, get_game_data, update_game_data

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
        [InlineKeyboardButton(text="⭐ Реферальная система", callback_data="referral")],
        [InlineKeyboardButton(text="🎮 Торговый симулятор", callback_data="game_menu")]
    ]
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton(text="🛡 Модерация", callback_data="moderate")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

def game_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Сделать продажу (+10💰)", callback_data="game_sell")],
        [InlineKeyboardButton(text="📦 Закупить товар (+5💰)", callback_data="game_buy")],
        [InlineKeyboardButton(text="⚡ Восстановить энергию (5💰)", callback_data="game_energy")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]
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
        "👋 Привет! Меня создал предприниматель, который прошёл через все трудности товарного бизнеса. "
        "Я — его система, которая помогает молодым продавцам торговать легко и без лишних проблем.\n\n"
        "📌 *Что я умею:*\n"
        "• Принимать объявления о товарах\n"
        "• Помогать с реферальной программой (зарабатывай на приглашениях)\n"
        "• Обучать товарному бизнесу через игру\n"
        "• Публиковать одобренные объявления в канале\n\n"
        "👇 *Выбери действие:*",
        reply_markup=main_keyboard(user.id),
        parse_mode=ParseMode.MARKDOWN
    )


# ========== ОБЪЯВЛЕНИЯ ==========

@dp.callback_query(F.data == "submit_ad")
async def submit_ad_start(callback: types.CallbackQuery):
    await callback.message.answer("📸 *Отправьте фото товара*\n\nЗатем напишите описание и цену.", parse_mode=ParseMode.MARKDOWN)
    await callback.answer()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user_data[message.from_user.id] = {'photo_id': message.photo[-1].file_id}
    await message.answer("✍️ *Теперь напишите описание и цену*\n\nПример: iPhone 14 Pro, 256GB, отличное состояние. 70 000 руб.", parse_mode=ParseMode.MARKDOWN)

@dp.message(F.text)
async def handle_description(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data or 'photo_id' not in user_data[user_id]:
        await message.answer("❌ Сначала отправьте фото товара!")
        return
    add_ad(user_id, message.from_user.username, user_data[user_id]['photo_id'], message.text)
    await message.answer("✅ *Объявление отправлено на модерацию!*", parse_mode=ParseMode.MARKDOWN, reply_markup=main_keyboard(user_id))
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
    balance = get_user_balance(user_id)
    referrals = get_referral_count(user_id)
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    text = (
        "⭐ *РЕФЕРАЛЬНАЯ ПРОГРАММА* ⭐\n\n"
        f"💎 Ваш баланс: *{balance} руб.*\n"
        f"👥 Приглашено друзей: *{referrals}*\n\n"
        f"🔗 Ваша ссылка: `https://t.me/{bot_username}?start={user_id}`\n\n"
        "🤝 *Как это работает:*\n"
        "• Вы приглашаете друга по ссылке\n"
        "• Он регистрируется в боте\n"
        "• Вы получаете *50 руб.* на баланс\n\n"
        "💰 *Вывод средств:*\n"
        "Накопите от 500 руб. и напишите /withdraw"
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "my_profile")
async def my_profile(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = get_user_balance(user_id)
    referrals = get_referral_count(user_id)
    text = (
        "👤 *Ваш профиль*\n\n"
        f"💰 Баланс: *{balance} руб.*\n"
        f"👥 Приглашено: *{referrals}* чел.\n"
        f"🆔 ID: `{user_id}`"
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()


# ========== МИНИ-ИГРА ==========

@dp.callback_query(F.data == "game_menu")
async def game_menu(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = get_game_data(user_id)
    text = (
        "🎮 *ТОРГОВЫЙ СИМУЛЯТОР* 🎮\n\n"
        "Здесь ты учишься основам товарного бизнеса:\n"
        "• Делай продажи и получай опыт\n"
        "• Закупай товар для перепродажи\n"
        "• Следи за энергией — без неё нельзя торговать\n\n"
        f"📊 *Статистика:*\n"
        f"💼 Опыт: *{game['score']}* очков\n"
        f"⚡ Энергия: *{game['energy']}*%\n\n"
        "👇 *Выбери действие:*"
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=game_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "game_sell")
async def game_sell(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = get_game_data(user_id)
    if game['energy'] < 20:
        await callback.answer("❌ Недостаточно энергии! Восстанови её.", show_alert=True)
        return
    profit = random.randint(5, 25)
    update_game_data(user_id, profit, -20)
    await callback.answer(f"✅ Продажа совершена! +{profit}💰", show_alert=True)
    await game_menu(callback)

@dp.callback_query(F.data == "game_buy")
async def game_buy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    game = get_game_data(user_id)
    if game['energy'] < 10:
        await callback.answer("❌ Недостаточно энергии! Восстанови её.", show_alert=True)
        return
    exp_gain = random.randint(5, 15)
    update_game_data(user_id, exp_gain, -10)
    await callback.answer(f"📦 Удачная закупка! +{exp_gain}💰", show_alert=True)
    await game_menu(callback)

@dp.callback_query(F.data == "game_energy")
async def game_energy(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = get_user_balance(user_id)
    if balance < 5:
        await callback.answer("❌ Недостаточно средств (нужно 5 руб.)", show_alert=True)
        return
    update_user_balance(user_id, -5)
    update_game_data(user_id, 0, 50)
    await callback.answer("⚡ Энергия восстановлена на +50%!", show_alert=True)
    await game_menu(callback)


# ========== МОДЕРАЦИЯ ==========

@dp.message(Command("moderate"))
async def cmd_moderate(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет прав для этой команды.")
        return
    pending = get_pending_ads()
    if not pending:
        await message.answer("📭 Нет объявлений на модерации.")
        return
    for ad in pending:
        ad_id, user_id_ad, username, photo_id, desc = ad
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{ad_id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")]
        ])
        await message.answer_photo(photo=photo_id, caption=f"📦 *Объявление #{ad_id}*\n👤 От: @{username}\n📝 {desc}", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

@dp.callback_query(F.data.startswith("approve_"))
async def approve_ad(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав!")
        return
    ad_id = int(callback.data.split("_")[1])
    ad = get_ad_by_id(ad_id)
    if ad:
        await bot.send_photo(chat_id=CHANNEL_ID, photo=ad['photo_id'], caption=f"📢 *НОВОЕ ОБЪЯВЛЕНИЕ!*\n\n{ad['description']}", parse_mode=ParseMode.MARKDOWN)
    update_ad_status(ad_id, "approved")
    await callback.message.edit_caption("✅ Объявление одобрено и опубликовано!")
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_ad(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав!")
        return
    ad_id = int(callback.data.split("_")[1])
    update_ad_status(ad_id, "rejected")
    await callback.message.edit_caption("❌ Объявление отклонено.")
    await callback.answer()


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
    print("🚀 Бот ReSell запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())