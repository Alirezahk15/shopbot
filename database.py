import sqlite3
import json
from contextlib import contextmanager

DB = "shop.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB, timeout=10)  # 10s timeout for lock contention
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # WAL mode for concurrent access
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, lang TEXT DEFAULT NULL,
            balance REAL DEFAULT 0, referrer INTEGER DEFAULT NULL,
            ref_earnings REAL DEFAULT 0, blocked INTEGER DEFAULT 0,
            joined_at TEXT DEFAULT CURRENT_TIMESTAMP, account_age INTEGER DEFAULT 0,
            note TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE);
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER,
            name TEXT, price REAL, description TEXT, banner_url TEXT,
            features TEXT DEFAULT '', has_warranty INTEGER DEFAULT 0,
            sold INTEGER DEFAULT 0, active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER,
            content TEXT, is_sold INTEGER DEFAULT 0, warranty INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            product_id INTEGER, price REAL, delivered_content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP, quantity INTEGER DEFAULT 1,
            warranty TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            tx_hash TEXT UNIQUE, amount REAL, method TEXT DEFAULT 'usdt',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS discounts (
            code TEXT PRIMARY KEY, percent INTEGER,
            max_uses INTEGER, used INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1,
            expires_at TEXT DEFAULT NULL,
            product_ids TEXT DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS discount_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT, user_id INTEGER,
            order_id INTEGER DEFAULT NULL,
            used_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS card_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            amount REAL, status TEXT DEFAULT 'pending',
            receipt_file_id TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS locked_channels (
            channel_id INTEGER PRIMARY KEY, title TEXT, locked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            invite_link TEXT DEFAULT '',
            custom_message TEXT DEFAULT '',
            expires_at TEXT DEFAULT NULL);
        CREATE TABLE IF NOT EXISTS locked_groups (
            group_id INTEGER PRIMARY KEY, title TEXT, locked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            invite_link TEXT DEFAULT '',
            custom_message TEXT DEFAULT '',
            expires_at TEXT DEFAULT NULL);
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS broadcast_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT, media_type TEXT DEFAULT 'text',
            media_url TEXT DEFAULT '',
            target_filter TEXT DEFAULT 'all',
            button_text TEXT DEFAULT '',
            button_url TEXT DEFAULT '',
            scheduled_at TEXT DEFAULT NULL,
            sent_at TEXT DEFAULT NULL,
            user_count INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS broadcast_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, message TEXT,
            media_type TEXT DEFAULT 'text',
            media_url TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY, is_super INTEGER DEFAULT 0,
            permissions TEXT DEFAULT 'all', added_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT DEFAULT NULL, notify_prefs TEXT DEFAULT 'all');
        CREATE TABLE IF NOT EXISTS panel_sessions (
    sid TEXT PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    ip TEXT,
    user_agent TEXT,
    created_at TEXT,
    status TEXT DEFAULT 'active');

CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER,
            action TEXT, detail TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS payment_methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
            details TEXT, active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            min_amount REAL DEFAULT 0,
            max_amount REAL DEFAULT 0,
            guide_message TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS payment_method_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method_id INTEGER, action TEXT, detail TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            subject TEXT, message TEXT, status TEXT DEFAULT 'open',
            admin_reply TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            replied_at TEXT DEFAULT '',
            priority TEXT DEFAULT 'normal',
            tags TEXT DEFAULT '',
            internal_note TEXT DEFAULT '',
            assigned_to INTEGER DEFAULT NULL);
        CREATE TABLE IF NOT EXISTS ticket_quick_replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS warranty_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
            order_id INTEGER, reason TEXT, status TEXT DEFAULT 'pending',
            admin_note TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """)
        # جداول تکمیلی: قبل از _migrate ساخته شوند تا ایندکس‌هایشان در نصب تازه هم ساخته شود
        _ensure_extra_tables(db)
        # migrate: add columns that may not exist in older DBs
        _migrate(db)

def _migrate(db):
    cols = {
        "users": ["note TEXT DEFAULT ''", "account_age INTEGER DEFAULT 0", "vip INTEGER DEFAULT 0"],
        "products": ["features TEXT DEFAULT ''", "has_warranty INTEGER DEFAULT 0", "banner_url TEXT",
                     "duration_days INTEGER DEFAULT 0"],
        "card_payments": ["receipt_file_id TEXT DEFAULT ''", "reject_reason TEXT DEFAULT ''"],
        "orders": ["warranty TEXT DEFAULT ''", "expires_at TEXT DEFAULT NULL",
                   "renew_notified INTEGER DEFAULT 0"],
        "admins": [
            "expires_at TEXT DEFAULT NULL",
            "notify_prefs TEXT DEFAULT 'all'",
            "panel_username TEXT DEFAULT NULL",
            "panel_password_hash TEXT DEFAULT NULL",
            "totp_secret TEXT DEFAULT ''",
            "totp_pending_secret TEXT DEFAULT ''",
            "totp_enabled INTEGER DEFAULT 0",
            "reset_code_hash TEXT DEFAULT ''",
            "reset_code_expires TEXT DEFAULT ''",
        ],
        "discounts": [
            "active INTEGER DEFAULT 1",
            "expires_at TEXT DEFAULT NULL",
            "product_ids TEXT DEFAULT NULL",
        ],
        "payment_methods": [
            "display_order INTEGER DEFAULT 0",
            "min_amount REAL DEFAULT 0",
            "max_amount REAL DEFAULT 0",
            "guide_message TEXT DEFAULT ''",
        ],
        "tickets": [
            "priority TEXT DEFAULT 'normal'",
            "tags TEXT DEFAULT ''",
            "internal_note TEXT DEFAULT ''",
            "assigned_to INTEGER DEFAULT NULL",
            "escalated INTEGER DEFAULT 0",
        ],
        "locked_channels": [
            "invite_link TEXT DEFAULT ''",
            "custom_message TEXT DEFAULT ''",
            "expires_at TEXT DEFAULT NULL",
        ],
        "locked_groups": [
            "invite_link TEXT DEFAULT ''",
            "custom_message TEXT DEFAULT ''",
            "expires_at TEXT DEFAULT NULL",
        ],
    }
    for table, new_cols in cols.items():
        existing = [r[1] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
        for col_def in new_cols:
            col_name = col_def.split()[0]
            if col_name not in existing:
                try:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
                except Exception:
                    pass
    # ── جداول نسخه ۲: قیف فروش، FAQ، امتیازدهی ──
    db.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, event TEXT,
        meta TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    db.execute("""CREATE TABLE IF NOT EXISTS faq (
        id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT,
        keywords TEXT DEFAULT '', lang TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    db.execute("""CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_id INTEGER,
        order_id INTEGER UNIQUE, stars INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    # ── ایندکس‌های کارایی ──
    for idx in (
        "CREATE INDEX IF NOT EXISTS idx_stock_prod_sold ON stock(product_id, is_sold)",
        "CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_product ON orders(product_id, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)",
        "CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer)",
        "CREATE INDEX IF NOT EXISTS idx_events_event ON events(event, created_at)",
        # ── اصلاح: ایندکس مفقود روی ref_earnings_log برای کوئری ref_earned_today ──
        "CREATE INDEX IF NOT EXISTS idx_ref_earnings_user_day ON ref_earnings_log(user_id, day)",
    ):
        try:
            db.execute(idx)
        except Exception:
            pass

    # ── v3: شخصی‌سازی ──
    db.execute("""CREATE TABLE IF NOT EXISTS text_overrides (
        key TEXT, lang TEXT, text TEXT,
        PRIMARY KEY (key, lang))""")
    db.execute("""CREATE TABLE IF NOT EXISTS custom_buttons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        type TEXT DEFAULT 'text',
        content TEXT DEFAULT '',
        parent_id INTEGER,
        position INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1)""")
    try:
        db.execute("ALTER TABLE categories ADD COLUMN image TEXT DEFAULT ''")
    except Exception:
        pass

# ──────────────── کاربران ────────────────
def add_user(uid, username="", referrer=None):
    with get_db() as db:
        exists = db.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone()
        if not exists:
            db.execute("INSERT INTO users (user_id, username, referrer) VALUES (?,?,?)",
                       (uid, username, referrer))
        else:
            db.execute("UPDATE users SET username=? WHERE user_id=?", (username, uid))

def get_user(uid):
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()

def get_user_by_username(username):
    with get_db() as db:
        uname = username.lstrip("@")
        return db.execute("SELECT * FROM users WHERE username=?", (uname,)).fetchone()

def update_user_account_age(uid, days):
    with get_db() as db:
        db.execute("UPDATE users SET account_age=? WHERE user_id=?", (days, uid))

def set_lang(uid, lang):
    with get_db() as db:
        db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, uid))

def get_user_lang(user_id):
    with get_db() as db:
        row = db.execute("SELECT lang FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row["lang"] if row else None

def add_balance(uid, amount, ref_earning=False):
    with get_db() as db:
        db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, uid))
        if ref_earning:
            db.execute("UPDATE users SET ref_earnings=ref_earnings+? WHERE user_id=?", (amount, uid))

def set_blocked(uid, val):
    with get_db() as db:
        db.execute("UPDATE users SET blocked=? WHERE user_id=?", (val, uid))

def is_vip(uid):
    with get_db() as db:
        row = db.execute("SELECT vip FROM users WHERE user_id=?", (uid,)).fetchone()
        return bool(row["vip"]) if row else False

def set_vip(uid, val):
    with get_db() as db:
        db.execute("UPDATE users SET vip=? WHERE user_id=?", (val, uid))

def count_orders_today(uid):
    """تعداد خریدهای امروز کاربر (برای محدودیت خرید روزانه)"""
    with get_db() as db:
        row = db.execute(
            "SELECT COUNT(*) c FROM orders WHERE user_id=? AND date(created_at)=date('now')",
            (uid,)).fetchone()
        return row["c"] if row else 0

def set_user_note(uid, note):
    with get_db() as db:
        db.execute("UPDATE users SET note=? WHERE user_id=?", (note, uid))

def all_users():
    with get_db() as db:
        return db.execute("SELECT user_id, lang FROM users WHERE blocked=0").fetchall()

def search_users(query):
    with get_db() as db:
        try:
            uid = int(query)
            return db.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchall()
        except ValueError:
            return db.execute("SELECT * FROM users WHERE username LIKE ?",
                              (f"%{query.lstrip('@')}%",)).fetchall()

def ref_count(uid):
    with get_db() as db:
        return db.execute("SELECT COUNT(*) c FROM users WHERE referrer=?", (uid,)).fetchone()["c"]

def get_user_stats(user_id):
    with get_db() as db:
        return db.execute("""
            SELECT u.*,
                   COUNT(DISTINCT o.id) as total_orders,
                   COALESCE(SUM(o.price), 0) as total_spent,
                   (SELECT COUNT(*) FROM users WHERE referrer=u.user_id) as ref_total
            FROM users u
            LEFT JOIN orders o ON u.user_id = o.user_id
            WHERE u.user_id = ?
            GROUP BY u.user_id
        """, (user_id,)).fetchone()

def get_all_users_paginated(offset=0, limit=20):
    with get_db() as db:
        return db.execute(
            "SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?",
            (limit, offset)).fetchall()

def count_users():
    with get_db() as db:
        return db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]

# ──────────────── دسته و محصول ────────────────
def add_category(name):
    with get_db() as db:
        db.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))

def get_categories():
    with get_db() as db:
        return db.execute("SELECT * FROM categories").fetchall()

def delete_category(cid):
    with get_db() as db:
        db.execute("DELETE FROM stock WHERE product_id IN (SELECT id FROM products WHERE category_id=?)", (cid,))
        db.execute("DELETE FROM products WHERE category_id=?", (cid,))
        db.execute("DELETE FROM categories WHERE id=?", (cid,))

def add_product(cid, name, price, desc, features="", has_warranty=0):
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO products (category_id,name,price,description,features,has_warranty) VALUES (?,?,?,?,?,?)",
            (cid, name, price, desc, features, has_warranty))
        return cur.lastrowid

def get_products(cid, only_active=True):
    with get_db() as db:
        q = "SELECT * FROM products WHERE category_id=?" + (" AND active=1" if only_active else "")
        return db.execute(q, (cid,)).fetchall()

def get_all_products():
    with get_db() as db:
        return db.execute("SELECT * FROM products").fetchall()

def get_product(pid):
    with get_db() as db:
        return db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()

def delete_product(pid):
    with get_db() as db:
        db.execute("DELETE FROM products WHERE id=?", (pid,))
        db.execute("DELETE FROM stock WHERE product_id=?", (pid,))

def update_price(pid, price):
    with get_db() as db:
        db.execute("UPDATE products SET price=? WHERE id=?", (price, pid))

_ALLOWED_PRODUCT_COLS = {"name", "price", "description", "features",
                         "has_warranty", "banner_url", "active", "sold"}

def update_product(pid, **kwargs):
    invalid = set(kwargs) - _ALLOWED_PRODUCT_COLS
    if invalid:
        raise ValueError(f"update_product: invalid column(s): {invalid}")
    with get_db() as db:
        sets = ", ".join(f"{k}=?" for k in kwargs)
        db.execute(f"UPDATE products SET {sets} WHERE id=?", (*kwargs.values(), pid))

def toggle_product_active(pid):
    with get_db() as db:
        db.execute("UPDATE products SET active=1-active WHERE id=?", (pid,))
        row = db.execute("SELECT active FROM products WHERE id=?", (pid,)).fetchone()
        return row["active"]

# ──────────────── موجودی ────────────────
def add_stock(pid, items):
    with get_db() as db:
        for c in items:
            if c.strip():
                db.execute("INSERT INTO stock (product_id, content) VALUES (?,?)", (pid, c.strip()))

def stock_count(pid):
    with get_db() as db:
        return db.execute("SELECT COUNT(*) c FROM stock WHERE product_id=? AND is_sold=0",
                          (pid,)).fetchone()["c"]

# ──────────────── خرید اتمیک (چندتایی) ────────────────
def purchase(uid, product, final_price, qty=1):
    """خرید چند محصول به‌صورت اتمیک. برمی‌گردونه لیست محتواها یا کد خطا."""
    with get_db() as db:
        u = db.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        total = round(final_price * qty, 2)
        if u["balance"] < total:
            return "NO_BALANCE"
        items = db.execute(
            "SELECT * FROM stock WHERE product_id=? AND is_sold=0 LIMIT ?",
            (product["id"], qty)).fetchall()
        if len(items) < qty:
            return "NO_STOCK"
        contents = []
        for item in items:
            db.execute("UPDATE stock SET is_sold=1 WHERE id=?", (item["id"],))
            contents.append(item["content"])
        db.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (total, uid))
        db.execute("UPDATE products SET sold=sold+? WHERE id=?", (qty, product["id"]))
        warranty_val = "yes" if product["has_warranty"] else ""
        db.execute(
            "INSERT INTO orders (user_id,product_id,price,delivered_content,quantity,warranty) VALUES (?,?,?,?,?,?)",
            (uid, product["id"], total, "\n".join(contents), qty, warranty_val))
        return contents

def get_orders(uid, limit=10):
    with get_db() as db:
        return db.execute(
            "SELECT o.*, COALESCE(p.name, '(deleted)') as name, "
            "COALESCE(p.has_warranty, 0) as has_warranty FROM orders o "
            "LEFT JOIN products p ON o.product_id=p.id "
            "WHERE o.user_id=? ORDER BY o.id DESC LIMIT ?", (uid, limit)).fetchall()

def get_order(oid):
    with get_db() as db:
        return db.execute(
            "SELECT o.*, COALESCE(p.name, '(deleted)') as name, "
            "COALESCE(p.has_warranty, 0) as has_warranty FROM orders o "
            "LEFT JOIN products p ON o.product_id=p.id WHERE o.id=?", (oid,)).fetchone()

# ──────────────── تراکنش USDT ────────────────
def tx_exists(h):
    with get_db() as db:
        return db.execute("SELECT 1 FROM transactions WHERE tx_hash=?", (h,)).fetchone() is not None

def save_tx(uid, h, amount, method="usdt"):
    with get_db() as db:
        db.execute("INSERT INTO transactions (user_id,tx_hash,amount,method) VALUES (?,?,?,?)",
                   (uid, h, amount, method))
        db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, uid))

# ──────────────── کد تخفیف ────────────────
def add_discount(code, percent, max_uses):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO discounts (code,percent,max_uses,used) VALUES (?,?,?,0)",
                   (code.upper(), percent, max_uses))

def get_discount(code, product_id=None):
    """کد تخفیف معتبر: سقف مصرف، فعال بودن، انقضا و محدودیت محصول بررسی میشود"""
    from datetime import date
    with get_db() as db:
        d = db.execute("SELECT * FROM discounts WHERE code=?", (code.upper(),)).fetchone()
        if not d or d["used"] >= d["max_uses"]:
            return None
        keys = d.keys()
        if "active" in keys and d["active"] in (0, "0"):
            return None
        if "expires_at" in keys and d["expires_at"]:
            if str(d["expires_at"])[:10] < date.today().isoformat():
                return None
        if product_id is not None and "product_ids" in keys and d["product_ids"]:
            allowed = {p.strip() for p in str(d["product_ids"]).split(",") if p.strip()}
            if allowed and str(product_id) not in allowed:
                return None
        return d

def use_discount(code, user_id=None, order_id=None):
    with get_db() as db:
        db.execute("UPDATE discounts SET used=used+1 WHERE code=?", (code.upper(),))
        # Record usage history
        try:
            db.execute(
                "INSERT INTO discount_usage (code, user_id, order_id) VALUES (?,?,?)",
                (code.upper(), user_id, order_id)
            )
        except Exception:
            pass  # discount_usage table may not exist in older DBs

def all_discounts():
    with get_db() as db:
        return db.execute("SELECT * FROM discounts").fetchall()

def delete_discount(code):
    with get_db() as db:
        db.execute("DELETE FROM discounts WHERE code=?", (code,))

# ──────────────── کارت به کارت ────────────────
def create_card_payment(uid, amount, file_id=""):
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO card_payments (user_id,amount,receipt_file_id) VALUES (?,?,?)",
            (uid, amount, file_id))
        return cur.lastrowid

def get_card_payment(pay_id):
    with get_db() as db:
        return db.execute("SELECT * FROM card_payments WHERE id=?", (pay_id,)).fetchone()

def set_card_status(pay_id, status):
    with get_db() as db:
        db.execute("UPDATE card_payments SET status=? WHERE id=?", (status, pay_id))
        return db.execute("SELECT * FROM card_payments WHERE id=?", (pay_id,)).fetchone()

def get_pending_card_payments():
    with get_db() as db:
        return db.execute(
            "SELECT cp.*, u.username FROM card_payments cp "
            "JOIN users u ON cp.user_id=u.user_id "
            "WHERE cp.status='pending' ORDER BY cp.id DESC").fetchall()

# ──────────────── قفل کانال/گروه ────────────────
def locked_channel_exists(channel_id):
    with get_db() as db:
        return db.execute("SELECT 1 FROM locked_channels WHERE channel_id=?",
                          (channel_id,)).fetchone() is not None

def lock_channel(channel_id, title):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO locked_channels (channel_id, title) VALUES (?,?)",
                   (channel_id, title))

def unlock_channel(channel_id):
    with get_db() as db:
        db.execute("DELETE FROM locked_channels WHERE channel_id=?", (channel_id,))

def get_locked_channels():
    with get_db() as db:
        return db.execute("SELECT * FROM locked_channels").fetchall()

def locked_group_exists(group_id):
    with get_db() as db:
        return db.execute("SELECT 1 FROM locked_groups WHERE group_id=?",
                          (group_id,)).fetchone() is not None

def lock_group(group_id, title):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO locked_groups (group_id, title) VALUES (?,?)",
                   (group_id, title))

def unlock_group(group_id):
    with get_db() as db:
        db.execute("DELETE FROM locked_groups WHERE group_id=?", (group_id,))

def get_locked_groups():
    with get_db() as db:
        return db.execute("SELECT * FROM locked_groups").fetchall()

# ──────────────── تنظیمات ────────────────
def get_broadcast_target_users(target_filter):
    """گرفتن لیست آیدی کاربران هدف بر اساس فیلتر (هماهنگ با پنل تحت وب)"""
    with get_db() as conn:
        if target_filter == "fa":
            rows = conn.execute("SELECT user_id FROM users WHERE blocked=0 AND lang='fa'").fetchall()
        elif target_filter == "en":
            rows = conn.execute("SELECT user_id FROM users WHERE blocked=0 AND lang='en'").fetchall()
        elif target_filter == "has_balance":
            rows = conn.execute("SELECT user_id FROM users WHERE blocked=0 AND balance > 0").fetchall()
        elif target_filter == "has_orders":
            rows = conn.execute(
                "SELECT DISTINCT u.user_id FROM users u "
                "JOIN orders o ON u.user_id=o.user_id WHERE u.blocked=0"
            ).fetchall()
        else:
            rows = conn.execute("SELECT user_id FROM users WHERE blocked=0").fetchall()
        return [r["user_id"] for r in rows]


def get_pending_panel_broadcast():
    """خواندن پیام همگانی فوری که از پنل تحت وب در صف قرار گرفته است"""
    raw = get_setting("pending_broadcast_v2", "")
    bid = get_setting("pending_broadcast_id", "")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    data["id"] = bid
    return data


def clear_pending_panel_broadcast():
    """پاک کردن پیام همگانی فوری بعد از ارسال"""
    set_setting("pending_broadcast_v2", "")
    set_setting("pending_broadcast_id", "")


def get_due_scheduled_broadcasts():
    """پیام‌های همگانی زمان‌بندی‌شده‌ای که موعد ارسالشان رسیده است"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM broadcast_history WHERE status='pending' AND scheduled_at IS NOT NULL "
            "AND datetime(scheduled_at) <= datetime('now')"
        ).fetchall()
        return [dict(r) for r in rows]


def mark_broadcast_sent(bid, success_count):
    """علامت زدن پیام همگانی به عنوان ارسال‌شده به همراه تعداد ارسال موفق"""
    if not bid:
        return
    with get_db() as conn:
        conn.execute(
            "UPDATE broadcast_history SET status='sent', success_count=?, sent_at=CURRENT_TIMESTAMP WHERE id=?",
            (success_count, bid)
        )


def set_setting(key, value):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))

def get_setting(key, default=None):
    with get_db() as db:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

def get_pending_dms():
    """پیام‌های مستقیمی که از پنل تحت وب برای ارسال به کاربران در صف قرار گرفته‌اند"""
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM settings WHERE key LIKE 'pending_dm_%'").fetchall()
        return [dict(r) for r in rows]

def delete_setting(key):
    with get_db() as conn:
        conn.execute("DELETE FROM settings WHERE key=?", (key,))

def get_all_settings():
    with get_db() as db:
        return {row["key"]: row["value"] for row in db.execute("SELECT * FROM settings").fetchall()}

# ──────────────── ادمین ────────────────
def add_admin(user_id, is_super=0, permissions="all"):
    with get_db() as db:
        db.execute("INSERT INTO admins (user_id, is_super, permissions) VALUES (?,?,?) "
                   "ON CONFLICT(user_id) DO UPDATE SET is_super=excluded.is_super, permissions=excluded.permissions",
                   (user_id, is_super, permissions))

def get_admin(user_id):
    with get_db() as db:
        return db.execute("SELECT * FROM admins WHERE user_id=?", (user_id,)).fetchone()

def is_admin_user(user_id):
    with get_db() as db:
        return db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone() is not None

_ALLOWED_ADMIN_COLS = {"is_super", "permissions"}

def update_admin(user_id, **kwargs):
    invalid = set(kwargs) - _ALLOWED_ADMIN_COLS
    if invalid:
        raise ValueError(f"update_admin: invalid column(s): {invalid}")
    with get_db() as db:
        updates = ", ".join([f"{k}=?" for k in kwargs])
        params = list(kwargs.values()) + [user_id]
        db.execute(f"UPDATE admins SET {updates} WHERE user_id=?", params)

def delete_admin(user_id):
    with get_db() as db:
        db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))

def get_all_admins():
    with get_db() as db:
        return db.execute("SELECT * FROM admins").fetchall()

def admin_has_perm(user_id, perm):
    """بررسی اینکه ادمین دسترسی خاصی داره. super admin همیشه True."""
    adm = get_admin(user_id)
    if not adm:
        return False
    if adm["is_super"] == 1 or adm["permissions"] == "all":
        return True
    perms = adm["permissions"].split(",") if adm["permissions"] else []
    return perm in perms

# ──────────────── متدهای پرداخت ────────────────
def add_payment_method(name, details):
    with get_db() as db:
        db.execute("INSERT OR IGNORE INTO payment_methods (name, details) VALUES (?,?)",
                   (name, details))

def get_payment_methods(only_active=True):
    with get_db() as db:
        q = "SELECT * FROM payment_methods" + (" WHERE active=1" if only_active else "")
        return db.execute(q).fetchall()

def get_payment_method(method_id):
    with get_db() as db:
        return db.execute("SELECT * FROM payment_methods WHERE id=?", (method_id,)).fetchone()

_ALLOWED_PAYMENT_METHOD_COLS = {"name", "details", "active"}

def update_payment_method(method_id, **kwargs):
    invalid = set(kwargs) - _ALLOWED_PAYMENT_METHOD_COLS
    if invalid:
        raise ValueError(f"update_payment_method: invalid column(s): {invalid}")
    with get_db() as db:
        updates = ", ".join([f"{k}=?" for k in kwargs])
        params = list(kwargs.values()) + [method_id]
        db.execute(f"UPDATE payment_methods SET {updates} WHERE id=?", params)

def delete_payment_method(method_id):
    with get_db() as db:
        db.execute("DELETE FROM payment_methods WHERE id=?", (method_id,))

# ──────────────── تیکت‌های پشتیبانی ────────────────
def create_ticket(user_id, subject, message):
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO tickets (user_id,subject,message) VALUES (?,?,?)",
            (user_id, subject, message))
        return cur.lastrowid

def get_tickets(user_id=None, status=None):
    with get_db() as db:
        q = "SELECT t.*, u.username FROM tickets t JOIN users u ON t.user_id=u.user_id WHERE 1=1"
        params = []
        if user_id:
            q += " AND t.user_id=?"
            params.append(user_id)
        if status:
            q += " AND t.status=?"
            params.append(status)
        q += " ORDER BY t.id DESC"
        return db.execute(q, params).fetchall()

def get_ticket(tid):
    with get_db() as db:
        return db.execute(
            "SELECT t.*, u.username FROM tickets t JOIN users u ON t.user_id=u.user_id WHERE t.id=?",
            (tid,)).fetchone()

def reply_ticket(tid, reply):
    with get_db() as db:
        db.execute(
            "UPDATE tickets SET admin_reply=?, status='answered', replied_at=CURRENT_TIMESTAMP WHERE id=?",
            (reply, tid))
        return db.execute("SELECT * FROM tickets WHERE id=?", (tid,)).fetchone()

def close_ticket(tid):
    with get_db() as db:
        db.execute("UPDATE tickets SET status='closed' WHERE id=?", (tid,))

# ──────────────── درخواست گارانتی ───���────────────
def create_warranty_claim(user_id, order_id, reason):
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO warranty_claims (user_id,order_id,reason) VALUES (?,?,?)",
            (user_id, order_id, reason))
        return cur.lastrowid

def get_warranty_claims(status=None):
    with get_db() as db:
        q = ("SELECT wc.*, u.username, o.price as order_price, p.name as product_name "
             "FROM warranty_claims wc "
             "JOIN users u ON wc.user_id=u.user_id "
             "JOIN orders o ON wc.order_id=o.id "
             "JOIN products p ON o.product_id=p.id WHERE 1=1")
        params = []
        if status:
            q += " AND wc.status=?"
            params.append(status)
        q += " ORDER BY wc.id DESC"
        return db.execute(q, params).fetchall()

def update_warranty_claim(claim_id, status, note=""):
    with get_db() as db:
        db.execute("UPDATE warranty_claims SET status=?, admin_note=? WHERE id=?",
                   (status, note, claim_id))

# ──────────────── آمار ────────────────
def get_stats():
    with get_db() as db:
        return {
            "users": db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
            "orders": db.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"],
            "revenue": db.execute("SELECT COALESCE(SUM(price),0) s FROM orders").fetchone()["s"],
            "deposits": db.execute("SELECT COALESCE(SUM(amount),0) s FROM transactions").fetchone()["s"],
            "today_orders": db.execute(
                "SELECT COUNT(*) c FROM orders WHERE date(created_at)=date('now')").fetchone()["c"],
            "today_revenue": db.execute(
                "SELECT COALESCE(SUM(price),0) s FROM orders WHERE date(created_at)=date('now')").fetchone()["s"],
            "pending_tickets": db.execute(
                "SELECT COUNT(*) c FROM tickets WHERE status='open'").fetchone()["c"],
            "pending_cards": db.execute(
                "SELECT COUNT(*) c FROM card_payments WHERE status='pending'").fetchone()["c"],
            "pending_warranty": db.execute(
                "SELECT COUNT(*) c FROM warranty_claims WHERE status='pending'").fetchone()["c"],
            "blocked_users": db.execute(
                "SELECT COUNT(*) c FROM users WHERE blocked=1").fetchone()["c"],
        }

# ──────── Panel sessions (نشست‌های ورود به پنل) ────────
def create_panel_session(sid, user_id, username, ip, user_agent):
    import datetime as _dt
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO panel_sessions (sid, user_id, username, ip, user_agent, created_at, status) "
            "VALUES (?, ?, ?, ?, ?, ?, 'active')",
            (sid, user_id, username, ip, user_agent,
             _dt.datetime.now(_dt.timezone.utc).isoformat()))


def get_panel_session(sid):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM panel_sessions WHERE sid = ?", (sid,)).fetchone()
        return dict(row) if row else None


def set_panel_session_status(sid, status):
    with get_db() as conn:
        conn.execute("UPDATE panel_sessions SET status = ? WHERE sid = ?", (status, sid))


# ═══════════ جداول جدید: دستور سفارشی، پیام زمان‌بندی، لاگ رفرال، زرین‌پال ═══════════
def _ensure_extra_tables(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS custom_commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trigger TEXT UNIQUE, response TEXT,
        created_at TEXT DEFAULT (datetime('now')))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS scheduled_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT, send_time TEXT, enabled INTEGER DEFAULT 1,
        last_sent TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')))""")
    conn.execute("""CREATE TABLE IF NOT EXISTS ref_earnings_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, amount REAL, day TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS zarinpal_pending (
        authority TEXT PRIMARY KEY,
        user_id INTEGER, amount_rial INTEGER, amount_usd REAL,
        created_at TEXT DEFAULT (datetime('now')))""")


def get_custom_commands():
    with get_db() as conn:
        _ensure_extra_tables(conn)
        return [dict(r) for r in conn.execute(
            "SELECT * FROM custom_commands ORDER BY id DESC").fetchall()]


def add_custom_command(trigger, response):
    with get_db() as conn:
        _ensure_extra_tables(conn)
        conn.execute("INSERT OR REPLACE INTO custom_commands (trigger, response) VALUES (?,?)",
                     (trigger, response))


def delete_custom_command(cmd_id):
    with get_db() as conn:
        _ensure_extra_tables(conn)
        conn.execute("DELETE FROM custom_commands WHERE id=?", (cmd_id,))


def get_scheduled_messages():
    with get_db() as conn:
        _ensure_extra_tables(conn)
        return [dict(r) for r in conn.execute(
            "SELECT * FROM scheduled_messages ORDER BY send_time").fetchall()]


def add_scheduled_message(text, send_time):
    with get_db() as conn:
        _ensure_extra_tables(conn)
        conn.execute("INSERT INTO scheduled_messages (text, send_time) VALUES (?,?)",
                     (text, send_time))


def delete_scheduled_message(msg_id):
    with get_db() as conn:
        _ensure_extra_tables(conn)
        conn.execute("DELETE FROM scheduled_messages WHERE id=?", (msg_id,))


def mark_scheduled_sent(msg_id, day):
    with get_db() as conn:
        conn.execute("UPDATE scheduled_messages SET last_sent=? WHERE id=?", (day, msg_id))


def log_ref_earning(user_id, amount):
    with get_db() as conn:
        _ensure_extra_tables(conn)
        conn.execute("INSERT INTO ref_earnings_log (user_id, amount, day) VALUES (?,?,date('now'))",
                     (user_id, amount))


def ref_earned_today(user_id):
    with get_db() as conn:
        _ensure_extra_tables(conn)
        row = conn.execute(
            "SELECT COALESCE(SUM(amount),0) s FROM ref_earnings_log WHERE user_id=? AND day=date('now')",
            (user_id,)).fetchone()
        return float(row["s"] or 0)


def add_zp_pending(authority, user_id, amount_rial, amount_usd):
    with get_db() as conn:
        _ensure_extra_tables(conn)
        conn.execute(
            "INSERT OR REPLACE INTO zarinpal_pending (authority, user_id, amount_rial, amount_usd) VALUES (?,?,?,?)",
            (authority, user_id, amount_rial, amount_usd))


def pop_zp_pending(authority):
    with get_db() as conn:
        _ensure_extra_tables(conn)
        row = conn.execute("SELECT * FROM zarinpal_pending WHERE authority=?", (authority,)).fetchone()
        if row:
            conn.execute("DELETE FROM zarinpal_pending WHERE authority=?", (authority,))
            return dict(row)
        return None


# ──────────────── رویدادها (قیف فروش) ────────────────
def log_event(uid, event, meta=""):
    """ثبت رویداد برای گزارش قیف فروش — هرگز خطا پرتاب نمی‌کند"""
    try:
        with get_db() as db:
            db.execute("INSERT INTO events (user_id, event, meta) VALUES (?,?,?)",
                       (uid, event, str(meta)[:200]))
    except Exception:
        pass

# ──────────────── سوالات متداول (FAQ) ────────────────
def get_faqs():
    with get_db() as db:
        return db.execute("SELECT * FROM faq ORDER BY id DESC").fetchall()

def add_faq(question, answer, keywords="", lang=""):
    with get_db() as db:
        cur = db.execute("INSERT INTO faq (question, answer, keywords, lang) VALUES (?,?,?,?)",
                         (question, answer, keywords, lang))
        return cur.lastrowid

def update_faq(fid, question, answer, keywords="", lang=""):
    with get_db() as db:
        db.execute("UPDATE faq SET question=?, answer=?, keywords=?, lang=? WHERE id=?",
                   (question, answer, keywords, lang, fid))

def delete_faq(fid):
    with get_db() as db:
        db.execute("DELETE FROM faq WHERE id=?", (fid,))

def match_faqs(text, lang=None, limit=3):
    """تطبیق ساده کلیدواژه‌ای متن کاربر با سوالات متداول"""
    text_l = (text or "").lower()
    scored = []
    for f in get_faqs():
        if lang and f["lang"] and f["lang"] != lang:
            continue
        kws = {k.strip().lower() for k in (f["keywords"] or "").split(",") if k.strip()}
        kws |= {w for w in (f["question"] or "").lower().split() if len(w) > 2}
        score = sum(1 for k in kws if k and k in text_l)
        if score:
            scored.append((score, f["id"], f))
    scored.sort(key=lambda x: (-x[0], -x[1]))
    return [f for _, _, f in scored[:limit]]

# ──────────────── امتیازدهی محصولات ────────────────
def add_rating(uid, pid, order_id, stars):
    stars = max(1, min(5, int(stars)))
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO ratings (user_id, product_id, order_id, stars) VALUES (?,?,?,?)",
                   (uid, pid, order_id, stars))

def get_product_rating(pid):
    """میانگین امتیاز و تعداد آرا"""
    with get_db() as db:
        r = db.execute("SELECT AVG(stars) a, COUNT(*) n FROM ratings WHERE product_id=?", (pid,)).fetchone()
        return (round(r["a"], 1) if r["a"] else 0, r["n"] or 0)

# ──────────────── اشتراک‌ها ────────────────
def set_last_orders_expiry(uid, qty, days):
    """ثبت تاریخ انقضا روی آخرین سفارش‌های کاربر (محصولات اشتراکی)"""
    with get_db() as db:
        db.execute(
            "UPDATE orders SET expires_at=date('now', ?) WHERE id IN "
            "(SELECT id FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?)",
            (f"+{int(days)} days", uid, int(qty)))

def get_expiring_orders(days=3):
    """سفارش‌های اشتراکی رو به انقضا که هنوز یادآوری نگرفته‌اند"""
    with get_db() as db:
        return db.execute(
            "SELECT o.id, o.user_id, o.product_id, COALESCE(p.name,'') name, "
            "MAX(CAST(julianday(o.expires_at) - julianday('now') AS INTEGER), 0) days_left "
            "FROM orders o LEFT JOIN products p ON o.product_id=p.id "
            "WHERE o.expires_at IS NOT NULL AND COALESCE(o.renew_notified,0)=0 "
            "AND date(o.expires_at) <= date('now', ?)",
            (f"+{int(days)} days",)).fetchall()

def mark_renew_notified(oid):
    with get_db() as db:
        db.execute("UPDATE orders SET renew_notified=1 WHERE id=?", (oid,))

# ──────────────── امنیت: رفرال ────────────────
def referrals_today(ref_id):
    """تعداد زیرمجموعه‌های امروز یک کاربر"""
    with get_db() as db:
        return db.execute(
            "SELECT COUNT(*) c FROM users WHERE referrer=? AND date(joined_at)=date('now')",
            (ref_id,)).fetchone()["c"]

# ──────── متن‌های سفارشی ربات (Text Overrides) ────────
def get_text_overrides():
    """همه متن‌های بازنویسی‌شده به صورت dict: key|lang -> text"""
    with get_db() as db:
        return {f"{r['key']}|{r['lang']}": r["text"]
                for r in db.execute("SELECT * FROM text_overrides").fetchall()}

def set_text_override(key, lang, text):
    with get_db() as db:
        db.execute("INSERT OR REPLACE INTO text_overrides (key, lang, text) VALUES (?,?,?)",
                   (key, lang, text))

def delete_text_override(key, lang):
    with get_db() as db:
        db.execute("DELETE FROM text_overrides WHERE key=? AND lang=?", (key, lang))

# ──────── منوساز (Custom Buttons) ────────
def get_custom_buttons(parent_id=None, active_only=True):
    """دکمه‌های سفارشی یک سطح (ریشه یا زیرمنو)"""
    q = "SELECT * FROM custom_buttons WHERE COALESCE(parent_id, 0)=?"
    args = [int(parent_id or 0)]
    if active_only:
        q += " AND active=1"
    q += " ORDER BY position, id"
    with get_db() as db:
        return db.execute(q, args).fetchall()

def get_all_custom_buttons():
    with get_db() as db:
        return db.execute("SELECT * FROM custom_buttons ORDER BY COALESCE(parent_id,0), position, id").fetchall()

def get_custom_button(bid):
    with get_db() as db:
        return db.execute("SELECT * FROM custom_buttons WHERE id=?", (bid,)).fetchone()

def add_custom_button(label, btype="text", content="", parent_id=None, position=0):
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO custom_buttons (label, type, content, parent_id, position) VALUES (?,?,?,?,?)",
            (label, btype, content, parent_id, position))
        return cur.lastrowid

def update_custom_button(bid, label, btype, content, parent_id, position, active):
    with get_db() as db:
        db.execute(
            "UPDATE custom_buttons SET label=?, type=?, content=?, parent_id=?, position=?, active=? WHERE id=?",
            (label, btype, content, parent_id, position, 1 if active else 0, bid))

def delete_custom_button(bid):
    """حذف دکمه و زیرمنوهای آن"""
    with get_db() as db:
        db.execute("DELETE FROM custom_buttons WHERE id=? OR parent_id=?", (bid, bid))

def set_category_image(cid, image):
    with get_db() as db:
        db.execute("UPDATE categories SET image=? WHERE id=?", (image or "", cid))
