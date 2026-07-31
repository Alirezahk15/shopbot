import os
from dotenv import load_dotenv

load_dotenv()

# ---- Secrets (loaded from .env — never hardcode these) ----
BOT_TOKEN = os.environ["BOT_TOKEN"]
BSCSCAN_API_KEY = os.environ["BSCSCAN_API_KEY"]
_USD_RATE_API_KEY = os.environ["USD_RATE_API_KEY"]

ADMIN_IDS = [1663320676]
SUPPORT_USERNAME = "@akhit77"

# ---- USDT BEP20 (شبکه BSC) ----
USDT_WALLET = "0x28fd6fcaDc20844E79c3538341774e991470C1d0".lower()
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
