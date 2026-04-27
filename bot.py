import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.enums import ParseMode

from database import init_db, add_user, add_ad, get_pending_ads, update_ad_status, get_user_balance, get_referral_count, is_admin

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = os.environ.get('API_TOKEN')
ADMIN_IDS = [1475910449]  # Ваш Telegram ID
CHANNEL_ID = -1003767084450  # ID вашего канала
# ================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Инициализация базы данных
init_db()


# ========== КЛАВИАТУРЫ ==========

def main_keyboard():
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Подать объявление", callback_data="submit_ad"),
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="my_profile")
        ],
        [
            InlineKeyboardButton(text="⭐ Реферальная система", callback_data="referral"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ])
    return keyboard

def admin_keyboard():
    """Меню админа"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛡 Панель модерации", callback_data="moderate"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
        ]
    ])
    return keyboard


# ========== ОБРАБОТЧИКИ КОМАНД ==========

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Приветствие и регистрация пользователя"""
    user = message.from_user
    
    # Проверяем реферальный код
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
    
    add_user(user.id, user.username, referrer_id)
    
    await message.answer(
        "✨ *Добро пожаловать в SUPER ADS BOT!* ✨\n\n"
        "Здесь вы можете:\n"
        "📝 *Подать объявление* — ваше предложение увидят все\n"
        "⭐ *Зарабатывать* — приглашайте друзей и получайте бонусы\n"
        "💎 *Выгодные покупки* — только проверенные продавцы\n\n"
        "👇 *Выберите действие ниже:*",
        reply_markup=main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


@dp.callback_query(F.data == "submit_ad")
async def submit_ad_start(callback: types.CallbackQuery):
    """Начало подачи объявления"""
    await callback.message.answer(
        "📸 *Отправьте фото вашего товара*\n\n"
        "После этого напишите описание и цену.",
        parse_mode=ParseMode.MARKDOWN
    )
    await callback.answer()


@dp.message(F.photo)
async def handle_photo(message: types.Message):
    """Сохраняем фото и ждём описание"""
    photo = message.photo[-1]
    # Временно сохраняем photo_id в состоянии (простой способ — передаём в следующий шаг)
    # В реальном проекте лучше использовать FSMContext из aiogram
    user_data[message.from_user.id] = {'photo_id': photo.file_id}
    await message.answer(
        "✍️ *Теперь напишите описание и цену товара.*\n\n"
        "Пример:\n"
        "`iPhone 14 Pro, 256GB, отличное состояние. 70 000 руб.`",
        parse_mode=ParseMode.MARKDOWN
    )


@dp.message(F.text)
async def handle_description(message: types.Message):
    """Сохраняем описание и создаём объявление"""
    user_id = message.from_user.id
    if user_id not in user_data or 'photo_id' not in user_data[user_id]:
        await message.answer("❌ Сначала отправьте фото товара!")
        return
    
    photo_id = user_data[user_id]['photo_id']
    description = message.text
    
    # Сохраняем в базу
    add_ad(user_id, message.from_user.username, photo_id, description)
    
    await message.answer(
        "✅ *Ваше объявление отправлено на модерацию!*\n\n"
        "Обычно проверка занимает до 24 часов.\n"
        "После одобрения оно появится в нашем канале.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )
    del user_data[user_id]
    
    # Уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"📦 Новое объявление от @{message.from_user.username} ожидает модерации!")
        except:
            pass


# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========

@dp.callback_query(F.data == "referral")
async def referral_info(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    balance = get_user_balance(user_id)
    referrals = get_referral_count(user_id)
    
    text = (
        "⭐ *РЕФЕРАЛЬНАЯ ПРОГРАММА* ⭐\n\n"
        f"💎 Ваш баланс: *{balance} руб.*\n"
        f"👥 Приглашено друзей: *{referrals}*\n\n"
        "🔗 *Ваша реферальная ссылка:*\n"
        f"`https://t.me/{bot.username}?start={user_id}`\n\n"
        "🤝 *Как это работает:*\n"
        "• Вы приглашаете друга по ссылке\n"
        "• Он регистрируется в боте\n"
        "• Вы получаете *50 руб.* на баланс\n\n"
        "💰 *Вывод средств:*\n"
        "Накопите от 500 руб. и напишите /withdraw"
    )
    
    await callback.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
    await callback.answer()


# ========== МОДЕРАЦИЯ ДЛЯ АДМИНА ==========

@dp.callback_query(F.data == "moderate")
async def moderate_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ У вас нет прав администратора!")
        return
    
    pending = get_pending_ads()
    if not pending:
        await callback.message.answer("📭 Нет объявлений на модерации.")
        return
    
    for ad in pending:
        ad_id, user_id, username, photo_id, desc = ad
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_{ad_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{ad_id}")
            ]
        ])
        await callback.message.answer_photo(
            photo=photo_id,
            caption=f"📦 *Объявление #{ad_id}*\n👤 От: @{username}\n📝 {desc}",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("approve_"))
async def approve_ad(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав!")
        return
    
    ad_id = int(callback.data.split("_")[1])
    
    # Получаем объявление из базы (здесь нужно дописать функцию get_ad_by_id)
    # Для простоты считаем, что объявление существует
    
    update_ad_status(ad_id, "approved")
    await callback.message.edit_caption("✅ Объявление одобрено и будет опубликовано в канале.")
    # Здесь добавить публикацию в канал
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


# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

# В главное меню добавьте проверку на админа
def main_keyboard(user_id):
    buttons = [
        [InlineKeyboardButton(text="📝 Подать объявление", callback_data="submit_ad")],
        [InlineKeyboardButton(text="⭐ Реферальная система", callback_data="referral")]
    ]
    if user_id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton(text="🛡 Модерация", callback_data="moderate")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "✨ *Главное меню* ✨\n\nВыберите действие:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("approve_"))
async def approve_ad(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет прав!")
        return
    
    ad_id = int(callback.data.split("_")[1])
    
    # Получаем объявление из базы (нужно добавить функцию get_ad_by_id)
    # ad = get_ad_by_id(ad_id)
    
    # Публикуем в канал
    await bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=ad['photo_id'],
        caption=f"📢 *НОВОЕ ОБЪЯВЛЕНИЕ!*\n\n{ad['description']}",
        parse_mode="Markdown"
    )
    
    update_ad_status(ad_id, "approved")
    await callback.message.edit_caption("✅ Объявление одобрено и опубликовано в канале.")
    await callback.answer()

def get_ad_by_id(ad_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id, username, photo_id, description FROM ads WHERE id = ?', (ad_id,))
    result = cur.fetchone()
    conn.close()
    if result:
        return {
            'user_id': result[0],
            'username': result[1],
            'photo_id': result[2],
            'description': result[3]
        }
    return None


# ========== ЗАПУСК ==========

user_data = {}

async def main():
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())