import sqlite3
from datetime import datetime

DB_NAME = "ads_bot.db"

def init_db():
    """Создаёт таблицы при первом запуске"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # Таблица объявлений
    cur.execute('''
        CREATE TABLE IF NOT EXISTS ads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            photo_id TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP
        )
    ''')
    
    # Таблица пользователей и рефералов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            reg_date TIMESTAMP,
            referrer_id INTEGER,
            balance INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица для админов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(user_id, username, referrer_id=None):
    """Добавляет нового пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if not cur.fetchone():
        cur.execute('''
            INSERT INTO users (user_id, username, reg_date, referrer_id, balance)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, datetime.now(), referrer_id, 0))
        
        # Если есть реферер, начисляем ему бонус
        if referrer_id:
            cur.execute('UPDATE users SET balance = balance + 50 WHERE user_id = ?', (referrer_id,))
    
    conn.commit()
    conn.close()

def add_ad(user_id, username, photo_id, description):
    """Добавляет объявление в базу"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO ads (user_id, username, photo_id, description, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
    ''', (user_id, username, photo_id, description, datetime.now()))
    conn.commit()
    conn.close()
    return cur.lastrowid

def get_pending_ads():
    """Получает все объявления на модерации"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, username, photo_id, description FROM ads WHERE status = "pending" ORDER BY created_at')
    ads = cur.fetchall()
    conn.close()
    return ads

def update_ad_status(ad_id, status):
    """Обновляет статус объявления"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE ads SET status = ? WHERE id = ?', (status, ad_id))
    conn.commit()
    conn.close()

def get_user_balance(user_id):
    """Возвращает баланс пользователя"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 0

def get_referral_count(user_id):
    """Сколько пользователей пригласил"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def is_admin(user_id):
    """Проверяет, является ли пользователь админом"""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None