import sqlite3
from datetime import datetime

DB_NAME = "ads_bot.db"

def init_db():
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
            balance INTEGER DEFAULT 0,
            game_score INTEGER DEFAULT 0,
            game_energy INTEGER DEFAULT 100
        )
    ''')
    
    # Таблица для админов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    # Добавляем админа (замените на свой ID)
    cur.execute('INSERT OR IGNORE INTO admins (user_id) VALUES (1475910449)')
    
    conn.commit()
    conn.close()

def add_user(user_id, username, referrer_id=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if not cur.fetchone():
        cur.execute('''
            INSERT INTO users (user_id, username, reg_date, referrer_id, balance, game_score, game_energy)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, username, datetime.now(), referrer_id, 0, 0, 100))
        if referrer_id:
            cur.execute('UPDATE users SET balance = balance + 50 WHERE user_id = ?', (referrer_id,))
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
    result = cur.fetchone()
    conn.close()
    return result is not None

def get_game_data(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('SELECT game_score, game_energy FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    return {'score': result[0], 'energy': result[1]} if result else {'score': 0, 'energy': 100}

def update_game_data(user_id, score_change, energy_change):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('UPDATE users SET game_score = game_score + ?, game_energy = game_energy + ? WHERE user_id = ?', (score_change, energy_change, user_id))
    conn.commit()
    conn.close()