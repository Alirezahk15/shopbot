"""Zarinpal payment callback — hit by the user's browser after payment (no auth)."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
import sys, os, requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

try:
    from config import ADMIN_IDS as _ADMIN_IDS
except Exception:
    _ADMIN_IDS = []

router = APIRouter(prefix="/api/pay", tags=["pay"])


def _tg_send(chat_id, text):
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        return
    try:
        requests.post("https://api.telegram.org/bot" + token + "/sendMessage",
                      json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=15)
    except Exception:
        pass


def _html(title, body, ok=True):
    color = "#22c55e" if ok else "#ef4444"
    icon = "\u2705" if ok else "\u274c"
    return HTMLResponse(f"""<!doctype html><html dir="rtl" lang="fa"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title></head>
<body style="margin:0;display:flex;align-items:center;justify-content:center;min-height:100vh;background:#0f1117;font-family:Tahoma,sans-serif">
<div style="background:#1a1d27;border:1px solid #2a2e3d;border-radius:16px;padding:40px;max-width:420px;text-align:center;color:#e5e7eb">
<div style="font-size:48px;margin-bottom:16px">{icon}</div>
<h2 style="color:{color};margin:0 0 12px">{title}</h2>
<p style="color:#9ca3af;line-height:1.8">{body}</p>
</div></body></html>""")


def _apply_deposit_bonus(uid, usd):
    try:
        percent = float(db.get_setting("deposit_bonus_percent", "0") or 0)
        min_amt = float(db.get_setting("deposit_bonus_min", "0") or 0)
        if percent > 0 and usd >= min_amt:
            bonus = round(usd * percent / 100, 2)
            if bonus > 0:
                db.add_balance(uid, bonus)
                return bonus
    except Exception:
        pass
    return 0


def _pay_referral_sync(uid, amount):
    """معادل همزمان pay_referral ربات (دو سطح + سقف روزانه)."""
    if db.get_setting("feature_referral", "1") != "1":
        return
    user = db.get_user(uid)
    if not user or not user["referrer"]:
        return
    daily_cap = float(db.get_setting("referral_daily_cap", "0") or 0)

    def _pay(ref_id, percent):
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
        _tg_send(ref_id, f"\U0001F389 پورسانت رفرال: <b>${bonus:.2f}</b> به حساب شما اضافه شد!")

    p1 = float(db.get_setting("referral_percent", "10") or 10)
    _pay(user["referrer"], p1)
    p2 = float(db.get_setting("referral_l2_percent", "0") or 0)
    if p2 > 0:
        ref1 = db.get_user(user["referrer"])
        if ref1 and ref1["referrer"]:
            _pay(ref1["referrer"], p2)


@router.get("/zarinpal/callback")
def zarinpal_callback(Authority: str = "", Status: str = ""):
    if not Authority:
        return _html("خطا", "پارامتر پرداخت نامعتبر است.", ok=False)
    pending = db.pop_zp_pending(Authority)
    if not pending:
        return _html("خطا", "پرداخت یافت نشد یا قبلاً پردازش شده است.", ok=False)
    if Status != "OK":
        return _html("پرداخت لغو شد", "پرداخت انجام نشد. می‌توانید به ربات برگردید و دوباره تلاش کنید.", ok=False)
    merchant = db.get_setting("zarinpal_merchant", "")
    try:
        r = requests.post("https://payment.zarinpal.com/pg/v4/payment/verify.json", json={
            "merchant_id": merchant,
            "amount": pending["amount_rial"],
            "authority": Authority,
        }, timeout=20).json()
    except Exception:
        # اجازهٔ تلاش مجدد — رکورد را برمی‌گردانیم
        db.add_zp_pending(Authority, pending["user_id"], pending["amount_rial"], pending["amount_usd"])
        return _html("خطا", "ارتباط با زرین‌پال برقرار نشد. چند لحظه بعد صفحه را رفرش کنید.", ok=False)
    code = (r.get("data") or {}).get("code")
    if code not in (100, 101):
        # Put the pending record back. It was popped before verification,
        # so without this a transient Zarinpal error loses the payment for
        # good and the user can never retry.
        db.add_zp_pending(Authority, pending["user_id"],
                          pending["amount_rial"], pending["amount_usd"])
        return _html("پرداخت ناموفق", f"تایید پرداخت انجام نشد (کد {code}).", ok=False)
    ref_id = (r.get("data") or {}).get("ref_id", Authority)
    uid = pending["user_id"]
    usd = float(pending["amount_usd"])
    tx_id = f"zp_{ref_id}"
    if db.tx_exists(tx_id):
        return _html("پرداخت تکراری", "این پرداخت قبلاً ثبت شده است.", ok=False)
    db.save_tx(uid, tx_id, usd, "zarinpal")
    bonus = _apply_deposit_bonus(uid, usd)
    try:
        _pay_referral_sync(uid, usd)
    except Exception:
        pass
    user = db.get_user(uid)
    balance = user["balance"] if user else 0
    bonus_line = f"\n\U0001F381 بونوس: +${bonus:.2f}" if bonus else ""
    _tg_send(uid, f"\u2705 پرداخت زرین‌پال تایید شد!\n\n\U0001F4B0 +${usd:.2f}{bonus_line}\n\U0001F4B3 موجودی: ${balance:.2f}\n\U0001F9FE کد پیگیری: <code>{ref_id}</code>")
    try:
        all_admins = set(_ADMIN_IDS) | {a["user_id"] for a in db.get_all_admins()}
    except Exception:
        all_admins = set(_ADMIN_IDS)
    for aid in all_admins:
        _tg_send(aid, f"\U0001F4B3 واریز زرین‌پال\n\U0001F464 <code>{uid}</code>\n\U0001F4B5 ${usd:.2f}\n\U0001F9FE <code>{ref_id}</code>")
    return _html("پرداخت موفق", f"مبلغ ${usd:.2f} به حساب شما اضافه شد. به ربات برگردید.")
