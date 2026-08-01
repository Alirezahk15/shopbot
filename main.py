import time, logging, asyncio, requests, json, random, os
from datetime import datetime, timezone
from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup,
                      ReplyKeyboardMarkup, KeyboardButton, LabeledPrice)
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                          MessageHandler, ContextTypes, filters,
                          PreCheckoutQueryHandler)
import database as db
from lang import t, t_feature, render_premium_emoji, strip_premium_emoji, extract_premium_emoji
from config import *

from logging.handlers import RotatingFileHandler
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[logging.StreamHandler(),
              RotatingFileHandler("bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")])
log = logging.getLogger(__name__)


# ═══════════ گزارشات گروهی (تاپیک‌دار) ═══════════
async def send_report(ctx, category, text=None, photo=None, kb=None):
    """ارسال گزارش به تاپیک مربوطه در گروه گزارشات و/یا پیوی ادمین‌ها.

    ctx می‌تواند context هندلرها یا خود Application باشد (هر دو .bot دارند).
    """
    bot = ctx.bot
    gid = db.get_setting("report_group_id", "") or ""
    mode = db.get_setting("report_mode", "dm") or "dm"
    enabled = db.get_setting(f"report_on_{category}", "1") == "1"
    topic = db.get_setting(f"report_topic_{category}", "") or ""
    # ── ساعت سکوت گزارش‌ها (خطاها مستثنا) ──
    qs = db.get_setting("report_quiet_start", "") or ""
    qe = db.get_setting("report_quiet_end", "") or ""
    if qs and qe and category != "errors":
        _hm = datetime.now().strftime("%H:%M")
        _quiet = (qs <= _hm < qe) if qs <= qe else (_hm >= qs or _hm < qe)
        if _quiet:
            return
    sent_group = False
    if gid and enabled and mode in ("group", "both"):
        try:
            kwargs = {"parse_mode": "HTML", "reply_markup": kb}
            if topic:
                kwargs["message_thread_id"] = int(topic)
            if photo:
                await bot.send_photo(int(gid), photo, caption=text, **kwargs)
            else:
                await bot.send_message(int(gid), text, **kwargs)
            sent_group = True
        except Exception as e:
            log.error(f"send_report({category}) to group failed: {e}")
    if mode in ("dm", "both") or (mode == "group" and not sent_group):
        all_admins = [a["user_id"] for a in db.get_all_admins()] + ADMIN_IDS
        for aid in set(all_admins):
            try:
                if photo:
                    await bot.send_photo(aid, photo, caption=text, reply_markup=kb, parse_mode="HTML")
                else:
                    await bot.send_message(aid, text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass

# ═══════════ کش نرخ دلار ═══════════
_usd_rate_cache = {"rate": USD_RATE_FALLBACK, "ts": 0}


def _get_usd_rate_from_provider():
    """دریافت نرخ دلار بر اساس provider ذخیره‌شده در دیتابیس."""
    provider = db.get_setting("usd_rate_provider", "tgju")
    api_key = db.get_setting("usd_rate_api_key", "")
    manual_rate = db.get_setting("usd_rate_manual", str(USD_RATE_FALLBACK))

    if provider == "manual":
        return int(manual_rate or USD_RATE_FALLBACK)

    if provider == "navasan":
        key = api_key or _USD_RATE_API_KEY
        url = f"https://api.navasan.tech/latest/?api={key}"
        r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"}).json()
        usd = r.get("usd", {})
        val = usd.get("value", usd.get("sell", 0)) if isinstance(usd, dict) else usd
        return int(float(str(val).replace(",", "")))

    elif provider == "tgju":
        url = "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl"
        r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}).json()
        rows = r.get("data", [])
        if rows and isinstance(rows[0], list):
            val = rows[0][0]
            rials = int(float(str(val).replace(",", "")))
            return rials // 10  # Convert Rials to Tomans
        raise ValueError("Unexpected TGJU response format")

    else:
        # Fallback to original Navasan
        r = requests.get(USD_RATE_API, timeout=8).json()
        return int(r.get(USD_RATE_FIELD, {}).get("value", USD_RATE_FALLBACK))


def _fetch_usd_rate_sync():
    """دریافت نرخ دلار از API (همزمان — فقط از executor فراخوانی شود)"""
    now = time.time()
    # Read cache minutes from DB (default 30)
    try:
        cache_mins = int(db.get_setting("usd_rate_cache_minutes", str(USD_RATE_CACHE_MINUTES)) or USD_RATE_CACHE_MINUTES)
    except Exception:
        cache_mins = USD_RATE_CACHE_MINUTES

    if now - _usd_rate_cache["ts"] < cache_mins * 60:
        return _usd_rate_cache["rate"]
    try:
        rate = _get_usd_rate_from_provider()
        if rate > 1000:
            _usd_rate_cache["rate"] = rate
            _usd_rate_cache["ts"] = now
            return rate
    except Exception as e:
        log.warning(f"USD rate fetch error: {e}")
    return _usd_rate_cache["rate"]

def get_usd_rate():
    """نسخه همزمان — فقط در زمینه‌های غیر async استفاده شود"""
    return _fetch_usd_rate_sync()

async def get_usd_rate_async():
    """نسخه async — برای استفاده در هندلرهای Telegram"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_usd_rate_sync)

# ═══════════ توابع کمکی ═══════════
def is_admin(uid):
    """بررسی ادمین بودن - از دیتابیس یا config"""
    if uid in ADMIN_IDS:
        return True
    return db.is_admin_user(uid)

def has_perm(uid, perm):
    """بررسی دسترسی ادمین"""
    if uid in ADMIN_IDS:
        return True
    return db.admin_has_perm(uid, perm)

def _btn_label_icon(text):
    """Bot API 9.4: when enabled in the panel, the first premium emoji of a button
    label becomes icon_custom_emoji_id; otherwise the fallback emoji is kept."""
    if db.get_setting("premium_button_icons", "0") == "1":
        return extract_premium_emoji(text)
    return strip_premium_emoji(text), None

def _btn_kwargs(style=None, icon=None):
    _kw = {}
    if style:
        _kw["style"] = style
    if icon:
        _kw["icon_custom_emoji_id"] = icon
    return _kw or None

def btn(text, data, style=None, icon=None):
    if icon is None:
        text, icon = _btn_label_icon(text)
    return InlineKeyboardButton(text, callback_data=data,
                                 api_kwargs=_btn_kwargs(style, icon))

def L(uid):
    u = db.get_user(uid)
    return (u["lang"] if u and u["lang"] else "fa")

def get_feature(key, default="1"):
    """دریافت وضعیت قابلیت از دیتابیس"""
    val = db.get_setting(f"feature_{key}", default)
    return val == "1"

def get_card_number():
    return db.get_setting("card_number", CARD_NUMBER)

def get_card_holder():
    return db.get_setting("card_holder", CARD_HOLDER)

def get_usdt_wallet():
    return db.get_setting("usdt_wallet", USDT_WALLET)

def get_feature_value(key, default=""):
    """دریافت مقدار سفارشی یک قابلیت (نه وضعیت روشن/خاموش)"""
    return db.get_setting(f"feature_{key}", default)

def get_welcome_text(lang):
    """پیام خوش‌آمدگویی سفارشی از پنل؛ در غیر این صورت پیام پیش‌فرض"""
    custom = db.get_setting("welcome_message", "")
    return render_premium_emoji(custom) if custom else t("welcome", lang)

def get_support_username():
    """آیدی پشتیبانی سفارشی از پنل؛ در غیر این صورت مقدار پیش‌فرض config"""
    custom = db.get_setting("support_username", "")
    return custom if custom else SUPPORT_USERNAME

def maintenance_active():
    return get_feature("maintenance_mode", "0")

def get_maintenance_text(lang):
    msg = get_feature_value("maintenance_message", "")
    return msg if msg else t("maintenance_default", lang)


# ═══════════ ضداسپم، سطح کاربر، بونوس شارژ ═══════════
_spam_track = {}

def _spam_hit(uid):
    """محدودیت تعداد پیام در دقیقه (0 = غیرفعال)"""
    try:
        limit = int(float(db.get_setting("antispam_per_min", "0") or 0))
    except ValueError:
        limit = 0
    if limit <= 0:
        return False
    now = time.time()
    hits = [h for h in _spam_track.get(uid, []) if now - h < 60]
    hits.append(now)
    if hits:
        _spam_track[uid] = hits
    else:
        # پاک‌سازی کلید برای جلوگیری از نشت حافظه
        _spam_track.pop(uid, None)
    return len(hits) > limit


def _spam_cleanup():
    """حذف کاربران غیرفعال از دیکشنری ضداسپم (فراخوانی دوره‌ای)"""
    now = time.time()
    stale = [uid for uid, hits in _spam_track.items()
             if not any(now - h < 60 for h in hits)]
    for uid in stale:
        del _spam_track[uid]


def get_user_level(total_spent):
    """سطح کاربر بر اساس مجموع خرید: 0=برنزی 1=نقره‌ای 2=طلایی"""
    try:
        silver = float(db.get_setting("level_silver_spend", "50") or 50)
        gold = float(db.get_setting("level_gold_spend", "200") or 200)
    except ValueError:
        silver, gold = 50, 200
    if total_spent >= gold:
        return 2
    if total_spent >= silver:
        return 1
    return 0


def get_level_discount(uid):
    """درصد تخفیف سطح کاربر (اگر قابلیت فعال باشد)"""
    if db.get_setting("levels_enabled", "0") != "1":
        return 0
    try:
        stats = db.get_user_stats(uid)
        lvl = get_user_level(stats["total_spent"] or 0)
        if lvl == 2:
            return float(db.get_setting("level_gold_discount", "7") or 0)
        if lvl == 1:
            return float(db.get_setting("level_silver_discount", "3") or 0)
    except Exception:
        pass
    return 0


def apply_deposit_bonus(uid, amount):
    """بونوس شارژ — درصد اضافه روی واریز موفق (0 = غیرفعال)"""
    try:
        percent = float(db.get_setting("deposit_bonus_percent", "0") or 0)
        min_amt = float(db.get_setting("deposit_bonus_min", "0") or 0)
        if percent > 0 and amount >= min_amt:
            bonus = round(amount * percent / 100, 2)
            if bonus > 0:
                db.add_balance(uid, bonus)
                return bonus
    except Exception:
        pass
    return 0


async def _maybe_big_deposit_alert(ctx, uid, amount):
    """هشدار واریز بزرگ به ادمین‌ها (آستانه از پنل)"""
    try:
        threshold = float(db.get_setting("alert_big_deposit", "0") or 0)
        if threshold > 0 and amount >= threshold:
            await send_report(ctx, "deposits",
                f"🚨 واریز بزرگ!\n👤 <code>{uid}</code>\n💵 ${amount:.2f}")
    except Exception:
        pass


# ═══════════ کیبوردها ═══════════
_BUTTON_MENUS = {
    "main_reply": ["kb_start", "kb_products", "kb_support", "kb_lang"],
    "main_inline": ["btn_browse", "btn_orders", "btn_recharge", "btn_profile",
                     "btn_support", "btn_invite", "btn_lang", "btn_admin"],
    "admin_panel": ["adm_btn_products", "adm_btn_users", "adm_btn_codes", "adm_btn_cards",
                     "adm_btn_tickets", "adm_btn_warranty", "adm_btn_lock", "adm_btn_admins",
                     "adm_btn_payment", "adm_btn_apis", "adm_btn_settings", "adm_btn_broadcast"],
    "profile_menu": ["btn_recharge", "btn_orders", "btn_invite", "btn_back"],
    "recharge_menu": ["pay_usdt", "pay_usdt_trc20", "pay_ton", "pay_stars", "pay_zarinpal", "pay_card", "btn_back"],
    "support_menu": ["btn_tickets", "btn_new_ticket", "btn_back"],
    "invite_menu": ["btn_reftop", "btn_back"],
}

_MAIN_MENU_TARGETS = {
    "btn_browse": "browse", "btn_orders": "orders", "btn_recharge": "recharge",
    "btn_profile": "profile", "btn_support": "support", "btn_invite": "invite",
    "btn_lang": "lang", "btn_admin": "admin",
}

_ADMIN_PANEL_TARGETS = {
    "adm_btn_products": "a_products", "adm_btn_users": "a_users", "adm_btn_codes": "a_codes",
    "adm_btn_cards": "a_cards", "adm_btn_tickets": "a_tickets", "adm_btn_warranty": "a_warranty",
    "adm_btn_lock": "a_lock", "adm_btn_admins": "a_admins", "adm_btn_payment": "a_payment_methods",
    "adm_btn_apis": "a_apis", "adm_btn_settings": "a_settings", "adm_btn_broadcast": "a_broadcast",
}

_STYLE_MAP = {"blue": "primary", "green": "success", "red": "danger"}

_PROFILE_TARGETS = {"btn_recharge": "recharge", "btn_orders": "orders", "btn_invite": "invite", "btn_back": "home"}
_RECHARGE_TARGETS = {"pay_usdt": "usdt", "pay_usdt_trc20": "usdt_trc20", "pay_ton": "ton",
                     "pay_stars": "stars", "pay_zarinpal": "zarinpal", "pay_card": "card", "btn_back": "home"}
_SUPPORT_TARGETS = {"btn_tickets": "my_tickets", "btn_new_ticket": "new_ticket", "btn_back": "home"}
_INVITE_TARGETS = {"btn_reftop": "reftop", "btn_back": "home"}


def menu_kb(menu_key, targets, lang, allowed=None):
    # ساخت کیبورد زیرمنو طبق چیدمان/متن/رنگ تنظیم‌شده در پنل تحت وب
    kb = []
    for row in get_button_layout(menu_key, lang):
        out = [btn(label, targets[key], style, icon) for key, label, style, icon in row
               if key in targets and (allowed is None or key in allowed)]
        if out:
            kb.append(out)
    if not kb:
        kb = [[btn(t("btn_back", lang), "home")]]
    return kb


def get_button_layout(menu_key, lang):
    # چیدمان گریدی (ردیف‌بندی)، نمایش/مخفی‌شدن، رنگ و متن دلخواه دکمه‌های یک منو طبق تنظیمات پنل تحت وب
    # خروجی: لیستی از ردیف‌ها، هر ردیف لیستی از تاپل‌های (کلید, متن, استایل رنگ)
    default_keys = _BUTTON_MENUS.get(menu_key, [])
    raw = db.get_setting(f"button_layout_{menu_key}", "")
    rows_cfg, hidden_cfg, meta = None, [], {}
    if raw:
        try:
            parsed = json.loads(raw)
            rows_cfg = parsed.get("rows")
            hidden_cfg = parsed.get("hidden") or []
            meta = parsed.get("meta") or {}
        except Exception:
            rows_cfg = None
    if rows_cfg is None:
        rows_cfg = [default_keys[i:i + 2] for i in range(0, len(default_keys), 2)]
        hidden_cfg = []
    def _entry(k):
        label = ((meta.get(k) or {}).get("label") or "").strip()
        style = _STYLE_MAP.get((meta.get(k) or {}).get("color") or "")
        _lbl, _icon = _btn_label_icon(label if label else t(k, lang))
        return (k, _lbl, style, _icon)
    result = []
    seen = set()
    for row in rows_cfg:
        out_row = []
        for k in row:
            if k not in default_keys or k in seen:
                continue
            seen.add(k)
            out_row.append(_entry(k))
        if out_row:
            result.append(out_row)
    for k in default_keys:
        if k not in seen and k not in hidden_cfg:
            result.append([_entry(k)])
            seen.add(k)
    return result


def reply_kb(lang):
    rows = get_button_layout("main_reply", lang)
    if not rows:
        return ReplyKeyboardMarkup([[KeyboardButton(strip_premium_emoji(t("kb_start", lang)))]], resize_keyboard=True)
    kb = [[KeyboardButton(label, api_kwargs=_btn_kwargs(style, icon))
           for _, label, style, icon in row] for row in rows]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def main_menu(uid, lang):
    admin = is_admin(uid)
    rows = get_button_layout("main_inline", lang)
    kb = []
    for row in rows:
        out_row = [btn(label, _MAIN_MENU_TARGETS[key], style, icon) for key, label, style, icon in row
                    if key != "btn_admin" or admin]
        if out_row:
            kb.append(out_row)
    return InlineKeyboardMarkup(kb)

def back_kb(lang, target="home"):
    return InlineKeyboardMarkup([[btn(t("btn_back", lang), target)]])

def lang_kb():
    return InlineKeyboardMarkup([
        [btn("🇮🇷 فارسی", "setlang:fa"), btn("🇬🇧 English", "setlang:en")]])

# ═══════════ تأیید تراکنش USDT — BEP20 (BSC) ═══════════
def verify_usdt_bep20(tx_hash: str):
    try:
        wallet = get_usdt_wallet()

        def rpc(action, **params):
            p = {"module": "proxy", "action": action, "apikey": BSCSCAN_API_KEY, **params}
            return requests.get(BSCSCAN_API, params=p, timeout=15).json().get("result")

        tx = rpc("eth_getTransactionByHash", txhash=tx_hash)
        if not tx or not isinstance(tx, dict):
            return False, "❌ Transaction not found | تراکنش پیدا نشد."

        receipt = rpc("eth_getTransactionReceipt", txhash=tx_hash)
        if not receipt or not isinstance(receipt, dict) or receipt.get("status") != "0x1":
            return False, "❌ TX failed or pending | تراکنش ناموفق یا در انتظار تأیید است."

        if (tx.get("to") or "").lower() != USDT_CONTRACT:
            return False, "❌ Not a USDT (BEP20) transfer | این تراکنش USDT نیست."

        data = tx.get("input", "")
        if not data.startswith("0xa9059cbb"):
            return False, "❌ Invalid transfer type | نوع تراکنش نامعتبر."

        to_addr = "0x" + data[10:74][-40:]
        # USDT BEP20 (BSC) uses 18 decimals
        amount = int(data[74:138], 16) / 10**18

        if to_addr.lower() != wallet.lower():
            return False, "❌ Wrong destination wallet | مقصد، کیف پول فروشگاه نیست."
        min_dep = float(db.get_setting("min_deposit", MIN_DEPOSIT))
        max_dep = float(db.get_setting("max_deposit", 0) or 0)
        if amount < min_dep:
            return False, f"❌ Minimum deposit is ${min_dep} | حداقل واریز ${min_dep}"
        if max_dep and amount > max_dep:
            return False, f"❌ Maximum deposit is ${max_dep} | حداکثر واریز ${max_dep}"

        block = rpc("eth_getBlockByNumber", tag=tx["blockNumber"], boolean="false")
        if not block or not isinstance(block, dict):
            return False, "❌ Could not verify block timestamp | خطا در بررسی زمان تراکنش."
        ts = int(block["timestamp"], 16)
        if time.time() - ts > TX_MAX_AGE_HOURS * 3600:
            return False, "❌ Transaction too old | تراکنش قدیمی است."

        return True, round(amount, 2)
    except Exception as e:
        log.error(f"verify_usdt_bep20 error: {e}", exc_info=True)
        return False, "❌ Verification error, try again | خطا در بررسی."

# ═══════════ بررسی سن اکانت تلگرام ═══════════
def estimate_account_age_days(user_id: int) -> int:
    """تخمین سن اکانت بر اساس user_id تلگرام.
    این یک تخمین است چون API رسمی برای این وجود ندارد.
    نقاط مرجع بر اساس user_id های شناخته‌شده به‌روزرسانی شده‌اند.
    """
    base_id = 100_000_000   # تقریباً ژانویه ۲۰۱۴
    base_date = datetime(2014, 1, 1, tzinfo=timezone.utc)
    # به‌روزرسانی: بر اساس آمار ۲۰۲۶ — IDs بیش از ۷ میلیارد هستند
    max_id = 10_000_000_000  # تقریباً اواخر ۲۰۲۶
    max_date = datetime(2027, 1, 1, tzinfo=timezone.utc)

    if user_id <= base_id:
        days = (datetime.now(timezone.utc) - base_date).days + 365
    elif user_id >= max_id:
        # کاربران بسیار جدید — تخمین محافظه‌کارانه
        days = 30
    else:
        ratio = (user_id - base_id) / (max_id - base_id)
        total_days = (max_date - base_date).days
        estimated_reg = base_date.timestamp() + ratio * total_days * 86400
        days = int((time.time() - estimated_reg) / 86400)

    return max(0, days)

# ═══════════ USDT TRC20 (TRON) ═══════════
def verify_usdt_trc20(tx_hash):
    """تایید تراکنش USDT روی شبکه ترون از طریق TronScan (بدون نیاز به API Key)"""
    wallet = (db.get_setting("usdt_trc20_wallet", "") or "").strip()
    if not wallet:
        return False, "❌ کیف پول TRC20 تنظیم نشده است."
    try:
        r = requests.get("https://apilist.tronscanapi.com/api/transaction-info",
                         params={"hash": tx_hash}, timeout=20).json()
    except Exception as e:
        return False, f"❌ خطا در ارتباط با TronScan: {e}"
    if not r or r.get("contractRet") != "SUCCESS":
        return False, "❌ تراکنش یافت نشد یا ناموفق است."
    usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    for tr in (r.get("trc20TransferInfo") or []):
        if tr.get("contract_address") == usdt_contract and \
                str(tr.get("to_address", "")).lower() == wallet.lower():
            try:
                decimals = int(tr.get("decimals", 6) or 6)
                amount = float(tr.get("amount_str", tr.get("quant", 0)) or 0) / (10 ** decimals)
            except (TypeError, ValueError):
                return False, "❌ خطا در خواندن مبلغ تراکنش."
            ts = (r.get("timestamp", 0) or 0) / 1000
            if ts and time.time() - ts > TX_MAX_AGE_HOURS * 3600:
                return False, "❌ تراکنش قدیمی است."
            min_dep = float(db.get_setting("min_deposit", MIN_DEPOSIT))
            max_dep = float(db.get_setting("max_deposit", 0) or 0)
            if amount < min_dep:
                return False, f"❌ حداقل واریز ${min_dep} است."
            if max_dep and amount > max_dep:
                return False, f"❌ حداکثر واریز ${max_dep} است."
            return True, round(amount, 2)
    return False, "❌ انتقال USDT به کیف پول ما در این تراکنش پیدا نشد."


# ═══════════ TON ═══════════
_ton_rate_cache = {"rate": 0.0, "ts": 0}

def _get_ton_usd_rate():
    if time.time() - _ton_rate_cache["ts"] < 600 and _ton_rate_cache["rate"]:
        return _ton_rate_cache["rate"]
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids": "the-open-network", "vs_currencies": "usd"}, timeout=15).json()
        rate = float(r["the-open-network"]["usd"])
        _ton_rate_cache.update({"rate": rate, "ts": time.time()})
        return rate
    except Exception:
        manual = float(db.get_setting("ton_usd_rate", "0") or 0)
        return manual or _ton_rate_cache["rate"] or 5.0


def verify_ton_deposit(uid):
    """بررسی تراکنش‌های ورودی TON با کامنت اختصاصی کاربر (dep<uid>)"""
    wallet = (db.get_setting("ton_wallet", "") or "").strip()
    if not wallet:
        return False, "❌ کیف پول TON تنظیم نشده است."
    try:
        r = requests.get("https://toncenter.com/api/v2/getTransactions",
                         params={"address": wallet, "limit": 30}, timeout=20).json()
    except Exception as e:
        return False, f"❌ خطا در ارتباط با شبکه TON: {e}"
    if not r.get("ok"):
        return False, "❌ پاسخ نامعتبر از شبکه TON."
    memo = f"dep{uid}"
    for tx in r.get("result", []):
        msg = tx.get("in_msg") or {}
        if (msg.get("message") or "").strip() != memo:
            continue
        tx_id = (tx.get("transaction_id") or {}).get("hash", "")
        if not tx_id or db.tx_exists(f"ton_{tx_id}"):
            continue
        if time.time() - int(tx.get("utime", 0) or 0) > TX_MAX_AGE_HOURS * 3600:
            continue
        ton_amount = int(msg.get("value", 0) or 0) / 1e9
        usd = round(ton_amount * _get_ton_usd_rate(), 2)
        min_dep = float(db.get_setting("min_deposit", MIN_DEPOSIT))
        if usd < min_dep:
            return False, f"❌ مبلغ واریزی کمتر از حداقل (${min_dep}) است."
        return True, (f"ton_{tx_id}", usd)
    return False, "❌ تراکنش جدیدی با کد شما پیدا نشد. اگر تازه پرداخت کرده‌اید چند دقیقه بعد دوباره بزنید."


# ═══════════ زرین‌پال ═══════════
def zarinpal_request(amount_toman, uid, usd):
    """ساخت لینک پرداخت زرین‌پال. برگشت: (link, error)"""
    merchant = db.get_setting("zarinpal_merchant", "")
    base_url = (db.get_setting("panel_base_url", "") or "").rstrip("/")
    if not merchant:
        return None, "مرچنت زرین‌پال در پنل تنظیم نشده"
    if not base_url:
        return None, "آدرس عمومی پنل در تنظیمات پرداخت تنظیم نشده"
    amount_rial = int(amount_toman) * 10
    try:
        r = requests.post("https://payment.zarinpal.com/pg/v4/payment/request.json", json={
            "merchant_id": merchant,
            "amount": amount_rial,
            "callback_url": f"{base_url}/api/pay/zarinpal/callback",
            "description": f"شارژ حساب {uid}",
        }, timeout=20).json()
        authority = (r.get("data") or {}).get("authority")
        if authority:
            db.add_zp_pending(authority, uid, amount_rial, usd)
            return f"https://payment.zarinpal.com/pg/StartPay/{authority}", None
        return None, str(r.get("errors"))
    except Exception as e:
        return None, str(e)


# ═══════════ رفرال: واریز پورسانت (دو سطح + سقف روزانه) ═══════════
async def pay_referral(context, uid, amount):
    if not get_feature("referral"):
        return
    user = db.get_user(uid)
    if not user or not user["referrer"]:
        return
    daily_cap = float(db.get_setting("referral_daily_cap", "0") or 0)

    async def _pay(ref_id, percent):
        bonus = round(amount * percent / 100, 2)
        if bonus <= 0:
            return
        if daily_cap:
            earned = db.ref_earned_today(ref_id)
            if earned >= daily_cap:
                return
            bonus = min(bonus, round(daily_cap - earned, 2))
        db.add_balance(ref_id, bonus, ref_earning=True)
        db.log_ref_earning(ref_id, bonus)
        try:
            rl = L(ref_id)
            await context.bot.send_message(ref_id, t("ref_bonus", rl, a=bonus), parse_mode="HTML")
        except Exception:
            pass

    await _pay(user["referrer"], float(db.get_setting("referral_percent", REFERRAL_PERCENT)))
    # سطح دوم
    percent2 = float(db.get_setting("referral_l2_percent", "0") or 0)
    if percent2 > 0:
        ref1 = db.get_user(user["referrer"])
        if ref1 and ref1["referrer"]:
            await _pay(ref1["referrer"], percent2)

class _FakeQ:
    """شبیه‌ساز CallbackQuery برای فراخوانی show_confirm از پیام متنی (حذف کد تکراری)"""
    def __init__(self, message):
        self.message = message

    async def edit_message_text(self, *a, **k):
        raise Exception()


_cc_cache = {"ts": 0.0, "rows": []}

def _get_custom_commands_cached(ttl=30):
    """کش ۳۰ ثانیه‌ای دستورهای سفارشی — جلوگیری از کوئری دیتابیس در هر پیام متنی"""
    now = time.time()
    if now - _cc_cache["ts"] > ttl:
        _cc_cache["rows"] = [dict(r) for r in db.get_custom_commands()]
        _cc_cache["ts"] = now
    return _cc_cache["rows"]


# ═══════════ /start ═══════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    if maintenance_active() and not is_admin(u.id):
        await update.message.reply_text(get_maintenance_text(L(u.id)), parse_mode="HTML")
        return
    referrer = None
    if context.args and context.args[0].startswith("ref"):
        try:
            rid = int(context.args[0][3:])
            if rid != u.id and db.get_user(rid):
                # بررسی سن اکانت برای رفرال
                if get_feature("referral"):
                    age = estimate_account_age_days(u.id)
                    db.update_user_account_age(u.id, age)
                    if age >= int(db.get_setting("referral_min_days", REFERRAL_MIN_DAYS)):
                        referrer = rid
                    else:
                        # ثبت کاربر بدون رفرال
                        pass
                else:
                    referrer = rid
        except ValueError:
            pass

    if not db.get_user(u.id) and get_feature("registration_locked", "0") and not is_admin(u.id):
        await update.message.reply_text(t("registration_locked_msg", "fa"))
        return

    is_new_user = db.get_user(u.id) is None
    db.add_user(u.id, u.username or "", referrer)
    db.log_event(u.id, "start")
    # ── امنیت: تشخیص رفرال مشکوک (چنداکانتی) ──
    if is_new_user and referrer:
        try:
            _limit = int(float(db.get_setting("ref_fraud_daily", "0") or 0))
            if _limit > 0:
                _n = db.referrals_today(referrer)
                if _n == _limit + 1:
                    await send_report(context, "new_users",
                        f"🚨 رفرال مشکوک!\n👤 کاربر <code>{referrer}</code> امروز {_n} زیرمجموعه گرفته است (آستانه: {_limit}).\nاحتمال ساخت اکانت تقلبی برای دریافت پاداش وجود دارد.")
        except Exception:
            pass
    if is_new_user:
        try:
            await send_report(context, "new_users",
                f"👤 کاربر جدید در ربات\n🆔 <code>{u.id}</code> @{u.username or 'N/A'}"
                + (f"\n🎁 معرف: <code>{referrer}</code>" if referrer else ""))
        except Exception:
            pass
        # پاداش ثابت عضوگیری برای معرف
        if referrer:
            try:
                sb = float(db.get_setting("referral_signup_bonus", "0") or 0)
                if sb > 0:
                    db.add_balance(referrer, sb, ref_earning=True)
                    db.log_ref_earning(referrer, sb)
                    await context.bot.send_message(referrer, t("ref_signup_bonus", L(referrer), a=sb),
                                                   parse_mode="HTML")
            except Exception:
                pass
    context.user_data.clear()
    user = db.get_user(u.id)
    if user["blocked"]:
        await update.message.reply_text(t("blocked", user["lang"] or "fa"))
        return
    if not user["lang"]:
        await update.message.reply_text(t("choose_lang", "fa"), reply_markup=lang_kb())
        return
    lang = user["lang"]

    # ── کپچای ضدربات ──
    # وضعیت captcha در bot_data (حافظه موقت) ذخیره می‌شود نه در جدول settings دیتابیس
    _captcha_passed = context.bot_data.get("captcha_ok", set())
    if db.get_setting("captcha_enabled", "0") == "1" and not is_admin(u.id) \
            and u.id not in _captcha_passed:
        a, b = random.randint(2, 9), random.randint(2, 9)
        context.user_data["state"] = "captcha"
        context.user_data["captcha_answer"] = str(a + b)
        await update.message.reply_text(t("captcha_q", lang, a=a, b=b), parse_mode="HTML")
        return

    # ── بررسی عضویت در کانال‌ها/گروه‌های قفل‌شده ──
    if get_feature("lock_channels") or get_feature("lock_groups"):
        locked_channels = db.get_locked_channels() if get_feature("lock_channels") else []
        locked_groups = db.get_locked_groups() if get_feature("lock_groups") else []
        not_joined = []
        for ch in locked_channels:
            try:
                member = await context.bot.get_chat_member(ch["channel_id"], u.id)
                if member.status in ("left", "kicked"):
                    # دریافت لینک دعوت کانال
                    invite_link = None
                    try:
                        chat_info = await context.bot.get_chat(ch["channel_id"])
                        invite_link = chat_info.invite_link or chat_info.username
                        if chat_info.username:
                            invite_link = f"https://t.me/{chat_info.username}"
                    except Exception:
                        pass
                    not_joined.append(("📢", ch["title"], ch["channel_id"], invite_link))
            except Exception:
                pass
        for gr in locked_groups:
            try:
                member = await context.bot.get_chat_member(gr["group_id"], u.id)
                if member.status in ("left", "kicked"):
                    # دریافت لینک دعوت گروه
                    invite_link = None
                    try:
                        chat_info = await context.bot.get_chat(gr["group_id"])
                        invite_link = chat_info.invite_link or chat_info.username
                        if chat_info.username:
                            invite_link = f"https://t.me/{chat_info.username}"
                    except Exception:
                        pass
                    not_joined.append(("👥", gr["title"], gr["group_id"], invite_link))
            except Exception:
                pass
        if not_joined:
            join_text = (
                "⚠️ برای استفاده از ربات، ابتدا در کانال/گروه‌های زیر عضو شوید:\n\n"
                if lang == "fa" else
                "⚠️ To use the bot, please join the following channels/groups first:\n\n"
            )
            kb_join = []
            for icon, title, cid, invite_link in not_joined:
                join_text += f"{icon} <b>{title}</b>\n"
                if invite_link:
                    kb_join.append([InlineKeyboardButton(f"{icon} {title}", url=invite_link)])
            join_text += (
                "\n✅ پس از عضویت، دوباره /start بزنید."
                if lang == "fa" else
                "\n✅ After joining, press /start again."
            )
            await update.message.reply_text(
                join_text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(kb_join) if kb_join else None
            )
            return

    await update.message.reply_text(get_welcome_text(lang), reply_markup=main_menu(u.id, lang),
                                    parse_mode="HTML")

# ═══════════ Callback ها ═══════════
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data, uid = q.data, q.from_user.id
    user = db.get_user(uid)
    if not user:
        db.add_user(uid, q.from_user.username or "")
        user = db.get_user(uid)
    if user["blocked"] and not is_admin(uid):
        return
    lang = user["lang"] or "fa"

    if maintenance_active() and not is_admin(uid):
        await q.message.reply_text(get_maintenance_text(lang), parse_mode="HTML")
        return

    # پاک کردن state فقط برای callback های غیر ادمین-تأیید
    if not data.startswith(("cbapprove", "cbreject", "wapprove", "wreject", "sessapprove", "sessreject")):
        context.user_data.pop("state", None)

    async def edit(text, kb=None):
        try:
            await q.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass

    # ──── انتخاب زبان ────
    if data.startswith("setlang:"):
        newlang = data.split(":")[1]
        db.set_lang(uid, newlang)
        await edit(get_welcome_text(newlang), main_menu(uid, newlang))
        # ارسال کیبورد پایین با پیام تغییر زبان (بدون نقطه)
        await q.message.reply_text(t("lang_changed", newlang), reply_markup=reply_kb(newlang))

    elif data == "lang":
        await edit(t("choose_lang", lang), lang_kb())

    elif data == "home":
        await edit(get_welcome_text(lang), main_menu(uid, lang))

    # ──── محصولات ────
    elif data == "browse":
        cats = db.get_categories()
        if not cats:
            await edit(t("no_products", lang), back_kb(lang))
            return
        kb = [[btn(f"🗂 {c['name']}", f"cat:{c['id']}")] for c in cats]
        kb.append([btn(t("btn_back", lang), "home")])
        await edit(t("pick_cat", lang), InlineKeyboardMarkup(kb))

    elif data.startswith("cat:"):
        cid = int(data.split(":")[1])
        kb = []
        for p in db.get_products(cid):
            s = db.stock_count(p["id"])
            warranty = " 🛡" if p["has_warranty"] else ""
            kb.append([btn(f"{'✨' if s else '❌'} {p['name']} — ${p['price']}{warranty}",
                           f"prod:{p['id']}")])
        kb.append([btn(t("btn_back", lang), "browse")])
        await edit(t("pick_prod", lang), InlineKeyboardMarkup(kb))

    elif data.startswith("prod:"):
        p = db.get_product(int(data.split(":")[1]))
        if not p:
            await edit("❌ محصول یافت نشد.", back_kb(lang, "browse"))
            return
        s = db.stock_count(p["id"])
        db.log_event(uid, "view_product", p["id"])
        _avg, _votes = db.get_product_rating(p["id"])
        rating_text = f"\n⭐ {t('rating_label', lang)}: <b>{_avg}/5</b> ({_votes})" if _votes else ""
        _dur = p["duration_days"] if "duration_days" in p.keys() else 0
        duration_text = f"\n{t('duration_label', lang)}: <b>{_dur} {t('days_word', lang)}</b>" if _dur else ""
        features_text = ""
        if p["features"]:
            features_text = f"\n\n{t('features_label', lang)}\n" + "\n".join(
                f"  • {f.strip()}" for f in p["features"].split("\n") if f.strip())
        warranty_text = f"\n{t('warranty_badge', lang)}" if p["has_warranty"] else ""
        text = (f"📦 <b>{p['name']}</b>\n\n📝 {p['description']}"
                f"{features_text}{warranty_text}{rating_text}{duration_text}\n\n"
                f"{t('sold', lang)}: <b>{p['sold']}</b>\n"
                f"{t('price', lang)}: <b>${p['price']}</b>\n"
                f"{t('stock', lang)}: {('✅ ' + str(s)) if s else t('out_stock', lang)}")
        kb = []
        if s:
            kb.append([btn(t("buy_now", lang), f"buy:{p['id']}")])
        kb.append([btn(t("btn_back", lang), f"cat:{p['category_id']}")])

        # نمایش بنر اگر وجود داشت
        if p["banner_url"]:
            try:
                await q.message.reply_photo(p["banner_url"], caption=text,
                                            reply_markup=InlineKeyboardMarkup(kb),
                                            parse_mode="HTML")
                return
            except Exception:
                pass
        await edit(text, InlineKeyboardMarkup(kb))

    elif data.startswith("buy:"):
        pid = int(data.split(":")[1])
        # ── امنیت: حالت توقف اضطراری فروش ──
        if db.get_setting("sales_paused", "0") == "1" and not is_admin(uid):
            await edit(t("sales_paused_msg", lang), back_kb(lang))
            return
        db.log_event(uid, "buy_click", pid)
        p = db.get_product(pid)
        s = db.stock_count(pid)
        if s > 1:
            # پرسیدن تعداد
            context.user_data["buy_pid"] = pid
            context.user_data.pop("discount", None)
            context.user_data["state"] = "await_qty"
            await edit(t("ask_qty", lang, s=s), back_kb(lang, f"prod:{pid}"))
        else:
            context.user_data["buy_pid"] = pid
            context.user_data["buy_qty"] = 1
            context.user_data.pop("discount", None)
            await show_confirm(q, context, uid, lang)

    elif data == "enter_discount":
        context.user_data["state"] = "await_discount"
        await edit(t("enter_code", lang),
                   back_kb(lang, f"buy:{context.user_data.get('buy_pid')}"))

    elif data == "do_purchase":
        pid = context.user_data.get("buy_pid")
        qty = context.user_data.get("buy_qty", 1)
        if not pid:
            return
        if db.get_setting("sales_paused", "0") == "1" and not is_admin(uid):
            await edit(t("sales_paused_msg", lang), back_kb(lang))
            return
        if get_feature("daily_purchase_limit", "0") and not is_admin(uid):
            try:
                daily_limit = int(get_feature_value("daily_purchase_limit_value", "5"))
            except (TypeError, ValueError):
                daily_limit = 5
            if db.count_orders_today(uid) >= daily_limit:
                await edit(t("daily_limit_reached", lang, n=daily_limit), back_kb(lang, f"prod:{pid}"))
                return
        p = db.get_product(pid)
        d = context.user_data.get("discount")
        if d:
            percent = d["percent"]
        elif get_feature("vip_mode", "0") and db.is_vip(uid):
            try:
                percent = int(get_feature_value("vip_discount", "10"))
            except (TypeError, ValueError):
                percent = 10
        else:
            percent = 0
        final = round(p["price"] * (100 - percent) / 100, 2)
        result = db.purchase(uid, p, final, qty)
        if result == "NO_BALANCE":
            await edit(t("no_balance", lang), InlineKeyboardMarkup([
                [btn(t("btn_recharge", lang), "recharge")],
                [btn(t("btn_back", lang), f"prod:{pid}")]]))
        elif result == "NO_STOCK":
            await edit(t("no_stock", lang), back_kb(lang, "browse"))
        else:
            if d:
                db.use_discount(d["code"], user_id=uid)
            items_text = "\n".join(f"<code>{c}</code>" for c in result)
            total = round(final * qty, 2)
            await edit(f"{t('buy_ok', lang)}\n\n📦 {p['name']} × {qty}\n💵 ${total}\n\n"
                       f"{t('your_item', lang)}\n{items_text}\n\n"
                       f"{t('save_it', lang)}\n{get_support_username()}", back_kb(lang))
            # اطلاع به ادمین‌ها / گروه گزارشات
            await send_report(context, "sales",
                f"🔔 فروش جدید!\n👤 <code>{uid}</code>\n📦 {p['name']} × {qty}\n💵 ${total}")
            db.log_event(uid, "purchase", pid)
            # ── اشتراک: ثبت تاریخ انقضا ──
            try:
                _dur = p["duration_days"] if "duration_days" in p.keys() else 0
                if _dur:
                    db.set_last_orders_expiry(uid, qty, _dur)
            except Exception:
                pass
            # ── درخواست امتیاز ⭐ ──
            try:
                _last = db.get_orders(uid, 1)
                _oid = _last[0]["id"] if _last else 0
                await q.message.reply_text(t("rate_ask", lang), reply_markup=InlineKeyboardMarkup(
                    [[btn(f"{i}⭐", f"rate:{_oid}:{pid}:{i}") for i in range(1, 6)]]))
            except Exception:
                pass
            # ── محصولات مرتبط ──
            try:
                _rel = [r for r in db.get_products(p["category_id"])
                        if r["id"] != pid and db.stock_count(r["id"]) > 0][:2]
                if _rel:
                    await q.message.reply_text(t("related_title", lang), reply_markup=InlineKeyboardMarkup(
                        [[btn(f"✨ {r['name']} — ${r['price']}", f"prod:{r['id']}")] for r in _rel]))
            except Exception:
                pass

    # ──── سفارش‌ها ────
    elif data == "orders":
        orders = db.get_orders(uid)
        if not orders:
            await edit(t("no_orders", lang), back_kb(lang))
            return
        text = t("orders_title", lang) + "\n\n"
        kb = []
        for o in orders:
            prod_name = o["name"] or "(deleted)"
            qty = o["quantity"] if o["quantity"] is not None else 1
            text += (f"🔹 <b>#{o['id']}</b> | {prod_name} × {qty} | "
                     f"${o['price']}\n   📅 {o['created_at'][:10]}\n\n")
            if o["has_warranty"] and get_feature("warranty"):
                kb.append([btn(f"🛡 #{o['id']} {t('warranty_claim_btn', lang)}",
                               f"warranty:{o['id']}")])
        kb.append([btn(t("btn_back", lang), "home")])
        # Truncate if text is too long for Telegram (4096 char limit)
        if len(text) > 3800:
            text = text[:3800] + "\n..."
        try:
            await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        except Exception:
            await q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

    elif data.startswith("rate:"):
        try:
            _, _oid, _pid, _stars = data.split(":")
            db.add_rating(uid, int(_pid), int(_oid), int(_stars))
            await q.edit_message_text(t("rate_thanks", lang))
        except Exception:
            pass

    elif data.startswith("warranty:"):
        if not get_feature("warranty"):
            return
        oid = int(data.split(":")[1])
        context.user_data["state"] = "await_warranty_reason"
        context.user_data["warranty_order_id"] = oid
        await edit(t("warranty_reason", lang), back_kb(lang, "orders"))

    elif data.startswith("wapprove:") or data.startswith("wreject:"):
        if not is_admin(uid):
            return
        cid = int(data.split(":")[1])
        approved = data.startswith("wapprove")
        status = "approved" if approved else "rejected"
        with db.get_db() as conn:
            claim = conn.execute("SELECT * FROM warranty_claims WHERE id=?", (cid,)).fetchone()
        db.update_warranty_claim(cid, status)
        await edit(f"{'✅ تأیید' if approved else '❌ رد'} شد. (گارانتی #{cid})")
        if claim:
            target_lang = L(claim["user_id"])
            try:
                notify_key = "warranty_approved_user" if approved else "warranty_rejected_user"
                await context.bot.send_message(
                    claim["user_id"], t(notify_key, target_lang, oid=claim["order_id"]), parse_mode="HTML")
            except Exception:
                pass

    # ──── پروفایل ────
    elif data == "profile":
        stats = db.get_user_stats(uid)
        age_days = stats["account_age"] or estimate_account_age_days(uid)
        age_text = t("account_age_days", lang, d=age_days)
        level_line = ""
        if db.get_setting("levels_enabled", "0") == "1":
            lvl_names = {0: t("level_bronze", lang), 1: t("level_silver", lang), 2: t("level_gold", lang)}
            lvl = get_user_level(stats["total_spent"] or 0)
            disc = get_level_discount(uid)
            disc_txt = f" ({disc:g}% تخفیف)" if disc else ""
            level_line = f"{t('level_lbl', lang)}: <b>{lvl_names[lvl]}{disc_txt}</b>\n"
        text = (f"{t('profile', lang)}\n\n"
                f"🆔 <code>{uid}</code>\n"
                f"👤 @{stats['username'] or 'N/A'}\n"
                f"{t('your_balance', lang)}: <b>${stats['balance']:.2f}</b>\n"
                f"{t('ref_earnings_lbl', lang)}: <b>${stats['ref_earnings']:.2f}</b>\n"
                f"{t('referrals', lang)}: <b>{stats['ref_total']}</b>\n"
                f"{t('total_orders', lang)}: <b>{stats['total_orders']}</b>\n"
                f"{t('total_spent', lang)}: <b>${stats['total_spent']:.2f}</b>\n"
                f"{level_line}"
                f"{t('account_age', lang)}: <b>{age_text}</b>\n"
                f"{t('joined', lang)}: {stats['joined_at'][:10]}")
        kb = menu_kb("profile_menu", _PROFILE_TARGETS, lang)
        await edit(text, InlineKeyboardMarkup(kb))

    # ──── شارژ حساب ────
    elif data == "recharge":
        rate = await get_usd_rate_async() if get_feature("usd_rate") else None
        rate_line = f"\n💱 نرخ دلار: <b>{rate:,} تومان</b>" if rate else ""
        _pm = lambda key, default="1": db.get_setting(key, default) == "1"
        allowed = {"btn_back"}
        if _pm("pm_usdt_bep20"):
            allowed.add("pay_usdt")
        if _pm("pm_usdt_trc20", "0") and db.get_setting("usdt_trc20_wallet", ""):
            allowed.add("pay_usdt_trc20")
        if _pm("pm_ton", "0") and db.get_setting("ton_wallet", ""):
            allowed.add("pay_ton")
        if _pm("pm_stars", "0"):
            allowed.add("pay_stars")
        if _pm("pm_zarinpal", "0") and db.get_setting("zarinpal_merchant", ""):
            allowed.add("pay_zarinpal")
        if _pm("pm_card") and (not get_feature("card_iranian_only") or lang == "fa"):
            allowed.add("pay_card")
        kb = menu_kb("recharge_menu", _RECHARGE_TARGETS, lang, allowed)
        await edit(t("recharge_title", lang) + rate_line, InlineKeyboardMarkup(kb))

    elif data == "usdt":
        wallet = get_usdt_wallet()
        await edit(t("usdt_guide", lang, w=wallet, m=db.get_setting("min_deposit", MIN_DEPOSIT)),
                   InlineKeyboardMarkup([[btn(t("send_tx", lang), "send_tx")],
                                         [btn(t("btn_back", lang), "recharge")]]))

    elif data == "send_tx":
        context.user_data["state"] = "await_tx"
        await edit(t("ask_tx", lang), back_kb(lang, "usdt"))

    elif data == "usdt_trc20":
        wallet = db.get_setting("usdt_trc20_wallet", "")
        await edit(t("usdt_trc20_guide", lang, w=wallet, m=db.get_setting("min_deposit", MIN_DEPOSIT)),
                   InlineKeyboardMarkup([[btn(t("send_tx", lang), "send_tx_trc20")],
                                         [btn(t("btn_back", lang), "recharge")]]))

    elif data == "send_tx_trc20":
        context.user_data["state"] = "await_tx_trc20"
        await edit(t("ask_tx", lang), back_kb(lang, "usdt_trc20"))

    elif data == "ton":
        wallet = db.get_setting("ton_wallet", "")
        await edit(t("ton_guide", lang, w=wallet, memo=f"dep{uid}"),
                   InlineKeyboardMarkup([[btn(t("ton_check", lang), "ton_check")],
                                         [btn(t("btn_back", lang), "recharge")]]))

    elif data == "ton_check":
        await edit(t("checking", lang))
        loop = asyncio.get_running_loop()
        ok, result = await loop.run_in_executor(None, verify_ton_deposit, uid)
        if ok:
            ton_tx, usd = result
            db.save_tx(uid, ton_tx, usd, "ton")
            bonus = apply_deposit_bonus(uid, usd)
            await pay_referral(context, uid, usd)
            u2 = db.get_user(uid)
            extra = f"\n🎁 بونوس: +${bonus:.2f}" if bonus else ""
            await edit(f"{t('tx_ok', lang)}\n\n💰 +${usd:.2f}{extra}\n"
                       f"{t('your_balance', lang)}: ${u2['balance']:.2f}", back_kb(lang))
            await send_report(context, "deposits",
                f"💠 واریز TON!\n👤 <code>{uid}</code>\n💵 ${usd}")
            await _maybe_big_deposit_alert(context, uid, usd)
        else:
            await edit(result, back_kb(lang, "ton"))

    elif data == "stars":
        context.user_data["state"] = "await_stars_amount"
        await edit(t("stars_ask_amount", lang, s=db.get_setting("stars_per_usd", "50")),
                   back_kb(lang, "recharge"))

    elif data == "zarinpal":
        context.user_data["state"] = "await_zp_amount"
        await edit(t("zp_ask_amount", lang), back_kb(lang, "recharge"))

    elif data == "card":
        if get_feature("card_iranian_only") and lang != "fa":
            await edit(t("card_only_fa", lang), back_kb(lang, "recharge"))
            return
        context.user_data["state"] = "await_card_amount"
        rate = await get_usd_rate_async() if get_feature("usd_rate") else USD_TO_TOMAN
        rate_line = t("card_rate_live", lang, r=rate) if get_feature("usd_rate") else ""
        card_num = get_card_number()
        card_hld = get_card_holder()
        await edit(t("card_guide", lang, c=card_num, h=card_hld, rate_line=rate_line),
                   back_kb(lang, "recharge"))

    # ──── تأیید/رد کارت به کارت توسط ادمین ────
    elif data.startswith("cbapprove:") or data.startswith("cbreject:"):
        if not is_admin(uid):
            return
        pay_id = int(data.split(":")[1])
        approved = data.startswith("cbapprove")
        # بررسی وضعیت قبل از تغییر — جلوگیری از double-spend
        current = db.get_card_payment(pay_id)
        if not current:
            await edit("❌ پرداخت یافت نشد.")
            return
        if current["status"] != "pending":
            await edit(f"⚠️ این پرداخت قبلاً پردازش شده است (وضعیت: {current['status']}).")
            return
        pay = db.set_card_status(pay_id, "approved" if approved else "rejected")
        target_lang = L(pay["user_id"])
        if approved:
            db.save_tx(pay["user_id"], f"card_{pay_id}", pay["amount"], "card")
            apply_deposit_bonus(pay["user_id"], pay["amount"])
            await pay_referral(context, pay["user_id"], pay["amount"])
            await _maybe_big_deposit_alert(context, pay["user_id"], pay["amount"])
            try:
                await context.bot.send_message(pay["user_id"], t("card_approved", target_lang))
            except Exception:
                pass
            try:
                await q.edit_message_caption(
                    caption=f"✅ تأیید شد | ${pay['amount']} → {pay['user_id']}")
            except Exception:
                await edit(f"✅ تأیید شد | ${pay['amount']} → {pay['user_id']}")
        else:
            try:
                await context.bot.send_message(pay["user_id"], t("card_rejected", target_lang))
            except Exception:
                pass
            try:
                await q.edit_message_caption(caption=f"❌ رد شد | {pay['user_id']}")
            except Exception:
                await edit(f"❌ رد شد | {pay['user_id']}")

    # ──── تأیید/رد نشست پنل ────
    elif data.startswith("sessapprove:") or data.startswith("sessreject:"):
        if not is_admin(uid):
            return
        sid = data.split(":", 1)[1]
        sess = db.get_panel_session(sid)
        if not sess:
            await edit("❌ نشست یافت نشد.")
            return
        who = f"👤 {sess['username'] or '-'} (<code>{sess['user_id']}</code>)\n🌐 <code>{sess['ip']}</code>"
        if data.startswith("sessapprove:"):
            db.set_panel_session_status(sid, "approved")
            await edit(f"✅ نشست تأیید شد\n{who}")
        else:
            db.set_panel_session_status(sid, "revoked")
            await edit(f"⛔ نشست رد شد — این دستگاه از پنل خارج می‌شود.\n{who}")

    # ──── رفرال ────
    elif data == "invite":
        if not get_feature("referral"):
            await edit("❌ سیستم رفرال غیرفعال است.", back_kb(lang))
            return
        me = await context.bot.get_me()
        link = f"https://t.me/{me.username}?start=ref{uid}"
        txt = t("invite_text", lang, link=link, p=db.get_setting("referral_percent", REFERRAL_PERCENT),
                c=db.ref_count(uid), e=user["ref_earnings"],
                d=db.get_setting("referral_min_days", REFERRAL_MIN_DAYS))
        banner = db.get_setting("referral_banner_text", "")
        if banner:
            txt += f"\n\n{render_premium_emoji(banner)}"
        allowed = {"btn_back"}
        if db.get_setting("referral_leaderboard", "0") == "1":
            allowed.add("btn_reftop")
        kb = menu_kb("invite_menu", _INVITE_TARGETS, lang, allowed)
        await edit(txt, InlineKeyboardMarkup(kb))

    elif data == "reftop":
        with db.get_db() as conn:
            rows = conn.execute(
                "SELECT username, user_id, ref_earnings, "
                "(SELECT COUNT(*) FROM users u2 WHERE u2.referrer = users.user_id) rc "
                "FROM users WHERE ref_earnings > 0 ORDER BY ref_earnings DESC LIMIT 10").fetchall()
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, r in enumerate(rows):
            name = f"@{r['username']}" if r["username"] else f"<code>{str(r['user_id'])[:4]}***</code>"
            rank = medals[i] if i < 3 else f"{i + 1}."
            lines.append(f"{rank} {name} — {r['rc']} 👥 — ${r['ref_earnings']:.2f}")
        body = "\n".join(lines) if lines else t("reftop_empty", lang)
        await edit(f"{t('reftop_title', lang)}\n\n{body}", back_kb(lang, "invite"))

    # ──── پشتیبانی ────
    elif data == "support":
        allowed = {"btn_back"}
        if get_feature("tickets"):
            allowed |= {"btn_tickets", "btn_new_ticket"}
        kb = menu_kb("support_menu", _SUPPORT_TARGETS, lang, allowed)
        await edit(t("support_text", lang, s=get_support_username()), InlineKeyboardMarkup(kb))

    elif data == "new_ticket":
        if not get_feature("tickets"):
            return
        context.user_data["state"] = "ticket_subject"
        await edit(t("ticket_subject", lang), back_kb(lang, "support"))

    elif data == "my_tickets":
        if not get_feature("tickets"):
            return
        tickets = db.get_tickets(user_id=uid)
        if not tickets:
            await edit(t("no_tickets", lang), back_kb(lang, "support"))
            return
        text = t("tickets_list", lang) + "\n\n"
        kb = []
        for tk in tickets:
            status_key = f"ticket_status_{tk['status']}"
            status_text = t(status_key, lang) if status_key in ["ticket_status_open",
                "ticket_status_answered", "ticket_status_closed"] else tk["status"]
            text += f"🎫 #{tk['id']} | {tk['subject'][:30]} | {status_text}\n"
            kb.append([btn(f"#{tk['id']} {tk['subject'][:20]}", f"ticket_view:{tk['id']}")])
        kb.append([btn(t("btn_back", lang), "support")])
        await edit(text, InlineKeyboardMarkup(kb))

    elif data == "faq_ok":
        context.user_data.pop("pending_ticket_text", None)
        context.user_data.pop("ticket_subject", None)
        db.log_event(uid, "faq_solved")
        await edit(t("faq_glad", lang), back_kb(lang))

    elif data == "faq_ticket":
        _txt = context.user_data.pop("pending_ticket_text", "")
        subject = context.user_data.pop("ticket_subject", "بدون موضوع")
        if not _txt:
            context.user_data["state"] = "ticket_subject"
            await edit(t("ticket_subject", lang), back_kb(lang, "support"))
            return
        tid = db.create_ticket(uid, subject, _txt)
        await edit(t("ticket_sent", lang, id=tid), back_kb(lang))
        await send_report(context, "tickets",
            f"🎫 تیکت جدید #{tid}\n👤 <code>{uid}</code>\n📌 {subject}\n📝 {_txt[:100]}")

    elif data.startswith("ticket_view:"):
        tid = int(data.split(":")[1])
        tk = db.get_ticket(tid)
        if not tk or (tk["user_id"] != uid and not is_admin(uid)):
            return
        status_map = {"open": t("ticket_status_open", lang),
                      "answered": t("ticket_status_answered", lang),
                      "closed": t("ticket_status_closed", lang)}
        reply_section = ""
        if tk["admin_reply"]:
            reply_section = t("ticket_reply_section", lang, reply=tk["admin_reply"])
        text = t("ticket_detail", lang, id=tk["id"], subject=tk["subject"],
                 status=status_map.get(tk["status"], tk["status"]),
                 message=tk["message"], reply_section=reply_section)
        kb = [[btn(t("btn_back", lang), "my_tickets")]]
        await edit(text, InlineKeyboardMarkup(kb))

    # ──── پنل ادمین ────
    elif data.startswith(("admin", "a_")) or data in (
            "a_settings", "a_lock", "a_admins", "a_payment_methods", "a_apis",
            "a_users", "a_tickets", "a_warranty"):
        if not is_admin(uid):
            await q.answer("⛔️", show_alert=True)
            return
        await admin_cb(update, context, data, lang)

# ═══════════ نمایش صفحه تأیید خرید ═══════════
async def show_confirm(q, context, uid, lang):
    p = db.get_product(context.user_data["buy_pid"])
    qty = context.user_data.get("buy_qty", 1)
    user = db.get_user(uid)
    d = context.user_data.get("discount")

    # محاسبه تخفیف نهایی — کد تخفیف اولویت دارد، سپس VIP
    if d:
        percent = d["percent"]
        discount_label = f" → <b>${round(p['price'] * (100 - percent) / 100, 2)}</b> (-{percent}% 🎟)"
    elif get_feature("vip_mode", "0") and db.is_vip(uid):
        try:
            percent = int(get_feature_value("vip_discount", "10"))
        except (TypeError, ValueError):
            percent = 10
        discount_label = f" → <b>${round(p['price'] * (100 - percent) / 100, 2)}</b> (-{percent}% 👑 VIP)"
    else:
        percent = 0
        discount_label = ""

    # تخفیف سطح کاربر
    level_disc = get_level_discount(uid)
    if level_disc and not percent:
        percent = level_disc
        discount_label = f" → <b>${round(p['price'] * (100 - percent) / 100, 2)}</b> (-{percent}% 🏅)"

    final = round(p["price"] * (100 - percent) / 100, 2)
    total = round(final * qty, 2)
    text = (f"{t('confirm_buy', lang)}\n\n📦 {p['name']} × {qty}\n"
            f"{t('price', lang)}: ${p['price']}{discount_label}"
            f"\n💵 مجموع: <b>${total}</b>"
            f"\n{t('your_balance', lang)}: ${user['balance']:.2f}")
    kb = [[btn(t("confirm", lang), "do_purchase")],
          [btn(t("apply_code", lang), "enter_discount")],
          [btn(t("cancel", lang), f"prod:{p['id']}")]]
    try:
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    except Exception:
        await q.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# ═══════════ پنل ادمین ═══════════
async def admin_cb(update, context, data, lang):
    q = update.callback_query
    uid = q.from_user.id
    # پنل ادمین از زبان کاربر پیروی می‌کند
    admin_lang = lang
    L_ = admin_lang  # shorthand

    async def edit(text, kb=None):
        try:
            await q.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass

    def back(target):
        return back_kb(L_, target)

    # ──── صفحه اصلی ادمین ────
    if data == "admin":
        s = db.get_stats()
        text = (t("adm_panel", L_) + "\n\n" +
                t("adm_users_lbl", L_, u=s['users'], b=s['blocked_users']) + "\n" +
                t("adm_orders_lbl", L_, o=s['orders'], t=s['today_orders']) + "\n" +
                t("adm_revenue_lbl", L_, r=s['revenue'], tr=s['today_revenue']) + "\n" +
                t("adm_deposits_lbl", L_, d=s['deposits']) + "\n" +
                t("adm_tickets_lbl", L_, n=s['pending_tickets']) + "\n" +
                t("adm_cards_lbl", L_, n=s['pending_cards']) + "\n" +
                t("adm_warranty_lbl", L_, n=s['pending_warranty']))
        _grid = get_button_layout("admin_panel", L_)
        _rows = []
        for _row in _grid:
            _out = [btn(_label, _ADMIN_PANEL_TARGETS[_key], _style, _icon) for _key, _label, _style, _icon in _row
                    if _key in _ADMIN_PANEL_TARGETS]
            if _out:
                _rows.append(_out)
        _rows.append([btn(t("btn_back", L_), "home")])
        kb = InlineKeyboardMarkup(_rows)
        await edit(text, kb)

    # ──── مدیریت محصولات ────
    elif data == "a_products":
        kb = InlineKeyboardMarkup([
            [btn(t("adm_btn_addcat", L_), "a_addcat"), btn(t("adm_btn_delcat", L_), "a_delcat")],
            [btn(t("adm_btn_addprod", L_), "a_addprod"), btn(t("adm_btn_delprod", L_), "a_delprod")],
            [btn(t("adm_btn_addstock", L_), "a_addstock"), btn(t("adm_btn_price", L_), "a_price")],
            [btn(t("adm_btn_editprod", L_), "a_editprod"), btn(t("adm_btn_banner", L_), "a_banner")],
            [btn(t("adm_btn_toggle", L_), "a_toggleprod"), btn(t("adm_btn_prodstats", L_), "a_prodstats")],
            [btn(t("btn_back", L_), "admin")]
        ])
        await edit(t("adm_products_title", L_), kb)

    elif data == "a_addcat":
        context.user_data["state"] = "a_addcat"
        await edit(t("adm_ask_cat_name", L_), back("a_products"))

    elif data == "a_delcat":
        cats = db.get_categories()
        if not cats:
            await edit(t("adm_no_cats", L_), back("a_products"))
            return
        kb = [[btn(f"🗑 {c['name']}", f"a_delcat_do:{c['id']}")] for c in cats]
        kb.append([btn(t("btn_back", L_), "a_products")])
        await edit(t("adm_ask_delcat", L_), InlineKeyboardMarkup(kb))

    elif data.startswith("a_delcat_do:"):
        db.delete_category(int(data.split(":")[1]))
        await edit(t("adm_cat_deleted", L_), back("a_products"))

    elif data == "a_addprod":
        cats = db.get_categories()
        if not cats:
            await edit(t("adm_no_cats", L_), back("a_products"))
            return
        kb = [[btn(c["name"], f"a_addprod_cat:{c['id']}")] for c in cats]
        kb.append([btn(t("btn_back", L_), "a_products")])
        await edit(t("adm_ask_which_cat", L_), InlineKeyboardMarkup(kb))

    elif data.startswith("a_addprod_cat:"):
        context.user_data["state"] = "a_addprod_name"
        context.user_data["cat_id"] = int(data.split(":")[1])
        context.user_data.pop("new_prod", None)
        await edit(t("adm_addprod_step1", L_), back("a_products"))

    elif data in ("a_delprod", "a_addstock", "a_price", "a_editprod",
                  "a_banner", "a_toggleprod"):
        prods = db.get_all_products()
        if not prods:
            await edit(t("adm_no_prods", L_), back("a_products"))
            return
        kb = []
        for p in prods:
            s = db.stock_count(p["id"])
            status = "✅" if p["active"] else "❌"
            kb.append([btn(f"{status} {p['name']} (${p['price']}|📦{s})",
                           f"{data}_p:{p['id']}")])
        kb.append([btn(t("btn_back", L_), "a_products")])
        await edit(t("adm_ask_which_prod", L_), InlineKeyboardMarkup(kb))

    elif data.startswith("a_delprod_p:"):
        db.delete_product(int(data.split(":")[1]))
        await edit(t("adm_prod_deleted", L_), back("a_products"))

    elif data.startswith("a_addstock_p:"):
        context.user_data["state"] = "a_addstock"
        context.user_data["prod_id"] = int(data.split(":")[1])
        await edit(t("adm_ask_stock", L_), back("a_products"))

    elif data.startswith("a_price_p:"):
        context.user_data["state"] = "a_price"
        context.user_data["prod_id"] = int(data.split(":")[1])
        await edit(t("adm_ask_price", L_), back("a_products"))

    elif data.startswith("a_editprod_p:"):
        pid = int(data.split(":")[1])
        p = db.get_product(pid)
        context.user_data["state"] = "a_editprod"
        context.user_data["prod_id"] = pid
        await edit(t("adm_ask_editprod", L_, name=p['name']), back("a_products"))

    elif data.startswith("a_banner_p:"):
        pid = int(data.split(":")[1])
        context.user_data["state"] = "a_banner"
        context.user_data["prod_id"] = pid
        await edit(t("adm_ask_banner", L_), back("a_products"))

    elif data.startswith("a_toggleprod_p:"):
        pid = int(data.split(":")[1])
        active = db.toggle_product_active(pid)
        msg = t("adm_prod_toggled_on", L_) if active else t("adm_prod_toggled_off", L_)
        await edit(msg, back("a_products"))

    elif data == "a_prodstats":
        prods = db.get_all_products()
        text = t("adm_prodstats_title", L_) + "\n\n"
        for p in prods:
            s = db.stock_count(p["id"])
            status = t("adm_active", L_) if p["active"] else t("adm_inactive", L_)
            text += t("adm_prodstats_row", L_, name=p['name'], price=p['price'],
                      stock=s, sold=p['sold'], status=status)
        await edit(text or t("adm_no_prods", L_), back("a_products"))

    # ──── مدیریت کاربران ────
    elif data == "a_users":
        s = db.get_stats()
        text = t("adm_users_title", L_, total=s['users'], blocked=s['blocked_users'])
        kb = InlineKeyboardMarkup([
            [btn(t("adm_btn_userinfo", L_), "a_userinfo"), btn(t("adm_btn_addbal", L_), "a_addbal")],
            [btn(t("adm_btn_block", L_), "a_block"), btn(t("adm_btn_usernote", L_), "a_usernote")],
            [btn(t("adm_btn_userlist", L_), "a_userlist"), btn(t("adm_btn_userstats", L_), "a_userstats")],
            [btn(t("adm_btn_vip", L_), "a_vip")],
            [btn(t("btn_back", L_), "admin")]
        ])
        await edit(text, kb)

    elif data == "a_vip":
        context.user_data["state"] = "a_vip"
        await edit(t("adm_ask_vip", L_), back("a_users"))

    elif data == "a_userinfo":
        context.user_data["state"] = "a_userinfo"
        await edit(t("adm_ask_userinfo", L_), back("a_users"))

    elif data == "a_addbal":
        context.user_data["state"] = "a_addbal"
        await edit(t("adm_ask_addbal", L_), back("a_users"))

    elif data == "a_block":
        context.user_data["state"] = "a_block"
        await edit(t("adm_ask_block", L_), back("a_users"))

    elif data == "a_usernote":
        context.user_data["state"] = "a_usernote_id"
        await edit(t("adm_ask_usernote_id", L_), back("a_users"))

    elif data == "a_userlist":
        users = db.get_all_users_paginated(0, 15)
        text = t("adm_userlist_title", L_) + "\n\n"
        for u in users:
            text += f"👤 <code>{u['user_id']}</code> | @{u['username'] or 'N/A'} | {u['lang'] or '?'}\n"
        await edit(text, back("a_users"))

    elif data == "a_userstats":
        context.user_data["state"] = "a_userstats"
        await edit(t("adm_ask_userstats", L_), back("a_users"))

    # ──── کدهای تخفیف ────
    elif data == "a_codes":
        codes = db.all_discounts()
        text = t("adm_codes_title", L_) + "\n\n" + ("\n".join(
            f"🔹 <code>{c['code']}</code> | {c['percent']}% | {c['used']}/{c['max_uses']}"
            for c in codes) if codes else t("adm_codes_empty", L_))
        kb = [[btn(f"🗑 {c['code']}", f"a_delcode:{c['code']}")] for c in codes]
        kb.append([btn(t("adm_btn_addcode", L_), "a_addcode")])
        kb.append([btn(t("btn_back", L_), "admin")])
        await edit(text, InlineKeyboardMarkup(kb))

    elif data == "a_addcode":
        context.user_data["state"] = "a_addcode"
        await edit(t("adm_ask_addcode", L_), back("a_codes"))

    elif data.startswith("a_delcode:"):
        db.delete_discount(data.split(":")[1])
        await edit(t("adm_code_deleted", L_), back("a_codes"))

    # ──── پرداخت‌های کارتی ────
    elif data == "a_cards":
        payments = db.get_pending_card_payments()
        if not payments:
            await edit(t("adm_no_cards", L_), back("admin"))
            return
        text = t("adm_cards_title", L_, n=len(payments)) + "\n\n"
        for p in payments:
            text += (f"#{p['id']} | 👤 <code>{p['user_id']}</code> @{p['username'] or 'N/A'}\n"
                     f"   💵 ${p['amount']} | 📅 {p['created_at'][:10]}\n\n")
        await edit(text, back("admin"))

    # ──── تیکت‌ها ────
    elif data == "a_tickets":
        tickets = db.get_tickets(status="open")
        if not tickets:
            await edit(t("adm_no_tickets", L_), back("admin"))
            return
        text = t("adm_tickets_title", L_, n=len(tickets)) + "\n\n"
        kb = []
        for tk in tickets:
            text += f"#{tk['id']} | @{tk['username'] or 'N/A'} | {tk['subject'][:30]}\n"
            kb.append([btn(f"#{tk['id']} {tk['subject'][:25]}", f"a_ticket_view:{tk['id']}")])
        kb.append([btn(t("btn_back", L_), "admin")])
        await edit(text, InlineKeyboardMarkup(kb))

    elif data.startswith("a_ticket_view:"):
        tid = int(data.split(":")[1])
        tk = db.get_ticket(tid)
        if not tk:
            await edit(t("adm_ticket_not_found", L_), back("a_tickets"))
            return
        reply_part = t("adm_ticket_prev_reply", L_, reply=tk["admin_reply"]) if tk["admin_reply"] else ""
        text = t("adm_ticket_detail", L_, id=tk['id'], username=tk['username'] or 'N/A',
                 uid=tk['user_id'], subject=tk['subject'], status=tk['status'],
                 message=tk['message'], reply=reply_part)
        kb = InlineKeyboardMarkup([
            [btn(t("adm_btn_reply", L_), f"a_ticket_reply:{tid}"),
             btn(t("adm_btn_close_ticket", L_), f"a_ticket_close:{tid}")],
            [btn(t("btn_back", L_), "a_tickets")]
        ])
        await edit(text, kb)

    elif data.startswith("a_ticket_reply:"):
        tid = int(data.split(":")[1])
        context.user_data["state"] = "a_ticket_reply"
        context.user_data["ticket_id"] = tid
        await edit(t("adm_ask_ticket_reply", L_, id=tid), back(f"a_ticket_view:{tid}"))

    elif data.startswith("a_ticket_close:"):
        tid = int(data.split(":")[1])
        db.close_ticket(tid)
        await edit(t("adm_ticket_closed", L_), back("a_tickets"))

    # ──── گارانتی‌ها ────
    elif data == "a_warranty":
        claims = db.get_warranty_claims(status="pending")
        if not claims:
            await edit(t("adm_no_warranty", L_), back("admin"))
            return
        text = t("adm_warranty_title", L_, n=len(claims)) + "\n\n"
        kb = []
        for c in claims:
            text += (f"#{c['id']} | 👤 <code>{c['user_id']}</code>\n"
                     f"   📦 {c['product_name']} | 💵 ${c['order_price']}\n"
                     f"   📝 {c['reason'][:50]}\n\n")
            kb.append([
                btn(f"✅ #{c['id']}", f"wapprove:{c['id']}"),
                btn(f"❌ #{c['id']}", f"wreject:{c['id']}")
            ])
        kb.append([btn(t("btn_back", L_), "admin")])
        await edit(text, InlineKeyboardMarkup(kb))

    # ──── قفل گروه/کانال ────
    elif data == "a_lock":
        locked_ch = db.get_locked_channels()
        locked_gr = db.get_locked_groups()
        text = t("adm_lock_title", L_, ch=len(locked_ch), gr=len(locked_gr)) + "\n\n"
        if locked_ch:
            text += t("adm_locked_channels", L_) + "\n" + "\n".join(
                f"  • {c['title']} (<code>{c['channel_id']}</code>)" for c in locked_ch) + "\n\n"
        if locked_gr:
            text += t("adm_locked_groups", L_) + "\n" + "\n".join(
                f"  • {g['title']} (<code>{g['group_id']}</code>)" for g in locked_gr)
        kb = InlineKeyboardMarkup([
            [btn(t("adm_btn_lock_ch", L_), "a_lock_channel"), btn(t("adm_btn_unlock_ch", L_), "a_unlock_channel")],
            [btn(t("adm_btn_lock_gr", L_), "a_lock_group"), btn(t("adm_btn_unlock_gr", L_), "a_unlock_group")],
            [btn(t("btn_back", L_), "admin")]
        ])
        await edit(text, kb)

    elif data == "a_lock_channel":
        context.user_data["state"] = "a_lock_channel"
        await edit(t("adm_ask_lock_ch", L_), back("a_lock"))

    elif data == "a_unlock_channel":
        channels = db.get_locked_channels()
        if not channels:
            await edit(t("adm_no_locked_ch", L_), back("a_lock"))
            return
        kb = [[btn(f"🔓 {c['title']}", f"a_unlock_ch_do:{c['channel_id']}")] for c in channels]
        kb.append([btn(t("btn_back", L_), "a_lock")])
        await edit(t("adm_ask_unlock_ch", L_), InlineKeyboardMarkup(kb))

    elif data.startswith("a_unlock_ch_do:"):
        db.unlock_channel(int(data.split(":")[1]))
        await edit(t("adm_ch_unlocked", L_), back("a_lock"))

    elif data == "a_lock_group":
        context.user_data["state"] = "a_lock_group"
        await edit(t("adm_ask_lock_gr", L_), back("a_lock"))

    elif data == "a_unlock_group":
        groups = db.get_locked_groups()
        if not groups:
            await edit(t("adm_no_locked_gr", L_), back("a_lock"))
            return
        kb = [[btn(f"🔓 {g['title']}", f"a_unlock_gr_do:{g['group_id']}")] for g in groups]
        kb.append([btn(t("btn_back", L_), "a_lock")])
        await edit(t("adm_ask_unlock_gr", L_), InlineKeyboardMarkup(kb))

    elif data.startswith("a_unlock_gr_do:"):
        db.unlock_group(int(data.split(":")[1]))
        await edit(t("adm_gr_unlocked", L_), back("a_lock"))

    # ──── مدیریت ادمین‌ها ────
    elif data == "a_admins":
        admins = db.get_all_admins()
        text = t("adm_admins_title", L_) + "\n\n"
        for a in admins:
            role = t("adm_super", L_) if a['is_super'] else t("adm_regular", L_)
            text += f"👤 <code>{a['user_id']}</code> | {role} | {t('adm_perm_lbl', L_)}: {a['permissions']}\n"
        kb = InlineKeyboardMarkup([
            [btn(t("adm_btn_addadmin", L_), "a_addadmin"), btn(t("adm_btn_deladmin", L_), "a_deladmin")],
            [btn(t("adm_btn_editadmin", L_), "a_editadmin")],
            [btn(t("btn_back", L_), "admin")]
        ])
        await edit(text or t("adm_no_admins", L_), kb)

    elif data == "a_addadmin":
        context.user_data["state"] = "a_addadmin"
        await edit(t("adm_ask_addadmin", L_), back("a_admins"))

    elif data == "a_deladmin":
        admins = db.get_all_admins()
        if not admins:
            await edit(t("adm_no_admins", L_), back("a_admins"))
            return
        kb = [[btn(f"🗑 {a['user_id']}", f"a_deladmin_do:{a['user_id']}")] for a in admins]
        kb.append([btn(t("btn_back", L_), "a_admins")])
        await edit(t("adm_ask_deladmin", L_), InlineKeyboardMarkup(kb))

    elif data.startswith("a_deladmin_do:"):
        target_id = int(data.split(":")[1])
        if target_id in ADMIN_IDS:
            await edit(t("adm_cant_del_main", L_), back("a_admins"))
            return
        db.delete_admin(target_id)
        await edit(t("adm_admin_deleted", L_), back("a_admins"))

    elif data == "a_editadmin":
        context.user_data["state"] = "a_editadmin"
        await edit(t("adm_ask_editadmin", L_), back("a_admins"))

    # ──── متدهای پرداخت ────
    elif data == "a_payment_methods":
        methods = db.get_payment_methods(only_active=False)
        text = t("adm_payment_title", L_) + "\n\n"
        for m in methods:
            text += f"{'✅' if m['active'] else '❌'} <b>{m['name']}</b>: {m['details']}\n"
        kb = InlineKeyboardMarkup([
            [btn(t("adm_btn_addmethod", L_), "a_addpaymethod"), btn(t("adm_btn_delmethod", L_), "a_delpaymethod")],
            [btn(t("adm_btn_togglemethod", L_), "a_togglepaymethod")],
            [btn(t("adm_btn_setcard", L_), "a_setcard"), btn(t("adm_btn_setwallet", L_), "a_setwallet")],
            [btn(t("btn_back", L_), "admin")]
        ])
        await edit(text or t("adm_no_methods", L_), kb)

    elif data == "a_addpaymethod":
        context.user_data["state"] = "a_addpaymethod"
        await edit(t("adm_ask_addmethod", L_), back("a_payment_methods"))

    elif data == "a_delpaymethod":
        methods = db.get_payment_methods(only_active=False)
        if not methods:
            await edit(t("adm_no_methods", L_), back("a_payment_methods"))
            return
        kb = [[btn(f"🗑 {m['name']}", f"a_delpaymethod_do:{m['id']}")] for m in methods]
        kb.append([btn(t("btn_back", L_), "a_payment_methods")])
        await edit(t("adm_ask_delmethod", L_), InlineKeyboardMarkup(kb))

    elif data.startswith("a_delpaymethod_do:"):
        db.delete_payment_method(int(data.split(":")[1]))
        await edit(t("adm_method_deleted", L_), back("a_payment_methods"))

    elif data == "a_togglepaymethod":
        methods = db.get_payment_methods(only_active=False)
        if not methods:
            await edit(t("adm_no_methods", L_), back("a_payment_methods"))
            return
        kb = [[btn(f"{'✅' if m['active'] else '❌'} {m['name']}",
                   f"a_togglepaymethod_do:{m['id']}")] for m in methods]
        kb.append([btn(t("btn_back", L_), "a_payment_methods")])
        await edit(t("adm_ask_togglemethod", L_), InlineKeyboardMarkup(kb))

    elif data.startswith("a_togglepaymethod_do:"):
        mid = int(data.split(":")[1])
        m = db.get_payment_method(mid)
        if m:
            db.update_payment_method(mid, active=0 if m["active"] else 1)
        await edit(t("adm_method_toggled", L_), back("a_payment_methods"))

    elif data == "a_setcard":
        context.user_data["state"] = "a_setcard"
        await edit(t("adm_ask_setcard", L_, card=get_card_number(), holder=get_card_holder()),
                   back("a_payment_methods"))

    elif data == "a_setwallet":
        context.user_data["state"] = "a_setwallet"
        await edit(t("adm_ask_setwallet", L_, wallet=get_usdt_wallet()), back("a_payment_methods"))

    # ──── API ها ────
    elif data == "a_apis":
        apis = db.get_all_settings()
        api_keys = {k: v for k, v in apis.items() if k.startswith("api_")}
        text = t("adm_apis_title", L_) + "\n\n"
        if api_keys:
            for k, v in api_keys.items():
                text += f"🔹 <code>{k}</code>: {v[:30]}...\n"
        else:
            text += t("adm_no_apis", L_) + "\n"
        text += "\n" + t("adm_ext_apis", L_) + "\n"
        for name, info in EXTERNAL_APIS.items():
            text += f"  • {name}: {info.get('url', '')[:40]}\n"
        kb = InlineKeyboardMarkup([
            [btn(t("adm_btn_addapi", L_), "a_addapi"), btn(t("adm_btn_delapi", L_), "a_delapi")],
            [btn(t("adm_btn_testapi", L_), "a_testapi")],
            [btn(t("btn_back", L_), "admin")]
        ])
        await edit(text, kb)

    elif data == "a_addapi":
        context.user_data["state"] = "a_addapi"
        await edit(t("adm_ask_addapi", L_), back("a_apis"))

    elif data == "a_delapi":
        apis = {k: v for k, v in db.get_all_settings().items() if k.startswith("api_")}
        if not apis:
            await edit(t("adm_no_apis", L_), back("a_apis"))
            return
        kb = [[btn(f"🗑 {k}", f"a_delapi_do:{k}")] for k in apis]
        kb.append([btn(t("btn_back", L_), "a_apis")])
        await edit(t("adm_ask_delapi", L_), InlineKeyboardMarkup(kb))

    elif data.startswith("a_delapi_do:"):
        key = data.split(":", 1)[1]
        db.set_setting(key, "")
        await edit(t("adm_api_deleted", L_), back("a_apis"))

    elif data == "a_testapi":
        rate = await get_usd_rate_async()
        await edit(t("adm_testapi_result", L_, rate=rate), back("a_apis"))

    # ──── تنظیمات ────
    elif data == "a_settings":
        feature_keys = [("referral", "1"), ("card_iranian_only", "1"), ("automatic_card_confirm", "0"),
                        ("usd_rate", "1"), ("tickets", "1"), ("warranty", "1"), ("lock_groups", "1"),
                        ("lock_channels", "1"), ("multi_admin", "1"), ("maintenance_mode", "0"),
                        ("registration_locked", "0"), ("daily_purchase_limit", "0"), ("vip_mode", "0")]
        text = t("adm_settings_title", L_) + "\n\n"
        kb = []
        for key, default in feature_keys:
            active = get_feature(key, default)
            name = t_feature(key, L_)
            text += f"{'✅' if active else '❌'} {name}\n"
            kb.append([btn(f"{'✅' if active else '❌'} {name}", f"a_toggle_feature:{key}")])
        kb.append([btn(t("btn_back", L_), "admin")])
        await edit(text, InlineKeyboardMarkup(kb))

    elif data.startswith("a_toggle_feature:"):
        key = data.split(":")[1]
        toggle_defaults = {"maintenance_mode": "0", "registration_locked": "0",
                          "daily_purchase_limit": "0", "vip_mode": "0", "automatic_card_confirm": "0"}
        current = get_feature(key, toggle_defaults.get(key, "1"))
        db.set_setting(f"feature_{key}", "0" if current else "1")
        msg = t("adm_feature_toggled_off", L_) if current else t("adm_feature_toggled_on", L_)
        await edit(msg, back("a_settings"))

    # ──── تأیید گارانتی محصول (از طریق دکمه inline) ────
    elif data in ("a_addprod_warranty_yes", "a_addprod_warranty_no"):
        has_warranty = 1 if data == "a_addprod_warranty_yes" else 0
        np = context.user_data.get("new_prod", {})
        cat_id = context.user_data.get("cat_id")
        context.user_data.pop("state", None)
        pid = db.add_product(cat_id, np.get("name", ""), np.get("price", 0),
                             np.get("desc", ""), np.get("features", ""), has_warranty)
        context.user_data.pop("new_prod", None)
        warranty_text = t("adm_warranty_has", L_) if has_warranty else t("adm_warranty_none", L_)
        kb = InlineKeyboardMarkup([
            [btn(t("adm_btn_addstock_now", L_), f"a_addstock_p:{pid}")],
            [btn(t("btn_back", L_), "a_products")]
        ])
        await edit(t("adm_prod_added", L_, pid=pid, name=np.get("name", ""),
                     price=np.get("price", 0), warranty=warranty_text), kb)
        await broadcast_new_product(context, np.get("name", ""), np.get("price", 0))

    # ──── پیام همگانی ────
    elif data == "a_broadcast":
        context.user_data["state"] = "a_broadcast"
        await edit(t("adm_ask_broadcast", L_), back("admin"))

# ═══════════ اطلاع‌رسانی محصول جدید ═══════════
async def broadcast_new_product(context, name, price):
    """ارسال اطلاع‌رسانی محصول جدید با رعایت rate limit تلگرام (۵۰ms بین هر پیام)"""
    from telegram.error import RetryAfter
    for u in db.all_users():
        for _attempt in range(2):
            try:
                await context.bot.send_message(
                    u["user_id"],
                    t("new_product", u["lang"] or "fa", name=name, price=price),
                    parse_mode="HTML")
                break
            except RetryAfter as e:
                await asyncio.sleep(float(getattr(e, "retry_after", 3)) + 1)
            except Exception:
                break
        await asyncio.sleep(0.05)  # جلوگیری از 429 Too Many Requests

# ═══════════ پیام‌های متنی ═══════════
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    user = db.get_user(uid)
    if not user:
        db.add_user(uid, update.effective_user.username or "")
        user = db.get_user(uid)
    if user["blocked"] and not is_admin(uid):
        return
    lang = user["lang"] or "fa"

    # Premium-emoji helper: when an admin sends a premium emoji, reply with a ready-to-copy code
    if is_admin(uid) and update.message.entities:
        _codes = []
        for _e in update.message.entities:
            if getattr(_e, "custom_emoji_id", None):
                _fb = update.message.parse_entity(_e)
                _codes.append(f"<code>[emoji:{_e.custom_emoji_id}:{_fb}]</code>")
        if _codes:
            _head = ("🧩 کد ایموجی پرمیوم — این کد را در متن‌ها یا لیبل دکمه‌ها قرار دهید:"
                     if lang == "fa" else
                     "🧩 Premium emoji code — paste it into texts or button labels:")
            await update.message.reply_text(_head + "\n" + "\n".join(_codes), parse_mode="HTML")
            return

    if maintenance_active() and not is_admin(uid):
        await update.message.reply_text(get_maintenance_text(lang), parse_mode="HTML")
        return

    state = context.user_data.get("state")

    # ──── دکمه‌های کیبورد پایین ────
    _kb_targets = {"kb_start": "home", "kb_products": "browse",
                   "kb_support": "support", "kb_lang": "lang"}
    kb_map = {}
    for key, target in _kb_targets.items():
        for lg in ("fa", "en"):
            kb_map[t(key, lg)] = target
    for _row in get_button_layout("main_reply", lang):
        for _key, _label, _style, _icon in _row:
            _t = _kb_targets.get(_key)
            if _t:
                kb_map[_label] = _t
    if text in kb_map:
        context.user_data.pop("state", None)
        target = kb_map[text]
        if target == "home":
            await update.message.reply_text(get_welcome_text(lang),
                reply_markup=main_menu(uid, lang), parse_mode="HTML")
        elif target == "browse":
            cats = db.get_categories()
            kb = [[btn(f"🗂 {c['name']}", f"cat:{c['id']}")] for c in cats]
            kb.append([btn(t("btn_back", lang), "home")])
            await update.message.reply_text(
                t("pick_cat", lang) if cats else t("no_products", lang),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        elif target == "support":
            kb = []
            if get_feature("tickets"):
                kb.append([btn(t("btn_tickets", lang), "my_tickets")])
                kb.append([btn(t("btn_new_ticket", lang), "new_ticket")])
            kb.append([btn(t("btn_back", lang), "home")])
            await update.message.reply_text(
                t("support_text", lang, s=get_support_username()),
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        elif target == "lang":
            await update.message.reply_text(t("choose_lang", lang), reply_markup=lang_kb())
        return

    if not state:
        # ──── ضداسپم ────
        if not is_admin(uid) and _spam_hit(uid):
            return
        # ──── دستورهای سفارشی ────
        try:
            for cc in _get_custom_commands_cached():
                if text.strip() == (cc["trigger"] or "").strip():
                    await update.message.reply_text(render_premium_emoji(cc["response"]),
                                                    parse_mode="HTML")
                    return
        except Exception:
            pass
        return

    # ──── کپچا ────
    if state == "captcha":
        if text.strip() == context.user_data.get("captcha_answer"):
            context.user_data.pop("state", None)
            context.user_data.pop("captcha_answer", None)
            # ذخیره در bot_data (حافظه) به جای settings دیتابیس
            _captcha_passed = context.bot_data.setdefault("captcha_ok", set())
            _captcha_passed.add(uid)
            await update.message.reply_text(t("captcha_ok", lang))
        else:
            await update.message.reply_text(t("captcha_bad", lang))
        return

    # ──── تعداد خرید ────
    if state == "await_qty":
        pid = context.user_data.get("buy_pid")
        s = db.stock_count(pid)
        try:
            qty = int(text)
            assert 1 <= qty <= s
        except (ValueError, AssertionError):
            await update.message.reply_text(t("qty_invalid", lang))
            return
        context.user_data["buy_qty"] = qty
        context.user_data.pop("state")

        await show_confirm(_FakeQ(update.message), context, uid, lang)
        return

    # ──── کد تخفیف ────
    if state == "await_discount":
        context.user_data.pop("state")
        d = db.get_discount(text, context.user_data.get("buy_pid"))
        if d:
            context.user_data["discount"] = dict(d)
            await update.message.reply_text(t("code_ok", lang))
        else:
            await update.message.reply_text(t("code_bad", lang))

        await show_confirm(_FakeQ(update.message), context, uid, lang)
        return

    # ──── هش USDT ────
    if state == "await_tx":
        context.user_data.pop("state")
        h = text.lower()
        if not h.startswith("0x"):
            h = "0x" + h
        if len(h) != 66:
            await update.message.reply_text(t("tx_bad_format", lang))
            return
        if db.tx_exists(h):
            await update.message.reply_text(t("tx_used", lang))
            return
        msg = await update.message.reply_text(t("checking", lang))
        loop = asyncio.get_running_loop()
        ok, result = await loop.run_in_executor(None, verify_usdt_bep20, h)
        if ok:
            db.save_tx(uid, h, result)
            bonus = apply_deposit_bonus(uid, result)
            await pay_referral(context, uid, result)
            u2 = db.get_user(uid)
            extra = f"\n🎁 بونوس: +${bonus:.2f}" if bonus else ""
            await msg.edit_text(f"{t('tx_ok', lang)}\n\n💰 +${result:.2f}{extra}\n"
                                f"{t('your_balance', lang)}: ${u2['balance']:.2f}",
                                parse_mode="HTML")
            await send_report(context, "deposits",
                f"💎 واریز USDT!\n👤 <code>{uid}</code>\n💵 ${result}")
            await _maybe_big_deposit_alert(context, uid, result)
        else:
            await msg.edit_text(result)
        return

    # ──── هش USDT TRC20 ────
    if state == "await_tx_trc20":
        context.user_data.pop("state")
        h = text.strip()
        if h.startswith("0x"):
            h = h[2:]
        if len(h) != 64 or not all(c in "0123456789abcdefABCDEF" for c in h):
            await update.message.reply_text(t("tx_bad_format", lang))
            return
        if db.tx_exists(h):
            await update.message.reply_text(t("tx_used", lang))
            return
        msg = await update.message.reply_text(t("checking", lang))
        loop = asyncio.get_running_loop()
        ok, result = await loop.run_in_executor(None, verify_usdt_trc20, h)
        if ok:
            db.save_tx(uid, h, result, "usdt_trc20")
            bonus = apply_deposit_bonus(uid, result)
            await pay_referral(context, uid, result)
            u2 = db.get_user(uid)
            extra = f"\n🎁 بونوس: +${bonus:.2f}" if bonus else ""
            await msg.edit_text(f"{t('tx_ok', lang)}\n\n💰 +${result:.2f}{extra}\n"
                                f"{t('your_balance', lang)}: ${u2['balance']:.2f}", parse_mode="HTML")
            await send_report(context, "deposits",
                f"💎 واریز USDT (TRC20)!\n👤 <code>{uid}</code>\n💵 ${result}")
            await _maybe_big_deposit_alert(context, uid, result)
        else:
            await msg.edit_text(result)
        return

    # ──── مبلغ استارز ────
    if state == "await_stars_amount":
        try:
            usd = float(text)
            assert usd > 0
        except (ValueError, AssertionError):
            await update.message.reply_text(t("tx_bad_format", lang))
            return
        context.user_data.pop("state")
        per = float(db.get_setting("stars_per_usd", "50") or 50)
        stars = max(1, int(round(usd * per)))
        try:
            await context.bot.send_invoice(
                chat_id=uid, title=t("stars_invoice_title", lang),
                description=t("stars_invoice_desc", lang, a=usd),
                payload=f"stars:{uid}:{usd}", provider_token="",
                currency="XTR", prices=[LabeledPrice(label=f"${usd:.2f}", amount=stars)])
        except Exception as e:
            await update.message.reply_text(f"❌ {e}")
        return

    # ──── مبلغ زرین‌پال ────
    if state == "await_zp_amount":
        try:
            usd = float(text)
            min_dep = float(db.get_setting("min_deposit", MIN_DEPOSIT))
            assert usd >= min_dep
        except (ValueError, AssertionError):
            await update.message.reply_text(t("tx_bad_format", lang))
            return
        context.user_data.pop("state")
        rate = await get_usd_rate_async() if get_feature("usd_rate") else USD_TO_TOMAN
        toman = int(usd * rate)
        loop = asyncio.get_running_loop()
        link, err = await loop.run_in_executor(None, zarinpal_request, toman, uid, usd)
        if link:
            await update.message.reply_text(
                t("zp_pay_link", lang, a=usd, t=toman),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(t("zp_pay_btn", lang), url=link)]]),
                parse_mode="HTML")
        else:
            await update.message.reply_text(t("zp_error", lang, e=err or ""))
        return

    # ──── مبلغ کارت به کارت ────
    if state == "await_card_amount":
        if get_feature("card_iranian_only") and lang != "fa":
            await update.message.reply_text(t("card_only_fa", lang))
            return
        try:
            amount = float(text)
            min_dep = float(db.get_setting("min_deposit", MIN_DEPOSIT))
            max_dep = float(db.get_setting("max_deposit", 0) or 0)
            assert amount >= min_dep
            assert not (max_dep and amount > max_dep)
        except (ValueError, AssertionError):
            await update.message.reply_text(t("tx_bad_format", lang))
            return
        context.user_data["state"] = "await_card_photo"
        context.user_data["card_amount"] = amount
        rate = await get_usd_rate_async() if get_feature("usd_rate") else USD_TO_TOMAN
        toman = int(amount * rate)
        await update.message.reply_text(t("card_send_photo", lang, a=amount, t=toman),
                                        parse_mode="HTML")
        return

    # ──── موضوع تیکت ────
    if state == "ticket_subject":
        context.user_data["ticket_subject"] = text
        context.user_data["state"] = "ticket_message"
        await update.message.reply_text(t("ticket_message", lang))
        return

    # ──── پیام تیکت ────
    if state == "ticket_message":
        context.user_data.pop("state")
        # ── پیشنهاد خودکار FAQ قبل از ثبت تیکت ──
        try:
            _matches = db.match_faqs(
                f"{context.user_data.get('ticket_subject', '')} {text}", lang) \
                if db.get_setting("faq_suggest", "1") == "1" else []
        except Exception:
            _matches = []
        if _matches:
            context.user_data["pending_ticket_text"] = text
            _body = t("faq_suggest", lang) + "\n"
            for _f in _matches:
                _body += f"\n<b>❓ {_f['question']}</b>\n{_f['answer']}\n"
            await update.message.reply_text(_body[:4000], parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [btn(t("faq_solved", lang), "faq_ok")],
                    [btn(t("faq_not_solved", lang), "faq_ticket")]]))
            return
        subject = context.user_data.pop("ticket_subject", "بدون موضوع")
        tid = db.create_ticket(uid, subject, text)
        await update.message.reply_text(t("ticket_sent", lang, id=tid))
        # اطلاع به ادمین‌ها / گروه گزارشات
        await send_report(context, "tickets",
            f"🎫 تیکت جدید #{tid}\n👤 <code>{uid}</code> @{update.effective_user.username or 'N/A'}\n"
            f"📌 {subject}\n📝 {text[:100]}")
        return

    # ──── دلیل گارانتی ────
    if state == "await_warranty_reason":
        oid = context.user_data.pop("warranty_order_id", None)
        context.user_data.pop("state")
        if oid:
            cid = db.create_warranty_claim(uid, oid, text)
            await update.message.reply_text(t("warranty_submitted", lang))
            await send_report(context, "warranty",
                f"🛡 درخواست گارانتی #{cid}\n👤 <code>{uid}</code>\n"
                f"📦 سفارش #{oid}\n📝 {text[:100]}")
        return

    # ═══ بخش‌های ادمین ═══
    if not is_admin(uid):
        return

    # ──── افزودن محصول مرحله به مرحله (state را پاک نمی‌کنیم تا مراحل بعدی کار کنند) ────
    if state == "a_addprod_name":
        context.user_data.setdefault("new_prod", {})["name"] = text
        context.user_data["state"] = "a_addprod_price"
        await update.message.reply_text(t("adm_addprod_step2", lang), parse_mode="HTML")
        return

    elif state == "a_addprod_price":
        try:
            price = float(text)
            assert price > 0
        except (ValueError, AssertionError):
            await update.message.reply_text(t("adm_invalid_price", lang))
            return
        context.user_data.setdefault("new_prod", {})["price"] = price
        context.user_data["state"] = "a_addprod_desc"
        await update.message.reply_text(t("adm_addprod_step3", lang), parse_mode="HTML")
        return

    elif state == "a_addprod_desc":
        context.user_data.setdefault("new_prod", {})["desc"] = text
        context.user_data["state"] = "a_addprod_features"
        await update.message.reply_text(t("adm_addprod_step4", lang), parse_mode="HTML")
        return

    elif state == "a_addprod_features":
        features = "" if text.strip() == "-" else text
        context.user_data.setdefault("new_prod", {})["features"] = features
        context.user_data["state"] = "a_addprod_warranty"
        await update.message.reply_text(
            t("adm_addprod_step5", lang),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [btn(t("adm_warranty_yes", lang), "a_addprod_warranty_yes"),
                 btn(t("adm_warranty_no", lang), "a_addprod_warranty_no")]
            ]))
        return

    elif state == "a_addprod_warranty":
        has_warranty = 1 if text.strip() in ("بله", "yes", "1", "y") else 0
        np = context.user_data.get("new_prod", {})
        cat_id = context.user_data.get("cat_id")
        pid = db.add_product(cat_id, np.get("name", ""), np.get("price", 0),
                             np.get("desc", ""), np.get("features", ""), has_warranty)
        context.user_data.pop("new_prod", None)
        context.user_data.pop("state", None)
        warranty_text = t("adm_warranty_has", lang) if has_warranty else t("adm_warranty_none", lang)
        kb = InlineKeyboardMarkup([
            [btn(t("adm_btn_addstock_now", lang), f"a_addstock_p:{pid}")],
            [btn(t("btn_back", lang), "a_products")]
        ])
        await update.message.reply_text(
            t("adm_prod_added", lang, pid=pid, name=np.get("name", ""),
              price=np.get("price", 0), warranty=warranty_text),
            parse_mode="HTML", reply_markup=kb)
        await broadcast_new_product(context, np.get("name", ""), np.get("price", 0))
        return

    # برای state هایی که نیاز به retry دارند، state را پاک نمی‌کنیم تا کاربر بتواند دوباره تلاش کند
    # فقط بعد از موفقیت state پاک می‌شود

    if state == "a_addcat":
        context.user_data.pop("state", None)
        db.add_category(text)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_products")]])
        await update.message.reply_text(t("adm_cat_added", lang), reply_markup=kb)

    elif state == "a_editprod":
        pid = context.user_data.get("prod_id")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) < 3:
            await update.message.reply_text(t("adm_invalid_format", lang))
            return
        try:
            price = float(lines[1])
        except ValueError:
            await update.message.reply_text(t("adm_invalid_price", lang))
            return
        context.user_data.pop("state", None)
        features = "\n".join(lines[3:]) if len(lines) > 3 else ""
        db.update_product(pid, name=lines[0], price=price,
                          description=lines[2], features=features)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_products")]])
        await update.message.reply_text(t("adm_prod_edited", lang), reply_markup=kb)

    elif state == "a_banner":
        context.user_data.pop("state", None)
        pid = context.user_data.get("prod_id")
        db.update_product(pid, banner_url=text)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_products")]])
        await update.message.reply_text(t("adm_banner_set", lang), reply_markup=kb)

    elif state == "a_addstock":
        context.user_data.pop("state", None)
        items = text.split("\n")
        count = len([i for i in items if i.strip()])
        db.add_stock(context.user_data["prod_id"], items)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_products")]])
        await update.message.reply_text(t("adm_stock_added", lang, n=count), reply_markup=kb)

    elif state == "a_price":
        try:
            price_val = float(text)
            assert price_val > 0
        except (ValueError, AssertionError):
            await update.message.reply_text(t("adm_invalid_price", lang))
            return
        context.user_data.pop("state", None)
        db.update_price(context.user_data["prod_id"], price_val)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_products")]])
        await update.message.reply_text(t("adm_price_updated", lang), reply_markup=kb)

    elif state == "a_addcode":
        try:
            parts = text.split()
            code, percent, uses = parts[0], int(parts[1]), int(parts[2])
        except (ValueError, IndexError):
            await update.message.reply_text(t("adm_ask_addcode", lang))
            return
        context.user_data.pop("state", None)
        db.add_discount(code, percent, uses)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_codes")]])
        await update.message.reply_text(t("adm_code_added", lang, code=code.upper()),
                                        parse_mode="HTML", reply_markup=kb)

    elif state == "a_addbal":
        try:
            parts = text.split()
            target, amount = int(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            await update.message.reply_text(t("adm_ask_addbal", lang))
            return
        context.user_data.pop("state", None)
        db.add_balance(target, amount)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_users")]])
        await update.message.reply_text(t("adm_bal_added", lang, amount=amount, uid=target),
                                        reply_markup=kb)
        try:
            await context.bot.send_message(target, t("adm_bal_notify", L(target), amount=amount))
        except Exception:
            pass

    elif state == "a_userinfo":
        results = db.search_users(text)
        if not results:
            kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_users")]])
            await update.message.reply_text(t("adm_user_not_found", lang), reply_markup=kb)
            return
        context.user_data.pop("state", None)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_users")]])
        for u in results[:3]:
            stats = db.get_user_stats(u["user_id"])
            orders = db.get_orders(u["user_id"], 3)
            age = u["account_age"] or estimate_account_age_days(u["user_id"])
            blocked_str = t("adm_yes", lang) if u["blocked"] else t("adm_no", lang)
            note_str = u["note"] or t("adm_no", lang)
            orders_str = "\n".join(f"  #{o['id']} {o['name']} ${o['price']}" for o in orders)
            info = t("adm_userinfo_text", lang, uid=u['user_id'], username=u['username'] or 'N/A',
                     balance=u['balance'], spent=stats['total_spent'], orders=stats['total_orders'],
                     refs=stats['ref_total'], ref_earn=u['ref_earnings'], age=age,
                     blocked=blocked_str, note=note_str, joined=u['joined_at'][:10])
            await update.message.reply_text(
                info + f"\n{t('adm_last_orders', lang)}\n{orders_str}",
                parse_mode="HTML", reply_markup=kb)

    elif state == "a_userstats":
        try:
            u = db.get_user(int(text))
        except ValueError:
            await update.message.reply_text(t("adm_invalid_id", lang))
            return
        if not u:
            await update.message.reply_text(t("adm_user_not_found", lang))
            return
        context.user_data.pop("state", None)
        stats = db.get_user_stats(u["user_id"])
        age = u["account_age"] or estimate_account_age_days(u["user_id"])
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_users")]])
        await update.message.reply_text(
            t("adm_userstats_text", lang, uid=u['user_id'], balance=u['balance'],
              spent=stats['total_spent'], orders=stats['total_orders'],
              refs=stats['ref_total'], ref_earn=u['ref_earnings'], age=age),
            parse_mode="HTML", reply_markup=kb)

    elif state == "a_usernote_id":
        try:
            target = int(text)
        except ValueError:
            await update.message.reply_text(t("adm_invalid_id", lang))
            return
        u = db.get_user(target)
        if not u:
            await update.message.reply_text(t("adm_user_not_found", lang))
            return
        context.user_data["state"] = "a_usernote_text"
        context.user_data["note_target"] = target
        note_str = u["note"] or t("adm_no", lang)
        await update.message.reply_text(t("adm_ask_usernote_text", lang, note=note_str))
        return

    elif state == "a_usernote_text":
        context.user_data.pop("state", None)
        target = context.user_data.pop("note_target", None)
        if target:
            db.set_user_note(target, text)
            kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_users")]])
            await update.message.reply_text(t("adm_note_saved", lang), reply_markup=kb)

    elif state == "a_block":
        try:
            u = db.get_user(int(text))
        except ValueError:
            await update.message.reply_text(t("adm_invalid_id", lang))
            return
        if not u:
            await update.message.reply_text(t("adm_user_not_found", lang))
            return
        context.user_data.pop("state", None)
        new_status = 0 if u["blocked"] else 1
        db.set_blocked(u["user_id"], new_status)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_users")]])
        msg = t("adm_unblocked", lang) if u["blocked"] else t("adm_blocked", lang)
        await update.message.reply_text(msg, reply_markup=kb)

    elif state == "a_vip":
        try:
            u = db.get_user(int(text))
        except ValueError:
            await update.message.reply_text(t("adm_invalid_id", lang))
            return
        if not u:
            await update.message.reply_text(t("adm_user_not_found", lang))
            return
        context.user_data.pop("state", None)
        was_vip = db.is_vip(u["user_id"])
        db.set_vip(u["user_id"], 0 if was_vip else 1)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_users")]])
        msg = t("adm_vip_removed", lang) if was_vip else t("adm_vip_added", lang)
        await update.message.reply_text(msg, reply_markup=kb)

    elif state == "a_broadcast":
        context.user_data.pop("state", None)
        sent = 0
        for u in db.all_users():
            try:
                await context.bot.send_message(u["user_id"], text, parse_mode="HTML")
                sent += 1
            except Exception:
                pass
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "admin")]])
        await update.message.reply_text(t("adm_broadcast_done", lang, n=sent), reply_markup=kb)

    elif state == "a_ticket_reply":
        context.user_data.pop("state", None)
        tid = context.user_data.pop("ticket_id", None)
        if tid:
            tk = db.reply_ticket(tid, text)
            kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_tickets")]])
            await update.message.reply_text(t("adm_ticket_replied", lang, id=tid), reply_markup=kb)
            try:
                target_lang = L(tk["user_id"])
                await context.bot.send_message(
                    tk["user_id"],
                    t("adm_ticket_reply_notify", target_lang, id=tid, reply=text),
                    parse_mode="HTML")
            except Exception:
                pass

    elif state == "a_addadmin":
        try:
            parts = text.split()
            target_id = int(parts[0])
            perms = parts[1] if len(parts) > 1 else "all"
        except (ValueError, IndexError):
            await update.message.reply_text(t("adm_ask_addadmin", lang))
            return
        context.user_data.pop("state", None)
        is_super = 1 if perms == "all" else 0
        db.add_admin(target_id, is_super, perms)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_admins")]])
        await update.message.reply_text(t("adm_admin_added", lang, uid=target_id, perms=perms),
                                        parse_mode="HTML", reply_markup=kb)

    elif state == "a_editadmin":
        try:
            parts = text.split()
            target_id = int(parts[0])
            perms = parts[1] if len(parts) > 1 else "all"
        except (ValueError, IndexError):
            await update.message.reply_text(t("adm_ask_editadmin", lang))
            return
        context.user_data.pop("state", None)
        is_super = 1 if perms == "all" else 0
        db.update_admin(target_id, permissions=perms, is_super=is_super)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_admins")]])
        await update.message.reply_text(t("adm_admin_updated", lang, uid=target_id), reply_markup=kb)

    elif state == "a_addpaymethod":
        try:
            parts = text.split(None, 1)
            name = parts[0]
            details = parts[1] if len(parts) > 1 else ""
        except IndexError:
            await update.message.reply_text(t("adm_ask_addmethod", lang))
            return
        context.user_data.pop("state", None)
        db.add_payment_method(name, details)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_payment_methods")]])
        await update.message.reply_text(t("adm_method_added", lang, name=name),
                                        parse_mode="HTML", reply_markup=kb)

    elif state == "a_setcard":
        try:
            parts = text.split(None, 1)
            card_num = parts[0]
            card_holder = parts[1] if len(parts) > 1 else get_card_holder()
        except Exception:
            await update.message.reply_text(t("adm_invalid_format", lang))
            return
        context.user_data.pop("state", None)
        db.set_setting("card_number", card_num)
        db.set_setting("card_holder", card_holder)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_payment_methods")]])
        await update.message.reply_text(t("adm_card_updated", lang, card=card_num, holder=card_holder),
                                        parse_mode="HTML", reply_markup=kb)

    elif state == "a_setwallet":
        wallet = text.strip().lower()
        if not wallet.startswith("0x") or len(wallet) != 42:
            await update.message.reply_text(t("adm_invalid_wallet", lang))
            return
        context.user_data.pop("state", None)
        db.set_setting("usdt_wallet", wallet)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_payment_methods")]])
        await update.message.reply_text(t("adm_wallet_updated", lang, wallet=wallet),
                                        parse_mode="HTML", reply_markup=kb)

    elif state == "a_lock_channel":
        try:
            parts = text.split(None, 1)
            channel_id = int(parts[0])
            title = parts[1] if len(parts) > 1 else str(channel_id)
        except (ValueError, IndexError):
            await update.message.reply_text(t("adm_ask_lock_ch", lang))
            return
        context.user_data.pop("state", None)
        db.lock_channel(channel_id, title)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_lock")]])
        await update.message.reply_text(t("adm_ch_locked", lang, title=title),
                                        parse_mode="HTML", reply_markup=kb)

    elif state == "a_lock_group":
        try:
            parts = text.split(None, 1)
            group_id = int(parts[0])
            title = parts[1] if len(parts) > 1 else str(group_id)
        except (ValueError, IndexError):
            await update.message.reply_text(t("adm_ask_lock_gr", lang))
            return
        context.user_data.pop("state", None)
        db.lock_group(group_id, title)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_lock")]])
        await update.message.reply_text(t("adm_gr_locked", lang, title=title),
                                        parse_mode="HTML", reply_markup=kb)

    elif state == "a_addapi":
        try:
            parts = text.split()
            name, url = parts[0], parts[1]
            key = parts[2] if len(parts) > 2 else ""
        except (ValueError, IndexError):
            await update.message.reply_text(t("adm_ask_addapi", lang))
            return
        context.user_data.pop("state", None)
        db.set_setting(f"api_{name}_url", url)
        if key:
            db.set_setting(f"api_{name}_key", key)
        kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_apis")]])
        await update.message.reply_text(t("adm_api_added", lang, name=name),
                                        parse_mode="HTML", reply_markup=kb)

# ═══════════ دریافت عکس رسید ═══════════
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    lang = (user["lang"] if user else None) or "fa"

    # بنر محصول توسط ادمین
    if is_admin(uid) and context.user_data.get("state") == "a_banner":
        pid = context.user_data.get("prod_id")
        if pid and update.message.photo:
            file_id = update.message.photo[-1].file_id
            db.update_product(pid, banner_url=file_id)
            context.user_data.pop("state", None)
            kb = InlineKeyboardMarkup([[btn(t("btn_back", lang), "a_products")]])
            await update.message.reply_text(t("adm_banner_set", lang), reply_markup=kb)
        return

    if context.user_data.get("state") != "await_card_photo":
        return

    if get_feature("card_iranian_only") and lang != "fa":
        await update.message.reply_text(t("card_only_fa", lang))
        return

    context.user_data.pop("state")
    amount = context.user_data.pop("card_amount", 0)
    file_id = update.message.photo[-1].file_id
    pay_id = db.create_card_payment(uid, amount, file_id)

    # تأیید خودکار اگر فعال باشد و روش تشخیص خودکار (card_detect_method) پرداخت را تأیید کند
    if get_feature("automatic_card_confirm") and lang == "fa" and await verify_card_auto(uid, amount):
        db.set_card_status(pay_id, "approved")
        db.save_tx(uid, f"card_{pay_id}", amount, "card")
        apply_deposit_bonus(uid, amount)
        await pay_referral(context, uid, amount)
        await update.message.reply_text(t("card_auto_approved", lang))
        rate = await get_usd_rate_async() if get_feature("usd_rate") else USD_TO_TOMAN
        await send_report(context, "payments",
            (f"💳 پرداخت خودکار تأیید شد #{pay_id}\n"
             f"👤 <code>{uid}</code> @{update.effective_user.username or 'N/A'}\n"
             f"💵 ${amount} = {int(amount * rate):,} تومان"),
            photo=file_id)
        await _maybe_big_deposit_alert(context, uid, amount)
        return

    await update.message.reply_text(t("card_pending", lang))
    rate = await get_usd_rate_async() if get_feature("usd_rate") else USD_TO_TOMAN
    caption = (f"💳 درخواست کارت به کارت #{pay_id}\n"
               f"👤 <code>{uid}</code> @{update.effective_user.username or 'N/A'}\n"
               f"💵 ${amount} = {int(amount * rate):,} تومان")
    kb = InlineKeyboardMarkup([[btn("✅ تأیید", f"cbapprove:{pay_id}"),
                                btn("❌ رد", f"cbreject:{pay_id}")]])
    await send_report(context, "payments", caption, photo=file_id, kb=kb)

# ═══════════ تشخیص خودکار پرداخت کارتی (card_detect_method) ═══════════
async def verify_card_auto(uid, amount):
    """
    بررسی خودکار واریز کارت‌به‌کارت بر اساس روش انتخاب‌شده در پنل مدیریت (card_detect_method).
    برای امنیت، در صورت هرگونه خطا یا عدم اطمینان False برمی‌گرداند تا پرداخت برای
    تأیید دستی ادمین باقی بماند (هیچ‌وقت به‌اشتباه یک پرداخت را تأیید نمی‌کند).
    """
    method = db.get_setting("card_detect_method", "manual")

    # حالت "manual" یعنی تأیید خودکار روی هیچ روشی فعال نیست؛
    # پرداخت باید دستی توسط ادمین تأیید شود.
    if method == "manual":
        return False

    if method == "email":
        email_addr = db.get_setting("card_detect_email", "")
        email_pass = db.get_setting("card_detect_email_password", "")
        if not email_addr or not email_pass:
            return False
        try:
            return await asyncio.to_thread(_check_email_for_deposit, email_addr, email_pass, amount)
        except Exception:
            log.exception("card_detect email check failed")
            return False

    if method == "gateway":
        gateway_url = db.get_setting("card_detect_gateway", "")
        gateway_key = db.get_setting("card_detect_gateway_key", "")
        gateway_merchant = db.get_setting("card_detect_gateway_merchant", "")
        if not gateway_url:
            return False
        try:
            resp = await asyncio.to_thread(
                requests.get, gateway_url,
                params={"key": gateway_key, "merchant": gateway_merchant, "amount": amount},
                timeout=8)
            data = resp.json()
            return bool(data.get("verified") or data.get("success"))
        except Exception:
            log.exception("card_detect gateway check failed")
            return False

    if method == "sms":
        # خواندن خودکار پیامک بانکی نیازمند اتصال به یک وب‌سرویس/وب‌هوک اختصاصی SMS است
        # که شماره آن در card_detect_sms_number ذخیره شده، اما این پروژه به چنین سرویسی
        # متصل نیست. برای امنیت، تا اتصال آن سرویس پیاده‌سازی شود، به تأیید دستی ادمین می‌افتد.
        return False

    return False


def _check_email_for_deposit(email_addr, email_password, amount):
    """جست‌وجوی بهترین‌کوشش یک ایمیل تأیید واریز که با مقدار پرداخت مطابقت داشته باشد."""
    import imaplib
    import email as email_lib

    imap_host = db.get_setting("card_detect_email_imap_host", "") or (
        "imap.gmail.com" if "gmail.com" in email_addr else "imap.gmail.com")

    conn = imaplib.IMAP4_SSL(imap_host)
    try:
        conn.login(email_addr, email_password)
        conn.select("INBOX")
        _, data = conn.search(None, "UNSEEN")
        ids = data[0].split()
        amount_str = str(int(amount)) if float(amount).is_integer() else str(amount)
        for msg_id in reversed(ids[-20:]):
            _, msg_data = conn.fetch(msg_id, "(RFC822)")
            msg = email_lib.message_from_bytes(msg_data[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body += payload.decode(errors="ignore")
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode(errors="ignore")
            if amount_str in body:
                conn.store(msg_id, "+FLAGS", "\\Seen")
                return True
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass
        conn.logout()


# ═══════════ هندلر گروه/کانال (قفل) ═══════════
async def group_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بررسی پیام‌های گروه/کانال قفل‌شده — پیام ادمین‌ها و مدیران گروه حذف نمی‌شود"""
    msg = update.effective_message
    if not msg:
        return
    chat = update.effective_chat
    if not chat:
        return
    sender = update.effective_user
    if not sender:
        return

    # پیام ادمین‌های ربات حذف نمی‌شود
    if is_admin(sender.id):
        return

    if chat.type in ("group", "supergroup"):
        if get_feature("lock_groups") and db.locked_group_exists(chat.id):
            # مدیران و ادمین‌های خود گروه نیز مستثنا هستند
            try:
                member = await context.bot.get_chat_member(chat.id, sender.id)
                if member.status in ("administrator", "creator"):
                    return
            except Exception:
                pass
            try:
                await msg.delete()
            except Exception:
                pass
    elif chat.type == "channel":
        if get_feature("lock_channels") and db.locked_channel_exists(chat.id):
            try:
                await msg.delete()
            except Exception:
                pass

# ═══════════ مقداردهی اولیه تنظیمات ═══════════
def init_settings():
    """مقداردهی اولیه تنظیمات از config اگر در دیتابیس نباشند"""
    defaults = {
        "feature_referral": "1" if FEATURE_REFERRAL else "0",
        "feature_card_iranian_only": "1" if FEATURE_CARD_IRANIAN_ONLY else "0",
        "feature_automatic_card_confirm": "1" if FEATURE_AUTOMATIC_CARD_CONFIRM else "0",
        "feature_usd_rate": "1" if FEATURE_USD_RATE else "0",
        "feature_tickets": "1" if FEATURE_TICKETS else "0",
        "feature_warranty": "1" if FEATURE_WARRANTY else "0",
        "feature_lock_groups": "1" if FEATURE_LOCK_GROUPS else "0",
        "feature_lock_channels": "1" if FEATURE_LOCK_CHANNELS else "0",
        "feature_multi_admin": "1" if FEATURE_MULTI_ADMIN else "0",
        "card_number": CARD_NUMBER,
        "card_holder": CARD_HOLDER,
        "usdt_wallet": USDT_WALLET,
    }
    for key, val in defaults.items():
        if db.get_setting(key) is None:
            db.set_setting(key, val)

    # افزودن ادمین‌های اصلی به جدول admins
    for aid in ADMIN_IDS:
        if not db.get_admin(aid):
            db.add_admin(aid, is_super=1, permissions="all")

    # افزودن متدهای پرداخت پیش‌فرض
    for pm in PAYMENT_METHODS:
        db.add_payment_method(pm["name"], pm["details"])

# ═══════════ صف پیام همگانی پنل تحت وب ═══════════
async def _send_broadcast_message(app, uid, message, media_type, media_url, button_text, button_url):
    """ارسال یک پیام همگانی به یک کاربر خاص — با مدیریت محدودیت نرخ تلگرام"""
    from telegram.error import RetryAfter
    message = render_premium_emoji(message)
    button_text, _btn_icon = _btn_label_icon(button_text or "")
    kb = None
    if button_text and button_url:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url,
                                                          api_kwargs=_btn_kwargs(None, _btn_icon))]])
    for _attempt in range(2):
        try:
            if media_type == "photo" and media_url:
                await app.bot.send_photo(uid, media_url, caption=message or None, parse_mode="HTML", reply_markup=kb)
            elif media_type == "video" and media_url:
                await app.bot.send_video(uid, media_url, caption=message or None, parse_mode="HTML", reply_markup=kb)
            elif media_type == "document" and media_url:
                await app.bot.send_document(uid, media_url, caption=message or None, parse_mode="HTML", reply_markup=kb)
            else:
                await app.bot.send_message(uid, message, parse_mode="HTML", reply_markup=kb)
            return True
        except RetryAfter as e:
            await asyncio.sleep(float(getattr(e, "retry_after", 3)) + 1)
        except Exception as e:
            log.warning(f"broadcast send failed for {uid}: {e}")
            return False
    return False


async def process_pending_dms(app):
    """ارسال پیام‌های مستقیمی که از پنل تحت وب در صف قرار گرفته‌اند (پیام مستقیم به کاربر، ارسال مجدد سفارش، تأیید/رد پرداخت، پاسخ تیکت، نتیجه گارانتی)"""
    for row in db.get_pending_dms():
        try:
            data = json.loads(row["value"])
            await app.bot.send_message(data["user_id"], render_premium_emoji(data["message"]), parse_mode="HTML")
        except Exception as e:
            log.warning(f"pending_dm send failed for {row.get('key')}: {e}")
        finally:
            db.delete_setting(row["key"])


async def process_pending_broadcasts(app):
    """بررسی و ارسال پیام‌های همگانی که از پنل تحت وب در صف قرار گرفته‌اند"""
    # ۱) پیام فوری در صف (دکمه «ارسال» در پنل)
    pending = db.get_pending_panel_broadcast()
    if pending:
        success = 0
        for uid in pending.get("user_ids", []):
            ok = await _send_broadcast_message(
                app, uid, pending.get("message", ""), pending.get("media_type", "text"),
                pending.get("media_url", ""), pending.get("button_text", ""), pending.get("button_url", "")
            )
            if ok:
                success += 1
            await asyncio.sleep(0.05)
        db.mark_broadcast_sent(pending.get("id"), success)
        db.clear_pending_panel_broadcast()

    # ۲) پیام‌های زمان‌بندی‌شده‌ای که موعدشان رسیده
    for bcast in db.get_due_scheduled_broadcasts():
        user_ids = db.get_broadcast_target_users(bcast.get("target_filter", "all"))
        success = 0
        for uid in user_ids:
            ok = await _send_broadcast_message(
                app, uid, bcast.get("message", ""), bcast.get("media_type", "text"),
                bcast.get("media_url", ""), bcast.get("button_text", ""), bcast.get("button_url", "")
            )
            if ok:
                success += 1
            await asyncio.sleep(0.05)
        db.mark_broadcast_sent(bcast["id"], success)


async def broadcast_worker(app):
    """پردازش دوره‌ای صف ارسال پیام همگانی و پیام‌های مستقیم که از پنل تحت وب ثبت می‌شود"""
    while True:
        try:
            await process_pending_broadcasts(app)
            await process_pending_dms(app)
        except Exception as e:
            log.error(f"broadcast_worker error: {e}")
        await asyncio.sleep(10)


# ═══════════ بکاپ خودکار و گزارش روزانه ═══════════
async def _send_db_backup(app):
    """ارسال فایل بکاپ دیتابیس به تاپیک بکاپ‌ها (یا پیوی ادمین‌های اصلی)"""
    import os as _os, shutil as _shutil, tempfile as _tempfile
    gid = db.get_setting("report_group_id", "") or ""
    topic = db.get_setting("report_topic_backups", "") or ""
    enabled = db.get_setting("report_on_backups", "1") == "1"
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    tmp = _os.path.join(_tempfile.gettempdir(), f"shop_backup_{ts}.db")
    _shutil.copy2(db.DB, tmp)
    caption = f"🗄 بکاپ خودکار دیتابیس\n📅 {ts}"
    sent = False
    try:
        if gid and enabled:
            try:
                kwargs = {"caption": caption}
                if topic:
                    kwargs["message_thread_id"] = int(topic)
                with open(tmp, "rb") as f:
                    await app.bot.send_document(int(gid), f, filename=f"shop_backup_{ts}.db", **kwargs)
                sent = True
            except Exception as e:
                log.error(f"backup to group failed: {e}")
        if not sent:
            for aid in ADMIN_IDS:
                try:
                    with open(tmp, "rb") as f:
                        await app.bot.send_document(aid, f, filename=f"shop_backup_{ts}.db", caption=caption)
                    sent = True
                except Exception:
                    pass
    finally:
        try:
            _os.remove(tmp)
        except Exception:
            pass


async def _daily_report(app):
    """آمار روزانه: فروش، واریز، کاربر جدید، تیکت باز"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with db.get_db() as conn:
        orders = conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(price),0) s FROM orders WHERE date(created_at)=?", (today,)).fetchone()
        deps = conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(amount),0) s FROM transactions WHERE date(created_at)=?", (today,)).fetchone()
        new_users = conn.execute(
            "SELECT COUNT(*) c FROM users WHERE date(joined_at)=?", (today,)).fetchone()["c"]
        open_tickets = conn.execute(
            "SELECT COUNT(*) c FROM tickets WHERE status='open'").fetchone()["c"]
    text = (f"📊 گزارش روزانه — {today}\n"
            f"🛒 فروش: {orders['c']} سفارش — ${orders['s']:.2f}\n"
            f"💰 واریز: {deps['c']} تراکنش — ${deps['s']:.2f}\n"
            f"👤 کاربر جدید: {new_users}\n"
            f"🎫 تیکت باز: {open_tickets}")
    await send_report(app, "daily", text)


async def _run_auto_backup(app):
    """بکاپ خودکار: نسخه محلی در پوشه backups + ارسال تلگرام (طبق تنظیمات)"""
    import sqlite3 as _sq, os as _os
    base = _os.path.dirname(_os.path.abspath(__file__))
    bdir = _os.path.join(base, "backups")
    path = None
    try:
        _os.makedirs(bdir, exist_ok=True)
        name = f"shop_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        path = _os.path.join(bdir, name)
        src = _sq.connect(_os.path.join(base, "shop.db"))
        dst = _sq.connect(path)
        src.backup(dst)
        dst.close()
        src.close()
    except Exception as e:
        log.error(f"local backup failed: {e}")
        path = None
    if db.get_setting("backup_to_telegram", "1") == "1":
        await _send_db_backup(app)
    if path and db.get_setting("backup_keep_local", "1") != "1":
        try:
            _os.remove(path)
            path = None
        except Exception:
            pass
    # نگه‌داشتن N بکاپ آخر
    try:
        keep = int(float(db.get_setting("backup_keep_last", "10") or 10))
        files = sorted([f for f in _os.listdir(bdir)
                        if f.startswith("shop_backup_") and f.endswith(".db")], reverse=True)
        for old in files[keep:]:
            _os.remove(_os.path.join(bdir, old))
    except Exception:
        pass


async def _summary_report(app, days, title):
    """گزارش تجمیعی چندروزه (هفتگی/ماهانه)"""
    span = f"-{days} days"
    with db.get_db() as conn:
        orders = conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(price),0) s FROM orders WHERE created_at >= datetime('now', ?)",
            (span,)).fetchone()
        deps = conn.execute(
            "SELECT COUNT(*) c, COALESCE(SUM(amount),0) s FROM transactions WHERE created_at >= datetime('now', ?)",
            (span,)).fetchone()
        new_users = conn.execute(
            "SELECT COUNT(*) c FROM users WHERE joined_at >= datetime('now', ?)",
            (span,)).fetchone()["c"]
    text = (f"{title}\n"
            f"🛒 فروش: {orders['c']} سفارش — ${orders['s']:.2f}\n"
            f"💰 واریز: {deps['c']} تراکنش — ${deps['s']:.2f}\n"
            f"👤 کاربر جدید: {new_users}")
    await send_report(app, "daily", text)


async def _send_scheduled_message(app, text):
    """ارسال پیام زمان‌بندی‌شده به همه کاربران غیرمسدود"""
    with db.get_db() as conn:
        uids = [r["user_id"] for r in conn.execute(
            "SELECT user_id FROM users WHERE blocked=0").fetchall()]
    body = render_premium_emoji(text)
    sent = 0
    for u in uids:
        try:
            await app.bot.send_message(u, body, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    log.info(f"scheduled message sent to {sent} users")


async def _expire_stale_card_payments(app):
    """انقضای خودکار پرداخت‌های کارتی تاییدنشده"""
    hours = float(db.get_setting("card_pending_expire_hours", "0") or 0)
    if hours <= 0:
        return
    with db.get_db() as conn:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(card_payments)")]
        if "created_at" not in cols:
            return
        rows = conn.execute(
            "SELECT id, user_id FROM card_payments WHERE status='pending' "
            "AND datetime(created_at) <= datetime('now', ?)",
            (f"-{int(hours)} hours",)).fetchall()
    for r in rows:
        try:
            db.set_card_status(r["id"], "rejected")
            await app.bot.send_message(r["user_id"], t("card_expired", L(r["user_id"])))
        except Exception:
            pass


async def reports_scheduler(app):
    """چک دوره‌ای: بکاپ خودکار، گزارش‌ها، پیام‌های زمان‌بندی‌شده، انقضای پرداخت‌ها"""
    while True:
        try:
            # ── پاکسازی دوره‌ای دیکشنری ضداسپم (جلوگیری از نشت حافظه) ──
            _spam_cleanup()
            # ── بکاپ خودکار (دقیقه/ساعت/روز) ──
            try:
                value = float(db.get_setting("backup_interval_value", "") or 0)
            except ValueError:
                value = 0
            unit = db.get_setting("backup_interval_unit", "hours") or "hours"
            minutes = value * (1 if unit == "minutes" else 60 if unit == "hours" else 1440)
            if not minutes:
                minutes = float(db.get_setting("backup_interval_hours", "0") or 0) * 60
            if minutes >= 5:
                last = float(db.get_setting("_backup_last_ts", "0") or 0)
                if time.time() - last >= minutes * 60:
                    db.set_setting("_backup_last_ts", str(time.time()))
                    await _run_auto_backup(app)
            now = datetime.now()
            today = now.strftime("%Y-%m-%d")
            hhmm = now.strftime("%H:%M")
            # ── گزارش روزانه ──
            if db.get_setting("report_on_daily", "0") == "1" and db.get_setting("report_group_id", ""):
                target = db.get_setting("report_daily_time", "23:00") or "23:00"
                if hhmm >= target and db.get_setting("_daily_report_last", "") != today:
                    db.set_setting("_daily_report_last", today)
                    await _daily_report(app)
            # ── گزارش هفتگی (جمعه) و ماهانه (اول ماه) ──
            if db.get_setting("report_weekly", "0") == "1" and now.weekday() == 4 and hhmm >= "12:00" \
                    and db.get_setting("_weekly_report_last", "") != today:
                db.set_setting("_weekly_report_last", today)
                await _summary_report(app, 7, "📅 گزارش هفتگی")
            if db.get_setting("report_monthly", "0") == "1" and now.day == 1 and hhmm >= "12:00" \
                    and db.get_setting("_monthly_report_last", "") != today:
                db.set_setting("_monthly_report_last", today)
                await _summary_report(app, 30, "🗓 گزارش ماهانه")
            # ── پیام‌های زمان‌بندی‌شده ──
            try:
                for m in db.get_scheduled_messages():
                    if m["enabled"] and m["send_time"] and hhmm >= m["send_time"] and m["last_sent"] != today:
                        db.mark_scheduled_sent(m["id"], today)
                        await _send_scheduled_message(app, m["text"])
            except Exception as e:
                log.error(f"scheduled messages error: {e}")
            # ── انقضای پرداخت‌های کارتی معلق ──
            try:
                await _expire_stale_card_payments(app)
            except Exception as e:
                log.error(f"card expiry error: {e}")
            # ── اسکالیشن تیکت‌های فوری بی‌پاسخ (SLA) ──
            try:
                _sla_h = float(db.get_setting("sla_urgent_hours", "0") or 0)
                if _sla_h > 0:
                    with db.get_db() as _conn:
                        _rows = _conn.execute(
                            "SELECT id, user_id, subject FROM tickets WHERE status='open' "
                            "AND priority='urgent' AND COALESCE(escalated,0)=0 "
                            "AND (julianday('now') - julianday(created_at)) * 24 >= ?",
                            (_sla_h,)).fetchall()
                        for _r in _rows:
                            _conn.execute("UPDATE tickets SET escalated=1 WHERE id=?", (_r["id"],))
                    for _r in _rows:
                        await send_report(app, "tickets",
                            f"🚨 هشدار SLA: تیکت فوری #{_r['id']} بیش از {_sla_h:g} ساعت بی‌پاسخ مانده!\n"
                            f"👤 <code>{_r['user_id']}</code>\n📌 {_r['subject']}")
            except Exception as e:
                log.error(f"sla error: {e}")
            # ── یادآوری انقضای اشتراک‌ها ──
            try:
                for _o in db.get_expiring_orders(3):
                    db.mark_renew_notified(_o["id"])
                    try:
                        _ol = L(_o["user_id"])
                        await app.bot.send_message(_o["user_id"],
                            t("sub_expiring", _ol, name=_o["name"], d=_o["days_left"]),
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                                t("btn_renew", _ol), callback_data=f"prod:{_o['product_id']}")]]))
                    except Exception:
                        pass
            except Exception as e:
                log.error(f"subscription reminder error: {e}")
            # ── هشدار موجودی کم (روزی یک‌بار) ──
            try:
                threshold = int(float(db.get_setting("alert_low_stock", "0") or 0))
                if threshold > 0 and db.get_setting("_lowstock_last", "") != today and hhmm >= "09:00":
                    db.set_setting("_lowstock_last", today)
                    with db.get_db() as conn:
                        rows = conn.execute(
                            "SELECT p.name, (SELECT COUNT(*) FROM stock s "
                            "WHERE s.product_id = p.id AND s.is_sold = 0) c "
                            "FROM products p").fetchall()
                    low = [r for r in rows if (r["c"] or 0) <= threshold]
                    if low:
                        txt = "📦 هشدار موجودی کم:\n" + "\n".join(
                            f"• {r['name']}: {r['c']}" for r in low)
                        await send_report(app, "errors", txt)
            except Exception:
                pass
        except Exception as e:
            log.error(f"reports_scheduler error: {e}")
        await asyncio.sleep(60)


async def precheckout_handler(update, context):
    """تایید پیش‌پرداخت استارز"""
    try:
        await update.pre_checkout_query.answer(ok=True)
    except Exception:
        pass


async def successful_payment_handler(update, context):
    """پرداخت موفق استارز — شارژ حساب"""
    sp = update.message.successful_payment
    uid = update.effective_user.id
    lang = L(uid)
    usd = 0.0
    try:
        # مبلغ دلاری از payload فاکتور (نرخ لحظه ساخت فاکتور) خوانده میشود
        _pp = (sp.invoice_payload or "").split(":")
        if len(_pp) == 3 and _pp[0] == "stars":
            usd = round(float(_pp[2]), 2)
    except Exception:
        usd = 0.0
    if not usd:
        per = float(db.get_setting("stars_per_usd", "50") or 50)
        usd = round(sp.total_amount / per, 2) if per else 0
    tx_id = f"stars_{sp.telegram_payment_charge_id}"
    if db.tx_exists(tx_id):
        return
    db.save_tx(uid, tx_id, usd, "stars")
    bonus = apply_deposit_bonus(uid, usd)
    await pay_referral(context, uid, usd)
    u2 = db.get_user(uid)
    extra = f"\n🎁 بونوس: +${bonus:.2f}" if bonus else ""
    await update.message.reply_text(
        f"{t('tx_ok', lang)}\n\n💰 +${usd:.2f}{extra}\n{t('your_balance', lang)}: ${u2['balance']:.2f}",
        parse_mode="HTML")
    await send_report(context, "deposits",
        f"⭐ واریز Stars!\n👤 <code>{uid}</code>\n💵 ${usd}")
    await _maybe_big_deposit_alert(context, uid, usd)


async def _error_handler(update, context):
    """گزارش خطاهای مهم ربات به تاپیک خطاها"""
    log.error("Unhandled bot error", exc_info=context.error)
    try:
        err = str(context.error)[:300]
        await send_report(context, "errors", f"⚠️ خطای ربات\n<code>{err}</code>")
    except Exception:
        pass


async def _post_init(app):
    """شروع پردازش پس‌زمینه صف پیام همگانی هنگام روشن شدن ربات"""
    app.create_task(broadcast_worker(app), name="broadcast_worker")
    app.create_task(reports_scheduler(app), name="reports_scheduler")


# ═══════════ اجرا ═══════════
def main():
    db.init_db()
    init_settings()

    app = Application.builder().token(BOT_TOKEN).post_init(_post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        text_handler))
    # هندلر گروه/کانال برای قفل
    app.add_handler(MessageHandler(
        (filters.ChatType.GROUPS | filters.ChatType.CHANNEL) & ~filters.COMMAND,
        group_handler))

    app.add_error_handler(_error_handler)

    webhook_url = (os.environ.get("WEBHOOK_URL") or "").strip()
    if webhook_url:
        port = int(os.environ.get("WEBHOOK_PORT", "8443") or 8443)
        print(f"🚀 ربات روشن شد (webhook روی پورت {port})...")
        app.run_webhook(listen="0.0.0.0", port=port, url_path=BOT_TOKEN,
                        webhook_url=f"{webhook_url.rstrip('/')}/{BOT_TOKEN}")
    else:
        print("🚀 ربات روشن شد (polling)...")
        app.run_polling()

if __name__ == "__main__":
    main()
