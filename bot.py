import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from database import (
    init_db, add_user, add_ad, get_pending_ads, update_ad_status,
    get_user_balance, update_user_balance, get_referral_count,
    is_admin, get_ad_by_id, get_game_state, update_game_state,
    set_product, set_demand_price
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
        [InlineKeyboardButton(text="🏪 Зайти в магазин", callback_data="game_shop")],
        [InlineKeyboardButton(text="📈 Узнать спрос", callback_data="game_demand")],
        [InlineKeyboardButton(text="🔄 Обновить товар/цену", callback_data="game_refresh")],
        [InlineKeyboardButton(text="🤝 Сделать продажу", callback_data="game_sell")],
        [InlineKeyboardButton(text="🔙 Вернуться", callback_data="back_to_main")]
    ])

def shop_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Смартфон", callback_data="set_product_smartphone")],
        [InlineKeyboardButton(text="💻 Ноутбук", callback_data="set_product_laptop")],
        [InlineKeyboardButton(text="⌚ Часы", callback_data="set_product_watch")],
        [InlineKeyboardButton(text="🎧 Наушники", callback_data="set_product_earphones")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="game_menu")]
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
        "👋 Привет! Я создан предпринимателем, который прошёл через все трудности товарного бизнеса.\n"
        "Я помогаю молодым продавцам торговать легко.\n\n"
        "📌 *Что я умею:*\n"
        "• Принимать объявления\n"
        "• Реферальная программа\n"
        "• Торговый симулятор (реалистичный бизнес)\n\n"
        "👇 *Выбери действие:*",
        reply_markup=main_keyboard(user.id),
        parse_mode=ParseMode.MARKDOWN
    )

# ========== ОБЪЯВЛЕНИЯ ==========

@dp.callback_query(F.data == "submit_ad")
async def submit_ad_start(callback: types.CallbackQuery):
    await callback.message.answer(
        "📸 *Отправьте фото товара*\n\nЗатем напишите описание и цену.",
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    user_data[message.from_user.id] = {'photo_id': message.photo[-1].file_id}
    await message.answer(
        "✍️ *Теперь напишите описание и цену*\n\n"
        "Пример: iPhone 14 Pro, 256GB, отличное состояние. 70 000 руб.",
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
        "Обычно проверка занимает до 24 часов.\n"
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
    balance = get_user_balance(user_id)
    referrals = get_referral_count(user_id)
    bot_username = (await bot.get_me()).username
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
        f"👥 Вы пригласили: *{referrals}* чел.\n"
        f"🆔 Ваш ID: `{user_id}`"
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()

# ========== ТОРГОВЫЙ СИМУЛЯТОР (ПОЛНАЯ ВЕРСИЯ) ==========

@dp.callback_query(F.data == "game_menu")
async def game_menu(callback: types.CallbackQuery):
    state = get_game_state(callback.from_user.id)
    xp_to_level = state['level'] * 100
    text = (
        "🎮 *ТОРГОВЫЙ РЕАЛИТИ* 🎮\n\n"
        "Управляй своим товаром, учитывай спрос и побеждай конкурентов.\n\n"
        f"📊 *Ваш бизнес:*\n"
        f"Уровень: *{state['level']}*\n"
        f"Опыт: *{state['xp']} / {xp_to_level}*\n"
        f"Товар: *{state['product']}*\n"
        f"💰 Цена: *{state['price']}* руб.\n"
        f"📈 Спрос: *{state['demand']}*\n\n"
        "👇 *Выбери действие:*"
    )
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=game_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "game_shop")
async def game_shop(callback: types.CallbackQuery):
    await callback.message.edit_text("🏪 *Выбери товар для продажи:*", parse_mode=ParseMode.MARKDOWN, reply_markup=shop_keyboard())
    await callback.answer()

@dp.callback_query(F.data.startswith("set_product_"))
async def set_product_handler(callback: types.CallbackQuery):
    product_map = {
        "set_product_smartphone": "смартфон",
        "set_product_laptop": "ноутбук",
        "set_product_watch": "часы",
        "set_product_earphones": "наушники"
    }
    new_product = product_map.get(callback.data)
    if new_product:
        set_product(callback.from_user.id, new_product)
        await callback.answer(f"✅ Товар изменён на {new_product}!")
        await game_menu(callback)
    else:
        await callback.answer("❌ Ошибка", show_alert=True)

@dp.callback_query(F.data == "game_demand")
async def game_demand(callback: types.CallbackQuery):
    demands = ["критически низкий ❌", "низкий 📉", "средний 📊", "высокий 📈", "ажиотаж 🔥"]
    demand = random.choice(demands)
    price = random.randint(100, 1000)
    set_demand_price(callback.from_user.id, demand, price)
    await callback.answer(f"📊 Спрос: {demand}\n💰 Цена: {price} руб.", show_alert=True)
    await game_menu(callback)

@dp.callback_query(F.data == "game_refresh")
async def game_refresh(callback: types.CallbackQuery):
    new_price = random.randint(100, 1000)
    state = get_game_state(callback.from_user.id)
    set_demand_price(callback.from_user.id, state['demand'], new_price)
    await callback.answer(f"💰 Цена обновлена: {new_price} руб.", show_alert=True)
    await game_menu(callback)

@dp.callback_query(F.data == "game_sell")
async def game_sell(callback: types.CallbackQuery):
    state = get_game_state(callback.from_user.id)
    profit = state['price'] - 50
    if profit <= 0:
        await callback.answer("❌ Ты не можешь заработать — цена слишком низкая.", show_alert=True)
        return

    competitor_price = random.randint(int(state['price'] * 0.7), int(state['price'] * 1.5))
    if competitor_price < state['price']:
        await callback.answer(
            f"❌ *Конкуренция!*\n"
            f"Конкурент продал по цене {competitor_price} руб.\n"
            f"Твой товар не купили.",
            show_alert=True
        )
        return

    # успешная продажа
    update_user_balance(callback.from_user.id, profit)

    new_xp = state['xp'] + 20
    new_level = state['level']
    level_up_msg = ""
    if new_xp >= state['level'] * 100:
        new_level += 1
        new_xp = 0
        update_user_balance(callback.from_user.id, 100)
        level_up_msg = f"\n🎉 *УРОВЕНЬ ПОВЫШЕН до {new_level}!*\n💰 Бонус: +100 руб."

    update_game_state(callback.from_user.id, new_level, new_xp)

    await callback.answer(
        f"✅ *Успешная продажа!*\n"
        f"💰 Выручка: +{profit} руб.\n"
        f"📈 Опыт: +20{level_up_msg}",
        show_alert=True
    )
    await game_menu(callback)

# ========== МОДЕРАЦИЯ (ИСПРАВЛЕНА И НЕ КОНФЛИКТУЕТ) ==========

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
        await message.answer_photo(
            photo=photo_id,
            caption=f"📦 *Объявление #{ad_id}*\n👤 От: @{username}\n📝 {desc}",
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
            caption=f"📢 *НОВОЕ ОБЪЯВЛЕНИЕ!*\n\n{ad['description']}",
            parse_mode=ParseMode.MARKDOWN
        )
    update_ad_status(ad_id, "approved")
    await callback.message.edit_caption("✅ Объявление одобрено и опубликовано в канале!")
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_"))
async def reject_ad(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав!", show_alert=True)
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
    print("🚀 Бот ReSell успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())