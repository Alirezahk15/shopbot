from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Optional
from api.auth import verify_token
import sys, os, json, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/settings", tags=["settings"])

FEATURE_KEYS = [
    "referral", "card_iranian_only", "automatic_card_confirm",
    "usd_rate", "tickets", "warranty", "lock_groups", "lock_channels", "multi_admin",
    # New features
    "maintenance_mode", "registration_locked", "daily_purchase_limit", "vip_mode",
]

# Group report categories (each maps to a forum topic in the reports group)
REPORT_CATEGORIES = [
    "sales", "payments", "deposits", "tickets", "warranty",
    "new_users", "daily", "errors", "sessions", "backups",
]

REPORT_CATEGORY_LABELS = {
    "sales": "🛒 فروش‌ها", "payments": "💳 پرداخت‌های کارتی", "deposits": "💎 واریزهای USDT",
    "tickets": "🎫 تیکت‌ها", "warranty": "🛡 گارانتی", "new_users": "👤 کاربران جدید",
    "daily": "📊 گزارش روزانه", "errors": "⚠️ خطاها", "sessions": "🖥 نشست‌ها", "backups": "🗄 بکاپ‌ها",
}


# USD Rate API providers
USD_RATE_PROVIDERS = {
    "navasan": {
        "name": "Navasan",
        "url_template": "https://api.navasan.tech/latest/?api={key}",
        "requires_key": True,
        "free": True,
        "description": "navasan.tech — رایگان با محدودیت",
        "extractor": "navasan",
    },
    "tgju": {
        "name": "TGJU",
        "url_template": "https://api.tgju.org/v1/market/indicator/summary-table-data/price_dollar_rl",
        "requires_key": False,
        "free": True,
        "description": "tgju.org — رایگان، نرخ بازار آزاد",
        "extractor": "tgju",
    },
    "manual": {
        "name": "نرخ دستی",
        "url_template": "",
        "requires_key": False,
        "free": True,
        "description": "تنظیم دستی نرخ دلار",
        "extractor": "manual",
    },
}


def extract_usd_rate(provider_key: str, data: dict) -> int:
    """Extract USD rate (in Tomans) from API response based on provider."""
    if provider_key == "navasan":
        # {"usd": {"value": 90000, ...}} — already in Tomans
        usd = data.get("usd", {})
        if isinstance(usd, dict):
            val = usd.get("value", usd.get("sell", 0))
        else:
            val = usd
        return int(float(str(val).replace(",", "")))
    elif provider_key == "tgju":
        # {"data": [["1,912,900", ...], ...]} — in Rials, divide by 10 for Tomans
        rows = data.get("data", [])
        if rows and isinstance(rows[0], list):
            val = rows[0][0]  # First row, first column = current price in Rials
            rials = int(float(str(val).replace(",", "")))
            return rials // 10  # Convert Rials to Tomans
        raise ValueError("Unexpected TGJU response format")
    else:
        raise ValueError(f"Unknown provider: {provider_key}")


@router.get("")
def get_settings(_: str = Depends(verify_token)):
    all_settings = db.get_all_settings()
    features = {}
    for key in FEATURE_KEYS:
        val = all_settings.get(f"feature_{key}", "0" if key in ("maintenance_mode", "registration_locked", "vip_mode") else "1")
        features[key] = val == "1"
    return {
        "features": features,
        # Feature customization values
        "feature_values": {
            "daily_purchase_limit": all_settings.get("feature_daily_purchase_limit_value", "5"),
            "vip_discount": all_settings.get("feature_vip_discount", "10"),
            "maintenance_message": all_settings.get("feature_maintenance_message", ""),
        },
        # Payment
        "card_number": all_settings.get("card_number", ""),
        "card_holder": all_settings.get("card_holder", ""),
        "usdt_wallet": all_settings.get("usdt_wallet", ""),
        "min_deposit": all_settings.get("min_deposit", "1.0"),
        "max_deposit": all_settings.get("max_deposit", "0"),
        # Bot
        "welcome_message": all_settings.get("welcome_message", ""),
        "support_username": all_settings.get("support_username", ""),
        "premium_button_icons": all_settings.get("premium_button_icons", "0"),
        # Referral
        "referral_percent": all_settings.get("referral_percent", "10"),
        "referral_min_days": all_settings.get("referral_min_days", "60"),
        # USD Rate
        "usd_rate_provider": all_settings.get("usd_rate_provider", "navasan"),
        "usd_rate_api_key": all_settings.get("usd_rate_api_key", ""),
        "usd_rate_manual": all_settings.get("usd_rate_manual", "90000"),
        "usd_rate_cache_minutes": all_settings.get("usd_rate_cache_minutes", "30"),
        # Card auto-detection
        "card_detect_method": all_settings.get("card_detect_method", "manual"),
        "card_detect_sms_number": all_settings.get("card_detect_sms_number", ""),
        "card_detect_email": all_settings.get("card_detect_email", ""),
        "card_detect_gateway": all_settings.get("card_detect_gateway", ""),
        "card_detect_gateway_key": all_settings.get("card_detect_gateway_key", ""),
        # Payment methods & extras
        "pm_card": all_settings.get("pm_card", "1") == "1",
        "pm_usdt_bep20": all_settings.get("pm_usdt_bep20", "1") == "1",
        "pm_usdt_trc20": all_settings.get("pm_usdt_trc20", "0") == "1",
        "pm_ton": all_settings.get("pm_ton", "0") == "1",
        "pm_stars": all_settings.get("pm_stars", "0") == "1",
        "pm_zarinpal": all_settings.get("pm_zarinpal", "0") == "1",
        "usdt_trc20_wallet": all_settings.get("usdt_trc20_wallet", ""),
        "ton_wallet": all_settings.get("ton_wallet", ""),
        "stars_per_usd": all_settings.get("stars_per_usd", "50"),
        "zarinpal_merchant": all_settings.get("zarinpal_merchant", ""),
        "panel_base_url": all_settings.get("panel_base_url", ""),
        "deposit_bonus_percent": all_settings.get("deposit_bonus_percent", "0"),
        "deposit_bonus_min": all_settings.get("deposit_bonus_min", "0"),
        "card_pending_expire_hours": all_settings.get("card_pending_expire_hours", "0"),
        # Bot extras
        "captcha_enabled": all_settings.get("captcha_enabled", "0") == "1",
        "antispam_per_min": all_settings.get("antispam_per_min", "0"),
        "levels_enabled": all_settings.get("levels_enabled", "0") == "1",
        "level_silver_spend": all_settings.get("level_silver_spend", "50"),
        "level_silver_discount": all_settings.get("level_silver_discount", "3"),
        "level_gold_spend": all_settings.get("level_gold_spend", "200"),
        "level_gold_discount": all_settings.get("level_gold_discount", "7"),
        # Referral extras
        "referral_l2_percent": all_settings.get("referral_l2_percent", "0"),
        "referral_signup_bonus": all_settings.get("referral_signup_bonus", "0"),
        "referral_daily_cap": all_settings.get("referral_daily_cap", "0"),
        "referral_leaderboard": all_settings.get("referral_leaderboard", "0") == "1",
        "referral_banner_text": all_settings.get("referral_banner_text", ""),
        # Reports extras
        "report_weekly": all_settings.get("report_weekly", "0") == "1",
        "report_monthly": all_settings.get("report_monthly", "0") == "1",
        "report_quiet_start": all_settings.get("report_quiet_start", ""),
        "report_quiet_end": all_settings.get("report_quiet_end", ""),
        "alert_big_deposit": all_settings.get("alert_big_deposit", "0"),
        "alert_low_stock": all_settings.get("alert_low_stock", "0"),
        # Security & support extras (v2)
        "sales_paused": all_settings.get("sales_paused", "0"),
        "sla_urgent_hours": all_settings.get("sla_urgent_hours", "0"),
        "ref_fraud_daily": all_settings.get("ref_fraud_daily", "0"),
        "faq_suggest": all_settings.get("faq_suggest", "1"),
        "panel_title": all_settings.get("panel_title", ""),
        "panel_logo_url": all_settings.get("panel_logo_url", ""),
        "occasion_messages": all_settings.get("occasion_messages", ""),
        "welcome_gold": all_settings.get("welcome_gold", ""),
        "welcome_silver": all_settings.get("welcome_silver", ""),
        "menu_image_main": all_settings.get("menu_image_main", ""),
        # Group reports
        "report_group_id": all_settings.get("report_group_id", ""),
        "report_mode": all_settings.get("report_mode", "dm"),
        "report_daily_time": all_settings.get("report_daily_time", "23:00"),
        "backup_interval_hours": all_settings.get("backup_interval_hours", "0"),
        "report_topics": {c: all_settings.get(f"report_topic_{c}", "") for c in REPORT_CATEGORIES},
        "report_flags": {c: all_settings.get(f"report_on_{c}", "0" if c == "daily" else "1") == "1" for c in REPORT_CATEGORIES},
    }


@router.get("/feature-stats")
def get_feature_stats(_: str = Depends(verify_token)):
    """Get live stats for each feature."""
    with db.get_db() as conn:
        return {
            "tickets_open": conn.execute("SELECT COUNT(*) c FROM tickets WHERE status='open'").fetchone()["c"],
            "warranty_pending": conn.execute("SELECT COUNT(*) c FROM warranty_claims WHERE status='pending'").fetchone()["c"],
            "referrals_total": conn.execute("SELECT COUNT(*) c FROM users WHERE referrer IS NOT NULL").fetchone()["c"],
            "cards_pending": conn.execute("SELECT COUNT(*) c FROM card_payments WHERE status='pending'").fetchone()["c"],
            "locked_channels": conn.execute("SELECT COUNT(*) c FROM locked_channels").fetchone()["c"],
            "locked_groups": conn.execute("SELECT COUNT(*) c FROM locked_groups").fetchone()["c"],
            "admins_count": conn.execute("SELECT COUNT(*) c FROM admins").fetchone()["c"],
        }


class FeatureValueRequest(BaseModel):
    key: str
    value: str


@router.post("/feature-value")
def set_feature_value(body: FeatureValueRequest, _: str = Depends(verify_token)):
    """Set a customization value for a feature."""
    allowed_keys = {
        "daily_purchase_limit_value", "vip_discount", "maintenance_message"
    }
    if body.key not in allowed_keys:
        raise HTTPException(status_code=400, detail=f"Unknown feature value key: {body.key}")
    db.set_setting(f"feature_{body.key}", body.value)
    return {"success": True}


class FeatureToggleRequest(BaseModel):
    key: str
    value: bool


@router.post("/feature")
def toggle_feature(body: FeatureToggleRequest, _: str = Depends(verify_token)):
    if body.key not in FEATURE_KEYS:
        return {"success": False, "error": "Unknown feature key"}
    db.set_setting(f"feature_{body.key}", "1" if body.value else "0")
    return {"success": True}


class CardRequest(BaseModel):
    card_number: str
    card_holder: str


@router.post("/card")
def update_card(body: CardRequest, _: str = Depends(verify_token)):
    db.set_setting("card_number", body.card_number)
    db.set_setting("card_holder", body.card_holder)
    return {"success": True}


class WalletRequest(BaseModel):
    wallet: str


@router.post("/wallet")
def update_wallet(body: WalletRequest, _: str = Depends(verify_token)):
    wallet = body.wallet.strip().lower()
    if not wallet.startswith("0x") or len(wallet) != 42:
        return {"success": False, "error": "Invalid wallet address"}
    db.set_setting("usdt_wallet", wallet)
    return {"success": True}


class DepositLimitsRequest(BaseModel):
    min_deposit: float
    max_deposit: float


@router.post("/deposit-limits")
def update_deposit_limits(body: DepositLimitsRequest, _: str = Depends(verify_token)):
    db.set_setting("min_deposit", str(body.min_deposit))
    db.set_setting("max_deposit", str(body.max_deposit))
    return {"success": True}


class BotSettingsRequest(BaseModel):
    welcome_message: Optional[str] = None
    support_username: Optional[str] = None
    premium_button_icons: Optional[str] = None


@router.post("/bot")
def update_bot_settings(body: BotSettingsRequest, _: str = Depends(verify_token)):
    if body.welcome_message is not None:
        db.set_setting("welcome_message", body.welcome_message)
    if body.support_username is not None:
        db.set_setting("support_username", body.support_username)
    if body.premium_button_icons is not None:
        db.set_setting("premium_button_icons", "1" if str(body.premium_button_icons) in ("1", "true", "True") else "0")
    return {"success": True}


class ReferralSettingsRequest(BaseModel):
    referral_percent: int
    referral_min_days: int


@router.post("/referral")
def update_referral_settings(body: ReferralSettingsRequest, _: str = Depends(verify_token)):
    if not 1 <= body.referral_percent <= 100:
        raise HTTPException(status_code=400, detail="Percent must be 1-100")
    if body.referral_min_days < 0:
        raise HTTPException(status_code=400, detail="Min days must be >= 0")
    db.set_setting("referral_percent", str(body.referral_percent))
    db.set_setting("referral_min_days", str(body.referral_min_days))
    return {"success": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_panel_password(body: ChangePasswordRequest, _: str = Depends(verify_token)):
    from api.auth import PANEL_PASSWORD
    import api.auth as auth_module
    if body.current_password != PANEL_PASSWORD:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines = content.split("\n")
        new_lines = []
        found = False
        for line in lines:
            if line.startswith("PANEL_PASSWORD="):
                new_lines.append(f"PANEL_PASSWORD={body.new_password}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"PANEL_PASSWORD={body.new_password}")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        auth_module.PANEL_PASSWORD = body.new_password
        os.environ["PANEL_PASSWORD"] = body.new_password
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update .env: {e}")


@router.get("/system-info")
def get_system_info(_: str = Depends(verify_token)):
    """Get system information."""
    import platform, sqlite3
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "shop.db")
    db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0

    # Count records
    with db.get_db() as conn:
        stats = {
            "users": conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
            "orders": conn.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"],
            "transactions": conn.execute("SELECT COUNT(*) c FROM transactions").fetchone()["c"],
        }

    # Disk space
    try:
        disk = shutil.disk_usage(os.path.dirname(db_path))
        disk_info = {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent": round(disk.used / disk.total * 100, 1),
        }
    except Exception:
        disk_info = {}

    return {
        "python_version": platform.python_version(),
        "os": platform.system(),
        "db_size_kb": round(db_size / 1024, 1),
        "db_path": db_path,
        "sqlite_version": sqlite3.sqlite_version,
        "records": stats,
        "disk": disk_info,
    }


@router.get("/backup")
def download_backup(_: str = Depends(verify_token)):
    """Download the SQLite database as a backup."""
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "shop.db")
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")
    with open(db_path, "rb") as f:
        content = f.read()
    from datetime import datetime
    filename = f"shop_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/referral-stats")
def get_referral_stats(_: str = Depends(verify_token)):
    """Get referral statistics."""
    with db.get_db() as conn:
        total_referrals = conn.execute("SELECT COUNT(*) c FROM users WHERE referrer IS NOT NULL").fetchone()["c"]
        total_earnings = conn.execute("SELECT COALESCE(SUM(ref_earnings), 0) s FROM users").fetchone()["s"]
        top_referrers = conn.execute("""
            SELECT u.user_id, u.username,
                   COUNT(r.user_id) as ref_count,
                   u.ref_earnings
            FROM users u
            LEFT JOIN users r ON r.referrer = u.user_id
            GROUP BY u.user_id
            HAVING ref_count > 0
            ORDER BY ref_count DESC
            LIMIT 10
        """).fetchall()
    return {
        "total_referrals": total_referrals,
        "total_earnings": round(total_earnings, 2),
        "top_referrers": [dict(r) for r in top_referrers],
    }


# ── USD Rate Settings ──

@router.get("/usd-providers")
def get_usd_providers(_: str = Depends(verify_token)):
    """Get list of available USD rate providers."""
    return {"providers": USD_RATE_PROVIDERS}


class UsdRateSettingsRequest(BaseModel):
    provider: str
    api_key: Optional[str] = ""
    manual_rate: Optional[str] = "90000"
    cache_minutes: Optional[int] = 30


@router.post("/usd-rate")
def update_usd_rate_settings(body: UsdRateSettingsRequest, _: str = Depends(verify_token)):
    if body.provider not in USD_RATE_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {body.provider}")
    db.set_setting("usd_rate_provider", body.provider)
    if body.api_key:
        db.set_setting("usd_rate_api_key", body.api_key)
    if body.manual_rate:
        db.set_setting("usd_rate_manual", body.manual_rate)
    db.set_setting("usd_rate_cache_minutes", str(body.cache_minutes or 30))
    return {"success": True}


@router.post("/usd-rate/test")
def test_usd_rate(_: str = Depends(verify_token)):
    """Test the current USD rate API and return the rate."""
    import requests as _req
    provider_key = db.get_setting("usd_rate_provider", "tgju")
    api_key = db.get_setting("usd_rate_api_key", "")
    manual_rate = db.get_setting("usd_rate_manual", "90000")

    if provider_key == "manual":
        return {"success": True, "rate": int(manual_rate or 90000), "provider": "manual", "source": "manual"}

    provider = USD_RATE_PROVIDERS.get(provider_key)
    if not provider:
        raise HTTPException(status_code=400, detail="Unknown provider")

    url = provider["url_template"].format(key=api_key or "")
    try:
        resp = _req.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            return {"success": False, "error": f"HTTP {resp.status_code}: {resp.text[:100]}", "provider": provider["name"]}
        data = resp.json()
        rate = extract_usd_rate(provider_key, data)
        if rate < 1000:
            raise ValueError(f"Rate too low: {rate}")
        return {"success": True, "rate": rate, "provider": provider["name"], "source": url}
    except Exception as e:
        return {"success": False, "error": str(e), "provider": provider["name"]}


# ── Card Auto-Detection Settings ──

CARD_DETECT_METHODS = {
    "manual": {
        "name": "تأیید دستی",
        "name_en": "Manual Approval",
        "desc": "ادمین هر پرداخت را دستی تأیید می‌کند (پیش‌فرض)",
        "desc_en": "Admin manually approves each payment (default)",
        "fields": [],
    },
    "sms": {
        "name": "SMS بانک",
        "name_en": "Bank SMS",
        "desc": "ربات SMS های بانک را می‌خواند و پرداخت را تأیید می‌کند",
        "desc_en": "Bot reads bank SMS messages and auto-confirms payments",
        "fields": [
            {"key": "sms_number", "label": "شماره SMS بانک", "label_en": "Bank SMS Number", "placeholder": "+989XXXXXXXXX"},
        ],
        "note": "⚠️ هنوز پیاده‌سازی نشده — انتخاب این گزینه به تأیید دستی برمی‌گردد",
        "note_en": "Not implemented yet - selecting this falls back to manual approval",
        "unavailable": True,
    },
    "email": {
        "name": "ایمیل بانک",
        "name_en": "Bank Email",
        "desc": "ربات ایمیل‌های تراکنش بانک را می‌خواند",
        "desc_en": "Bot reads bank transaction emails",
        "fields": [
            {"key": "email", "label": "آدرس ایمیل", "label_en": "Email Address", "placeholder": "bank@example.com"},
            {"key": "email_password", "label": "رمز ایمیل (App Password)", "label_en": "Email Password (App Password)", "placeholder": "xxxx xxxx xxxx xxxx"},
        ],
        "note": "نیاز به دسترسی IMAP ایمیل دارد",
        "note_en": "Requires IMAP email access",
    },
    "gateway": {
        "name": "درگاه پرداخت",
        "name_en": "Payment Gateway",
        "desc": "استفاده از ZarinPal، IDPay یا سایر درگاه‌های رسمی",
        "desc_en": "Use ZarinPal, IDPay or other official payment gateways",
        "fields": [
            {"key": "gateway_name", "label": "نام درگاه", "label_en": "Gateway Name", "placeholder": "zarinpal / idpay / ..."},
            {"key": "gateway_key", "label": "API Key درگاه", "label_en": "Gateway API Key", "placeholder": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"},
            {"key": "gateway_merchant", "label": "Merchant ID", "label_en": "Merchant ID", "placeholder": ""},
        ],
        "note": "نیاز به مجوز کسب‌وکار و قرارداد با درگاه دارد",
        "note_en": "Requires business license and gateway contract",
    },
    "ocr": {
        "name": "OCR رسید",
        "name_en": "Receipt OCR",
        "desc": "کاربر عکس رسید می‌فرستد، سیستم مبلغ را می‌خواند",
        "desc_en": "User sends receipt photo, system reads the amount",
        "fields": [],
        "note": "دقت ۸۰-۹۰٪ — توصیه می‌شود با تأیید دستی ترکیب شود",
        "note_en": "80-90% accuracy — recommended to combine with manual review",
    },
}


@router.get("/card-detect-methods")
def get_card_detect_methods(_: str = Depends(verify_token)):
    return {"methods": CARD_DETECT_METHODS}


class CardDetectSettingsRequest(BaseModel):
    method: str
    sms_number: Optional[str] = ""
    email: Optional[str] = ""
    email_password: Optional[str] = ""
    gateway_name: Optional[str] = ""
    gateway_key: Optional[str] = ""
    gateway_merchant: Optional[str] = ""


@router.post("/card-detect")
def update_card_detect_settings(body: CardDetectSettingsRequest, _: str = Depends(verify_token)):
    if body.method not in CARD_DETECT_METHODS:
        raise HTTPException(status_code=400, detail=f"Unknown method: {body.method}")
    db.set_setting("card_detect_method", body.method)
    if body.sms_number:
        db.set_setting("card_detect_sms_number", body.sms_number)
    if body.email:
        db.set_setting("card_detect_email", body.email)
    if body.email_password:
        db.set_setting("card_detect_email_password", body.email_password)
    if body.gateway_name:
        db.set_setting("card_detect_gateway", body.gateway_name)
    if body.gateway_key:
        db.set_setting("card_detect_gateway_key", body.gateway_key)
    if body.gateway_merchant:
        db.set_setting("card_detect_gateway_merchant", body.gateway_merchant)
    return {"success": True}


# ──────── Group reports (topics) settings ────────
class ReportsSettingsRequest(BaseModel):
    report_group_id: Optional[str] = None
    report_mode: Optional[str] = None
    report_daily_time: Optional[str] = None
    backup_interval_hours: Optional[str] = None
    topics: Optional[dict] = None
    flags: Optional[dict] = None


@router.post("/reports")
def update_reports_settings(body: ReportsSettingsRequest, _: str = Depends(verify_token)):
    if body.report_group_id is not None:
        db.set_setting("report_group_id", body.report_group_id.strip())
    if body.report_mode is not None:
        if body.report_mode not in ("group", "dm", "both"):
            raise HTTPException(status_code=400, detail="Invalid report mode")
        db.set_setting("report_mode", body.report_mode)
    if body.report_daily_time is not None:
        db.set_setting("report_daily_time", body.report_daily_time.strip() or "23:00")
    if body.backup_interval_hours is not None:
        try:
            hours = float(str(body.backup_interval_hours) or 0)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid backup interval")
        db.set_setting("backup_interval_hours", str(hours))
    if body.topics:
        for cat, val in body.topics.items():
            if cat in REPORT_CATEGORIES:
                val = str(val or "").strip()
                if val and not val.lstrip("-").isdigit():
                    raise HTTPException(status_code=400, detail=f"Invalid topic ID for {cat}")
                db.set_setting(f"report_topic_{cat}", val)
    if body.flags:
        for cat, val in body.flags.items():
            if cat in REPORT_CATEGORIES:
                db.set_setting(f"report_on_{cat}", "1" if val else "0")
    return {"success": True}


@router.post("/reports/test")
def test_reports(_: str = Depends(verify_token)):
    """Send a test message to every enabled topic to verify the IDs."""
    import requests as rq
    token = os.environ.get("BOT_TOKEN", "")
    gid = db.get_setting("report_group_id", "")
    if not token:
        raise HTTPException(status_code=400, detail="BOT_TOKEN is not set")
    if not gid:
        raise HTTPException(status_code=400, detail="Group ID is not set")
    results = {}
    for cat in REPORT_CATEGORIES:
        if db.get_setting(f"report_on_{cat}", "0" if cat == "daily" else "1") != "1":
            continue
        topic = db.get_setting(f"report_topic_{cat}", "")
        payload = {"chat_id": gid, "text": f"✅ پیام تست — {REPORT_CATEGORY_LABELS.get(cat, cat)}"}
        if topic:
            payload["message_thread_id"] = int(topic)
        try:
            resp = rq.post("https://api.telegram.org/bot" + token + "/sendMessage", json=payload, timeout=10).json()
            results[cat] = True if resp.get("ok") else str(resp.get("description", "failed"))
        except Exception as exc:
            results[cat] = str(exc)
    return {"results": results}


class CreateTopicsRequest(BaseModel):
    group_id: Optional[str] = None


@router.post("/reports/create-topics")
def create_report_topics(body: CreateTopicsRequest, _: str = Depends(verify_token)):
    """Auto-create a forum topic for each report category and save the IDs.

    Requires the bot to be a group admin with the "Manage Topics" right,
    and the group must have Topics (forum) enabled.
    """
    import requests as rq
    token = os.environ.get("BOT_TOKEN", "")
    gid = (body.group_id or "").strip() or db.get_setting("report_group_id", "")
    if not token:
        raise HTTPException(status_code=400, detail="BOT_TOKEN is not set")
    if not gid:
        raise HTTPException(status_code=400, detail="Group ID is not set")
    if body.group_id and body.group_id.strip():
        db.set_setting("report_group_id", body.group_id.strip())
    icon_colors = [7322096, 16766590, 13338331, 9367192, 16749490, 16478047]
    created, skipped, errors = {}, [], {}
    for i, cat in enumerate(REPORT_CATEGORIES):
        if db.get_setting(f"report_topic_{cat}", ""):
            skipped.append(cat)
            continue
        payload = {
            "chat_id": gid,
            "name": REPORT_CATEGORY_LABELS.get(cat, cat),
            "icon_color": icon_colors[i % len(icon_colors)],
        }
        try:
            resp = rq.post("https://api.telegram.org/bot" + token + "/createForumTopic", json=payload, timeout=10).json()
            if resp.get("ok"):
                tid = resp["result"]["message_thread_id"]
                db.set_setting(f"report_topic_{cat}", str(tid))
                created[cat] = tid
            else:
                errors[cat] = str(resp.get("description", "failed"))
        except Exception as exc:
            errors[cat] = str(exc)
    return {"created": created, "skipped": skipped, "errors": errors}


# ═══ New: bulk settings / custom commands / scheduled messages / referral timeline ═══
_SIMPLE_KEYS = {
    "pm_card", "pm_usdt_bep20", "pm_usdt_trc20", "pm_ton", "pm_stars", "pm_zarinpal",
    "usdt_trc20_wallet", "ton_wallet", "stars_per_usd", "zarinpal_merchant", "panel_base_url",
    "deposit_bonus_percent", "deposit_bonus_min", "card_pending_expire_hours",
    "captcha_enabled", "antispam_per_min", "levels_enabled",
    "level_silver_spend", "level_silver_discount", "level_gold_spend", "level_gold_discount",
    "referral_l2_percent", "referral_signup_bonus", "referral_daily_cap",
    "referral_leaderboard", "referral_banner_text",
    "report_weekly", "report_monthly", "report_quiet_start", "report_quiet_end",
    "alert_big_deposit", "alert_low_stock",
    "sales_paused", "sla_urgent_hours", "ref_fraud_daily", "faq_suggest",
    "panel_title", "panel_logo_url", "occasion_messages", "welcome_gold",
    "welcome_silver", "menu_image_main",
}


class BulkSettingsRequest(BaseModel):
    values: dict


@router.post("/bulk")
def set_bulk_settings(body: BulkSettingsRequest, _: str = Depends(verify_token)):
    """Save a whitelisted set of simple settings in one call."""
    for key, value in (body.values or {}).items():
        if key not in _SIMPLE_KEYS:
            raise HTTPException(status_code=400, detail=f"Unknown setting: {key}")
        if isinstance(value, bool):
            value = "1" if value else "0"
        db.set_setting(key, str(value).strip())
    return {"success": True}


class CustomCommandRequest(BaseModel):
    trigger: str
    response: str


@router.get("/custom-commands")
def list_custom_commands(_: str = Depends(verify_token)):
    return {"commands": db.get_custom_commands()}


@router.post("/custom-commands")
def add_custom_command(body: CustomCommandRequest, _: str = Depends(verify_token)):
    trigger = body.trigger.strip()
    response = body.response.strip()
    if not trigger or not response:
        raise HTTPException(status_code=400, detail="Trigger and response are required")
    db.add_custom_command(trigger, response)
    return {"success": True}


@router.delete("/custom-commands/{cmd_id}")
def remove_custom_command(cmd_id: int, _: str = Depends(verify_token)):
    db.delete_custom_command(cmd_id)
    return {"success": True}


class ScheduledMessageRequest(BaseModel):
    text: str
    send_time: str


@router.get("/scheduled-messages")
def list_scheduled_messages(_: str = Depends(verify_token)):
    return {"messages": db.get_scheduled_messages()}


@router.post("/scheduled-messages")
def add_scheduled_message(body: ScheduledMessageRequest, _: str = Depends(verify_token)):
    text = body.text.strip()
    st = body.send_time.strip()
    if not text or len(st) != 5 or st[2] != ":":
        raise HTTPException(status_code=400, detail="Invalid text or time (HH:MM)")
    db.add_scheduled_message(text, st)
    return {"success": True}


@router.delete("/scheduled-messages/{msg_id}")
def remove_scheduled_message(msg_id: int, _: str = Depends(verify_token)):
    db.delete_scheduled_message(msg_id)
    return {"success": True}


@router.get("/referral-timeline")
def referral_timeline(_: str = Depends(verify_token)):
    """Daily new-referral counts for the last 30 days (for the panel chart)."""
    try:
        with db.get_db() as conn:
            rows = conn.execute(
                "SELECT substr(joined_at, 1, 10) d, COUNT(*) c FROM users "
                "WHERE referrer IS NOT NULL AND joined_at >= date('now', '-30 days') "
                "GROUP BY d ORDER BY d"
            ).fetchall()
        return {"timeline": [dict(r) for r in rows]}
    except Exception:
        return {"timeline": []}
