import os
import sys
import requests as _requests
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Add parent directory to path so we can import database.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from api.auth import create_token, PANEL_PASSWORD, verify_token
import api.auth as auth_module
from api.routers import (
    insights, faq, texts, menu_buttons, brand,
    dashboard, users, products, orders, payments,
    tickets, settings, discounts, warranty, lock,
    admins, broadcast, methods, buttons, system, pay
)
import database as db

app = FastAPI(title="Shop Bot Admin Panel API", version="1.0.0")

# ── CORS ──
ALLOWED_ORIGINS = os.environ.get(
    "PANEL_CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──
app.include_router(dashboard.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(tickets.router)
app.include_router(settings.router)
app.include_router(discounts.router)
app.include_router(warranty.router)
app.include_router(lock.router)
app.include_router(admins.router)
app.include_router(broadcast.router)
app.include_router(methods.router)
app.include_router(buttons.router)
app.include_router(system.router)
app.include_router(pay.router)
app.include_router(insights.router)
app.include_router(faq.router)
app.include_router(texts.router)
app.include_router(menu_buttons.router)
app.include_router(brand.router)


# ── Auth endpoints ──
import hashlib as _hashlib
import secrets as _secrets
from datetime import datetime, timedelta, timezone, date
from typing import Optional
from fastapi import Request
from fastapi.responses import JSONResponse

try:
    from config import ADMIN_IDS as _ADMIN_IDS
except Exception:
    _ADMIN_IDS = []

_TG_API_BASE = "https://api.telegram.org/bot"


def _send_telegram_message(chat_id, text):
    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        return False
    try:
        resp = _requests.post(
            _TG_API_BASE + bot_token + "/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        ).json()
        return bool(resp.get("ok"))
    except Exception:
        return False


_REPORT_CATS = ("sales", "payments", "deposits", "tickets", "warranty",
                "new_users", "daily", "errors", "sessions", "backups")


def _tg_api(method, payload):
    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        return {"ok": False, "description": "BOT_TOKEN not set"}
    try:
        return _requests.post(_TG_API_BASE + bot_token + "/" + method, json=payload, timeout=10).json()
    except Exception as exc:
        return {"ok": False, "description": str(exc)}


def _send_group_report(category, text, reply_markup=None):
    """Send a report to the configured group topic; fall back to admin DMs."""
    gid = db.get_setting("report_group_id", "") or ""
    mode = db.get_setting("report_mode", "dm") or "dm"
    enabled = db.get_setting(f"report_on_{category}", "1") == "1"
    topic = db.get_setting(f"report_topic_{category}", "") or ""
    sent_group = False
    if gid and enabled and mode in ("group", "both"):
        payload = {"chat_id": gid, "text": text, "parse_mode": "HTML"}
        if topic:
            payload["message_thread_id"] = int(topic)
        if reply_markup:
            payload["reply_markup"] = reply_markup
        sent_group = bool(_tg_api("sendMessage", payload).get("ok"))
    if mode in ("dm", "both") or (mode == "group" and not sent_group):
        admin_ids = set(_ADMIN_IDS)
        try:
            admin_ids |= {a["user_id"] for a in db.get_all_admins()}
        except Exception:
            pass
        for aid in admin_ids:
            payload = {"chat_id": aid, "text": text, "parse_mode": "HTML"}
            if reply_markup:
                payload["reply_markup"] = reply_markup
            _tg_api("sendMessage", payload)


def _start_panel_session(claims, request, username):
    """Create a tracked panel session and report the new login to the sessions topic."""
    sid = _secrets.token_hex(16)
    ip = client_ip(request)
    agent = (request.headers.get("user-agent", "") or "")[:200]
    try:
        db.create_panel_session(sid, claims.get("uid") or 0, username or "", ip, agent)
    except Exception:
        return claims
    kb = {"inline_keyboard": [[
        {"text": "✅ تأیید", "callback_data": f"sessapprove:{sid}"},
        {"text": "⛔ رد و خروج", "callback_data": f"sessreject:{sid}"},
    ]]}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = ("🖥 ورود جدید به پنل مدیریت\n"
            f"👤 {username or 'admin'} (<code>{claims.get('uid') or '-'}</code>)\n"
            f"🌐 IP: <code>{ip}</code>\n"
            f"📱 {agent or 'Unknown device'}\n"
            f"🕒 {now}")
    try:
        _send_group_report("sessions", text, kb)
    except Exception:
        pass
    return {**claims, "sid": sid}


import time as _time

# ── Real client IP ──
# The panel sits behind nginx, so request.client.host is always 127.0.0.1.
# Using it directly made the IP allowlist match nothing (127.0.0.1 is always
# allowed) and put every visitor in a single rate-limit bucket, so five bad
# logins from anyone locked out every admin.
# Set PANEL_TRUST_PROXY=0 if the app is exposed directly without a proxy.
_TRUST_PROXY = (os.environ.get("PANEL_TRUST_PROXY", "1") or "1").strip().lower() \
    not in ("0", "false", "no")


def client_ip(request: Request) -> str:
    direct = request.client.host if request.client else ""
    if not _TRUST_PROXY:
        return direct or "unknown"
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        first = fwd.split(",")[0].strip()   # left-most entry is the client
        if first:
            return first
    real = (request.headers.get("x-real-ip", "") or "").strip()
    if real:
        return real
    return direct or "unknown"


_allowlist_cache = {"value": "", "ts": 0.0}
_ALLOWLIST_TTL = 30


def _get_ip_allowlist() -> str:
    """Cached. This setting used to be read from SQLite on every request."""
    now = _time.time()
    if now - _allowlist_cache["ts"] < _ALLOWLIST_TTL:
        return _allowlist_cache["value"]
    try:
        val = (db.get_setting("panel_ip_allowlist", "") or "").strip()
    except Exception:
        val = _allowlist_cache["value"]
    _allowlist_cache["value"] = val
    _allowlist_cache["ts"] = now
    return val


class LoginRequest(BaseModel):
    username: Optional[str] = None
    password: str


@app.post("/api/auth/login")
def login(body: LoginRequest, request: Request):
    ip = client_ip(request)
    rate_key = f"login:{ip}"
    if not auth_module.check_rate_limit(rate_key):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")

    username = (body.username or "").strip()
    row = auth_module.get_admin_by_username(username) if username else None

    if row is not None and auth_module.verify_password(body.password, row["panel_password_hash"]):
        # Expired temporary admin?
        if row["expires_at"] and str(row["expires_at"]) < date.today().isoformat():
            raise HTTPException(status_code=403, detail="This admin account has expired")
        auth_module.clear_attempts(rate_key)
        claims = auth_module.admin_claims(row)
        if row["totp_enabled"]:
            # Short-lived ticket: only valid for the 2FA verification step
            ticket = auth_module.create_token({**claims, "purpose": "totp"}, hours=0.1)
            return {"totp_required": True, "ticket": ticket}
        token = auth_module.create_token(_start_panel_session(claims, request, row["panel_username"]))
        return {"token": token, "admin": auth_module.public_admin_info(claims, row["totp_enabled"])}

    # Legacy fallback: PANEL_PASSWORD works only while no admin has credentials yet
    if (auth_module.PANEL_PASSWORD
            and auth_module.credentialed_admin_count() == 0
            and _secrets.compare_digest(body.password, auth_module.PANEL_PASSWORD)):
        uid = _ADMIN_IDS[0] if _ADMIN_IDS else 0
        claims = {"sub": username or "admin", "uid": uid, "is_super": True, "perms": "all", "purpose": "full"}
        auth_module.clear_attempts(rate_key)
        return {"token": auth_module.create_token(_start_panel_session(claims, request, username or "admin")),
                "admin": auth_module.public_admin_info(claims, False)}

    auth_module.record_attempt(rate_key)
    raise HTTPException(status_code=401, detail="Invalid username or password")


class TotpVerifyRequest(BaseModel):
    ticket: str
    code: str


@app.post("/api/auth/totp-verify")
def totp_verify_login(body: TotpVerifyRequest, request: Request):
    payload = auth_module.decode_token(body.ticket)
    if payload.get("purpose") != "totp":
        raise HTTPException(status_code=401, detail="Invalid ticket")
    uid = payload.get("uid")
    rate_key = f"totp:{uid}"
    if not auth_module.check_rate_limit(rate_key, max_attempts=6, window=300):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")
    row = auth_module.get_admin_row(uid)
    if not row or not row["totp_enabled"] or not auth_module.verify_totp(row["totp_secret"], body.code):
        auth_module.record_attempt(rate_key)
        raise HTTPException(status_code=401, detail="Invalid verification code")
    auth_module.clear_attempts(rate_key)
    claims = auth_module.admin_claims(row)
    return {"token": auth_module.create_token(_start_panel_session(claims, request, row["panel_username"])),
            "admin": auth_module.public_admin_info(claims, True)}


@app.get("/api/auth/me")
def auth_me(payload: dict = Depends(verify_token)):
    row = auth_module.get_admin_row(payload.get("uid"))
    return {
        "username": payload.get("sub"),
        "user_id": payload.get("uid"),
        "is_super": bool(payload.get("is_super")),
        "perms": payload.get("perms", "all"),
        "totp_enabled": bool(row["totp_enabled"]) if row is not None else False,
        "has_credentials": bool(row is not None and row["panel_username"] and row["panel_password_hash"]),
    }


def _ensure_admin_row(uid):
    if uid is None:
        raise HTTPException(status_code=400, detail="This session has no admin ID. Log in with username and password.")
    row = auth_module.get_admin_row(uid)
    if row is None:
        if uid in _ADMIN_IDS:
            with db.get_db() as conn:
                conn.execute("INSERT OR IGNORE INTO admins (user_id, is_super, permissions) VALUES (?,1,'all')", (uid,))
            row = auth_module.get_admin_row(uid)
        else:
            raise HTTPException(status_code=404, detail="Admin not found")
    return row


@app.post("/api/auth/totp/setup")
def totp_setup(payload: dict = Depends(verify_token)):
    uid = payload.get("uid")
    _ensure_admin_row(uid)
    secret = auth_module.generate_totp_secret()
    with db.get_db() as conn:
        conn.execute("UPDATE admins SET totp_pending_secret=? WHERE user_id=?", (secret, uid))
    return {"secret": secret, "otpauth_uri": auth_module.totp_uri(secret, payload.get("sub") or f"admin-{uid}")}


class TotpCodeRequest(BaseModel):
    code: str


@app.post("/api/auth/totp/enable")
def totp_enable(body: TotpCodeRequest, payload: dict = Depends(verify_token)):
    uid = payload.get("uid")
    row = _ensure_admin_row(uid)
    pending = row["totp_pending_secret"] if "totp_pending_secret" in row.keys() else ""
    if not pending:
        raise HTTPException(status_code=400, detail="No 2FA setup in progress")
    if not auth_module.verify_totp(pending, body.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    with db.get_db() as conn:
        conn.execute("UPDATE admins SET totp_secret=?, totp_enabled=1, totp_pending_secret='' WHERE user_id=?", (pending, uid))
    return {"success": True}


@app.post("/api/auth/totp/disable")
def totp_disable(body: TotpCodeRequest, payload: dict = Depends(verify_token)):
    uid = payload.get("uid")
    row = _ensure_admin_row(uid)
    if not row["totp_enabled"]:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    if not auth_module.verify_totp(row["totp_secret"], body.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    with db.get_db() as conn:
        conn.execute("UPDATE admins SET totp_secret='', totp_enabled=0, totp_pending_secret='' WHERE user_id=?", (uid,))
    return {"success": True}


class SelfChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@app.post("/api/auth/change-password")
def self_change_password(body: SelfChangePasswordRequest, payload: dict = Depends(verify_token)):
    uid = payload.get("uid")
    row = _ensure_admin_row(uid)
    if not row["panel_password_hash"]:
        raise HTTPException(status_code=400, detail="No panel credentials set for this admin")
    if not auth_module.verify_password(body.current_password, row["panel_password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    with db.get_db() as conn:
        conn.execute(
            "UPDATE admins SET panel_password_hash=? WHERE user_id=?",
            (auth_module.hash_password(body.new_password), uid),
        )
    return {"success": True}


class ForgotRequest(BaseModel):
    user_id: int


_GENERIC_FORGOT = {
    "success": True,
    "message": "If this ID belongs to a panel admin, a verification code has been sent in the bot.",
}


@app.post("/api/auth/forgot")
def forgot_password(body: ForgotRequest, request: Request):
    ip = client_ip(request)
    if not auth_module.check_rate_limit(f"forgot:{ip}", max_attempts=5, window=600):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")
    auth_module.record_attempt(f"forgot:{ip}")
    row = auth_module.get_admin_row(body.user_id)
    # Always answer the same way so admin IDs can't be probed.
    # A panel_username is deliberately NOT required here: on a fresh install the
    # bot creates admin rows with no panel credentials, and those owners must
    # still be able to recover access or the panel is locked forever.
    if row is None:
        return _GENERIC_FORGOT
    code = f"{_secrets.randbelow(1000000):06d}"
    code_hash = _hashlib.sha256(code.encode()).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    with db.get_db() as conn:
        conn.execute(
            "UPDATE admins SET reset_code_hash=?, reset_code_expires=? WHERE user_id=?",
            (code_hash, expires, body.user_id),
        )
    _send_telegram_message(
        body.user_id,
        "\U0001F510 کد بازیابی رمز پنل مدیریت:\n\n"
        f"{code}\n\n"
        "\u23F0 این کد تا ۱۰ دقیقه معتبر است.\n"
        "اگر شما درخواست نداده‌اید، این پیام را نادیده بگیرید."
    )
    return _GENERIC_FORGOT


class ResetPasswordRequest(BaseModel):
    user_id: int
    code: str
    new_password: str


@app.post("/api/auth/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request):
    ip = client_ip(request)
    rate_key = f"reset:{ip}"
    if not auth_module.check_rate_limit(rate_key, max_attempts=6, window=600):
        raise HTTPException(status_code=429, detail="Too many attempts. Try again in a few minutes.")
    row = auth_module.get_admin_row(body.user_id)
    code_hash = _hashlib.sha256(str(body.code or "").strip().encode()).hexdigest()
    valid = (
        row is not None
        and row["reset_code_hash"]
        and row["reset_code_expires"]
        and str(row["reset_code_expires"]) > datetime.now(timezone.utc).isoformat()
        and code_hash == row["reset_code_hash"]
    )
    if not valid:
        auth_module.record_attempt(rate_key)
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")
    with db.get_db() as conn:
        # Give the admin a login name if they do not have one yet, otherwise the
        # new password would be unusable (login looks admins up by username).
        current = row["panel_username"] if row is not None else None
        username = (current or "").strip()
        if not username:
            taken = conn.execute(
                "SELECT 1 FROM admins WHERE lower(panel_username)='admin' "
                "AND user_id<>?", (body.user_id,)
            ).fetchone()
            username = "admin" if not taken else "admin%d" % body.user_id
        conn.execute(
            "UPDATE admins SET panel_username=?, panel_password_hash=?, "
            "reset_code_hash='', reset_code_expires='' WHERE user_id=?",
            (username, auth_module.hash_password(body.new_password), body.user_id),
        )
    auth_module.clear_attempts(rate_key)
    return {"success": True, "username": username}


# ── Section permission enforcement (based on admin permissions) ──
_PERM_GUARD_SKIP = ("/api/auth/", "/api/health", "/api/pay/")


@app.middleware("http")
async def permission_guard(request: Request, call_next):
    path = request.url.path
    # ── IP allowlist (empty = allow all; localhost is always allowed) ──
    if path.startswith("/api/") and not path.startswith("/api/pay/"):
        _allow = _get_ip_allowlist()
        if _allow:
            _client_ip = client_ip(request)
            _allowed = {p.strip() for p in _allow.split(",") if p.strip()}
            if _client_ip not in _allowed and _client_ip not in ("127.0.0.1", "::1", "localhost"):
                return JSONResponse({"detail": "Access from this IP is not allowed"}, status_code=403)
    if path.startswith("/api/") and not path.startswith(_PERM_GUARD_SKIP):
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            payload = auth_module.try_decode(auth_header[7:])
            if payload is not None:
                if payload.get("purpose", "full") != "full":
                    return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)
                if auth_module.session_revoked(payload):
                    return JSONResponse({"detail": "Session revoked"}, status_code=401)
                perm = auth_module.permission_for_path(path)
                if perm and not auth_module.payload_has_perm(payload, perm):
                    return JSONResponse({"detail": "You don't have access to this section"}, status_code=403)
    return await call_next(request)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/upload-media")
async def upload_media(
    file: UploadFile = File(...),
    _: str = Depends(verify_token)
):
    """Upload a file to Telegram and return the file_id.
    The file is sent to a special admin chat (the first ADMIN_ID) as a document/photo/video.
    """
    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        raise HTTPException(status_code=500, detail="BOT_TOKEN not configured")

    # Determine media type from content type
    content_type = file.content_type or ""
    if content_type.startswith("image/"):
        tg_method = "sendPhoto"
        field_name = "photo"
        media_type = "photo"
    elif content_type.startswith("video/"):
        tg_method = "sendVideo"
        field_name = "video"
        media_type = "video"
    else:
        tg_method = "sendDocument"
        field_name = "document"
        media_type = "document"

    # Get admin chat ID from config
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
        from config import ADMIN_IDS
        chat_id = ADMIN_IDS[0] if ADMIN_IDS else None
    except Exception:
        chat_id = None

    if not chat_id:
        raise HTTPException(status_code=500, detail="No admin chat ID configured")

    try:
        file_bytes = await file.read()
        resp = _requests.post(
            f"https://api.telegram.org/bot{bot_token}/{tg_method}",
            data={"chat_id": chat_id, "caption": f"📎 Broadcast media upload"},
            files={field_name: (file.filename, file_bytes, content_type)},
            timeout=30
        ).json()

        if not resp.get("ok"):
            raise HTTPException(status_code=400, detail=f"Telegram error: {resp.get('description', 'Unknown error')}")

        result = resp["result"]
        # Extract file_id based on media type
        if media_type == "photo":
            file_id = result["photo"][-1]["file_id"]
        elif media_type == "video":
            file_id = result["video"]["file_id"]
        else:
            file_id = result["document"]["file_id"]

        return {
            "success": True,
            "file_id": file_id,
            "media_type": media_type,
            "filename": file.filename,
            "size": len(file_bytes),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {e}")


@app.get("/api/tg-file/{file_id}")
def get_telegram_file(file_id: str, _: str = Depends(verify_token)):
    """Proxy a Telegram file by file_id — returns the image bytes."""
    bot_token = os.environ.get("BOT_TOKEN", "")
    if not bot_token:
        raise HTTPException(status_code=500, detail="BOT_TOKEN not configured")
    try:
        # Step 1: Get file path from Telegram
        resp = _requests.get(
            f"https://api.telegram.org/bot{bot_token}/getFile",
            params={"file_id": file_id},
            timeout=10
        ).json()
        if not resp.get("ok"):
            raise HTTPException(status_code=404, detail="File not found in Telegram")
        file_path = resp["result"]["file_path"]
        # Step 2: Download the file
        file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        file_resp = _requests.get(file_url, timeout=15, stream=True)
        content_type = file_resp.headers.get("content-type", "image/jpeg")
        return StreamingResponse(
            file_resp.iter_content(chunk_size=8192),
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch file: {e}")


# ── Serve React build in production ──
panel_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "panel", "dist")
if os.path.exists(panel_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(panel_dist, "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_react(full_path: str):
        # Never swallow unknown API routes: answering with index.html and
        # HTTP 200 makes the frontend try to JSON.parse an HTML document.
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        index = os.path.join(panel_dist, "index.html")
        return FileResponse(index)


# ── Startup ──
# @app.on_event is deprecated in current FastAPI releases; this handler is
# registered explicitly at the bottom of this module instead.
def startup():
    db.init_db()
    # Enable WAL mode for better concurrent access
    with db.get_db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
    print("✅ Admin Panel API started")
    print(f"📖 Docs: http://localhost:{os.environ.get('PANEL_PORT', 8000)}/docs")


app.add_event_handler("startup", startup)
