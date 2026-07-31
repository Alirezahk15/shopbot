# -*- coding: utf-8 -*-
"""
اسکریپت مایگریشن دیتابیس
این فایل را یک بار در کنار shop.db اجرا کنید تا جداول جدید ساخته شوند.
python migrate_db.py
"""
import sqlite3, os, sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop.db")

if not os.path.exists(DB):
    print(f"[ERROR] shop.db پیدا نشد: {DB}")
    sys.exit(1)

conn = sqlite3.connect(DB, timeout=10)
conn.row_factory = sqlite3.Row

try:
    print("[1/6] جدول ratings ...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            order_id INTEGER UNIQUE,
            stars INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)
    """)

    print("[2/6] جدول events ...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            event TEXT,
            meta TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)
    """)

    print("[3/6] جدول faq ...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            answer TEXT,
            keywords TEXT DEFAULT '',
            lang TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP)
    """)

    print("[4/6] جدول text_overrides ...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS text_overrides (
            key TEXT, lang TEXT, text TEXT,
            PRIMARY KEY (key, lang))
    """)

    print("[5/6] جدول custom_buttons ...")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS custom_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            type TEXT DEFAULT 'text',
            content TEXT DEFAULT '',
            parent_id INTEGER,
            position INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1)
    """)

    print("[6/6] ستون‌های جدید ...")
    # categories.image
    try:
        conn.execute("ALTER TABLE categories ADD COLUMN image TEXT DEFAULT ''")
        print("      categories.image OK")
    except Exception:
        print("      categories.image already exists")

    # ستون‌های users
    for col in ["note TEXT DEFAULT ''", "account_age INTEGER DEFAULT 0", "vip INTEGER DEFAULT 0"]:
        try:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col}")
        except Exception:
            pass

    # ستون‌های products
    for col in ["features TEXT DEFAULT ''", "has_warranty INTEGER DEFAULT 0",
                "banner_url TEXT", "duration_days INTEGER DEFAULT 0"]:
        try:
            conn.execute(f"ALTER TABLE products ADD COLUMN {col}")
        except Exception:
            pass

    # ستون‌های orders
    for col in ["warranty TEXT DEFAULT ''", "expires_at TEXT DEFAULT NULL",
                "renew_notified INTEGER DEFAULT 0"]:
        try:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {col}")
        except Exception:
            pass

    # ستون‌های admins
    for col in ["expires_at TEXT DEFAULT NULL", "notify_prefs TEXT DEFAULT 'all'",
                "panel_username TEXT DEFAULT NULL", "panel_password_hash TEXT DEFAULT NULL",
                "totp_secret TEXT DEFAULT ''", "totp_pending_secret TEXT DEFAULT ''",
                "totp_enabled INTEGER DEFAULT 0", "reset_code_hash TEXT DEFAULT ''",
                "reset_code_expires TEXT DEFAULT ''"]:
        try:
            conn.execute(f"ALTER TABLE admins ADD COLUMN {col}")
        except Exception:
            pass

    # ستون tickets.escalated
    try:
        conn.execute("ALTER TABLE tickets ADD COLUMN escalated INTEGER DEFAULT 0")
    except Exception:
        pass

    # ایندکس‌ها
    for idx in (
        "CREATE INDEX IF NOT EXISTS idx_stock_prod_sold ON stock(product_id, is_sold)",
        "CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)",
        "CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer)",
        "CREATE INDEX IF NOT EXISTS idx_events_event ON events(event, created_at)",
    ):
        try:
            conn.execute(idx)
        except Exception:
            pass

    conn.commit()
    print("\n✅ مایگریشن با موفقیت انجام شد! ربات را restart کنید.")

except Exception as e:
    conn.rollback()
    print(f"\n[ERROR] {e}")
    sys.exit(1)
finally:
    conn.close()
