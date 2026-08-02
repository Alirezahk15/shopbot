import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

def _require_env(name):
    """Read a REQUIRED environment variable, or exit with a clear message.
    English on purpose: journalctl and most terminals cannot render Persian."""
    val = os.environ.get(name)
    if not val:
        import sys
        sys.exit(
            "\n[ShopBot] Required environment variable %s is missing!\n" % name
            + "The .env file next to config.py is missing or incomplete.\n"
            + "How to fix:\n"
            + "  cd /opt/shopbot && cp .env.example .env && nano .env\n"
            + "  sudo systemctl restart shopbot\n"
        )
    return val


def _optional_env(name, default=""):
    """Read an OPTIONAL environment variable.
    These are only needed when the matching payment method is enabled, so an
    empty value must never stop the bot from booting."""
    return os.environ.get(name) or default


def require_bscscan_key():
    """Called at the moment a BEP20 transaction is verified, so a missing key
    fails loudly there instead of preventing the whole bot from starting."""
    if not BSCSCAN_API_KEY:
        raise RuntimeError(
            "BSCSCAN_API_KEY is not set in .env, so USDT BEP20 payments cannot "
            "be verified. Add the key to /opt/shopbot/.env and restart the bot."
        )
    return BSCSCAN_API_KEY


# ---- Secrets (loaded from .env - never hardcode these) ----
# Only BOT_TOKEN is genuinely required for the bot to start.
BOT_TOKEN = _require_env("BOT_TOKEN")

# Optional - only used when USDT BEP20 payment is enabled.
BSCSCAN_API_KEY = _optional_env("BSCSCAN_API_KEY")
# Optional - navasan.tech accepts the public "free" key.
_USD_RATE_API_KEY = _optional_env("USD_RATE_API_KEY", "free")
# Optional - only used when Zarinpal payment is enabled.
ZARINPAL_MERCHANT_ID = _optional_env("ZARINPAL_MERCHANT_ID")

def _int_list_env(name, default):
    """Parse a comma separated list of Telegram numeric IDs from .env."""
    raw = _optional_env(name, default)
    out = []
    for part in str(raw).replace(" ", "").split(","):
        if part.lstrip("-").isdigit():
            out.append(int(part))
    return out


# Deployment specific values. Defaults are kept for backward compatibility
# with existing installs, but every one of them can be overridden in .env.
ADMIN_IDS = _int_list_env("ADMIN_IDS", "1663320676")
SUPPORT_USERNAME = _optional_env("SUPPORT_USERNAME", "@akhit77")

# ---- USDT BEP20 (شبکه BSC) ----
USDT_WALLET = _optional_env("USDT_WALLET", "0x28fd6fcaDc20844E79c3538341774e991470C1d0").lower()
USDT_CONTRACT = "0x55d398326f99059ff775485246999027b3197955"
BSCSCAN_API = "https://api.bscscan.com/api"
MIN_DEPOSIT = 1.0
TX_MAX_AGE_HOURS = 24

# ---- کارت به کارت ----
CARD_NUMBER = "6037-XXXX-XXXX-XXXX"
CARD_HOLDER = "نام صاحب کارت"
USD_TO_TOMAN = 90000
CARD_CONFIRM_ADMIN_REQUIRED = True

# ---- نرخ دلار آنلاین ----
# از navasan.tech (رایگان، نیازی به API key ندارد)
USD_RATE_API = f"https://api.navasan.tech/latest/?api={_USD_RATE_API_KEY}"
USD_RATE_FIELD = "usd"          # فیلد نرخ فروش دلار
USD_RATE_FALLBACK = 90000       # اگه API کار نکرد از این استفاده میشه
USD_RATE_CACHE_MINUTES = 30     # هر ۳۰ دقیقه یکبار بروزرسانی

# ---- رفرال ----
REFERRAL_PERCENT = 10
REFERRAL_MIN_DAYS = 60

# ---- قابلیت‌های پیش‌فرض (در دیتابیس settings هم ذخیره میشن) ----
FEATURE_LOCK_GROUPS = True
FEATURE_LOCK_CHANNELS = True
FEATURE_CARD_IRANIAN_ONLY = True
FEATURE_AUTOMATIC_CARD_CONFIRM = False
FEATURE_USD_RATE = True
FEATURE_REFERRAL = True
FEATURE_TICKETS = True
FEATURE_WARRANTY = True
FEATURE_MULTI_ADMIN = True

# ---- متدهای پرداخت پیش‌فرض ----
PAYMENT_METHODS = [
    {"name": "usdt", "details": "USDT (BEP20)"},
    {"name": "card", "details": "کارت به کارت (ریالی)"},
]

# ---- API های خارجی (اختیاری) ----
EXTERNAL_APIS = {
    # "my_api": {"url": "https://...", "key": "..."},
}
