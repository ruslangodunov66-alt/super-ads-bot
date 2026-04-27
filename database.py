import sqlite3
from datetime import datetime

DB_NAME = "ads_bot.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # Объявления
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
    
    # Пользователи (расширенная таблица)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            reg_date TIMESTAMP,
            referrer_id INTEGER,
            balance INTEGER DEFAULT 0,
            free_ads INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            product TEXT DEFAULT 'смартфон',
            demand TEXT DEFAULT 'средний',
            price INTEGER DEFAULT 100
        )
    ''')
    
    # Админы
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    cur.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (1475910449)')
    conn.commit()
    conn.close()

def add_user(user_id, username, referrer_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if not cur.fetchone():
        # новому пользователю: 0 бесплатных выкладок
        cur.execute('''
            INSERT INTO users (user_id, username, reg_date, referrer_id, balance, free_ads, level, xp, product, demand, price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, datetime.now(), referrer_id, 0, 0, 1, 0, 'смартфон', 'средний', 100))
        
        # реферер получает +1 бесплатную выкладку и +5✨ (бонус в игре)
        if referrer_id:
            cur.execute('UPDATE users SET free_ads = free_ads + 1 WHERE user_id = ?', (referrer_id,))
            cur.execute('UPDATE users SET balance = balance + 5 WHERE user_id = ?', (referrer_id,))
    conn.commit()
    conn.close()

def add_ad(user_id, username, photo_id, description):
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
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT id, user_id, username, photo_id, description FROM ads WHERE status = "pending" ORDER BY created_at')
    ads = cur.fetchall()
    conn.close()
    return ads

def get_ad_by_id(ad_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id, username, photo_id, description FROM ads WHERE id = ?', (ad_id,))
    result = cur.fetchone()
    conn.close()
    if result:
        return {'user_id': result[0], 'username': result[1], 'photo_id': result[2], 'description': result[3]}
    return None

def update_ad_status(ad_id, status):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE ads SET status = ? WHERE id = ?', (status, ad_id))
    conn.commit()
    conn.close()

def get_user_balance(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 0

def update_user_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_free_ads(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT free_ads FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 0

def use_free_ad(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET free_ads = free_ads - 1 WHERE user_id = ? AND free_ads > 0', (user_id,))
    conn.commit()
    conn.close()

def get_referral_count(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM users WHERE referrer_id = ?', (user_id,))
    count = cur.fetchone()[0]
    conn.close()
    return count

def is_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,))
    return cur.fetchone() is not None

def get_game_state(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT level, xp, product, demand, price FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return {
        'level': result[0],
        'xp': result[1],
        'product': result[2],
        'demand': result[3],
        'price': result[4]
    } if result else {}

def update_game_state(user_id, new_level, new_xp):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET level = ?, xp = ? WHERE user_id = ?', (new_level, new_xp, user_id))
    conn.commit()
    conn.close()

def set_product(user_id, product):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET product = ? WHERE user_id = ?', (product, user_id))
    conn.commit()
    conn.close()

def set_demand_price(user_id, demand, price):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET demand = ?, price = ? WHERE user_id = ?', (demand, price, user_id))
    conn.commit()
    conn.close()