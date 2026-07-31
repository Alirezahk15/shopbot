"""Authentication & authorization for the admin panel API.

Supports:
- Per-admin username/password login (bcrypt hashed, stored in the admins table)
- TOTP two-factor auth compatible with Google Authenticator (RFC 6238)
- Password reset codes delivered through the Telegram bot
- Permission-based access control per panel section
- Legacy PANEL_PASSWORD login (only while no admin has credentials yet)
"""
import os
import sys
import time
import hmac
import base64
import hashlib
import struct
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import database as db

load_dotenv()

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-set-JWT_SECRET-in-env")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "24"))
PANEL_PASSWORD = os.environ.get("PANEL_PASSWORD", "admin123")

TOTP_ISSUER = os.environ.get("PANEL_2FA_ISSUER", "Shop Bot Panel")

security = HTTPBearer()


# ──────── Password hashing ────────
def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        if not password_hash:
            return False
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("utf-8"))
    except Exception:
        return False


# ──────── TOTP (Google Authenticator compatible) ────────
def generate_totp_secret() -> str:
    """Generate a random base32 secret (160 bits, no padding)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8")


def totp_uri(secret: str, account: str) -> str:
    """otpauth:// URI usable as a QR code in authenticator apps."""
    from urllib.parse import quote
    issuer = quote(TOTP_ISSUER)
    return (
        f"otpauth://totp/{issuer}:{quote(str(account))}"
        f"?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"
    )


def _totp_at(secret: str, counter: int, digits: int = 6) -> str:
    key = base64.b32decode(secret.strip().replace(" ", "").upper())
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(number % (10 ** digits)).zfill(digits)


def verify_totp(secret: str, code: str, window: int = 1, interval: int = 30) -> bool:
    code = str(code or "").strip().replace(" ", "")
    if not secret or not code.isdigit() or len(code) != 6:
        return False
    counter = int(time.time() // interval)
    for offset in range(-window, window + 1):
        try:
            if hmac.compare_digest(_totp_at(secret, counter + offset), code):
                return True
        except Exception:
            return False
    return False


# ──────── Simple in-memory rate limiting ────────
_attempts = {}


def check_rate_limit(key: str, max_attempts: int = 5, window: int = 600) -> bool:
    """Return True if another attempt is allowed for this key."""
    now = time.time()
    stamps = [t for t in _attempts.get(key, []) if now - t < window]
    _attempts[key] = stamps
    return len(stamps) < max_attempts


def record_attempt(key: str):
    _attempts.setdefault(key, []).append(time.time())


def clear_attempts(key: str):
    _attempts.pop(key, None)


# ──────── Admin lookups ────────
def get_admin_row(user_id):
    if user_id is None:
        return None
    with db.get_db() as conn:
        return conn.execute("SELECT * FROM admins WHERE user_id=?", (user_id,)).fetchone()


def get_admin_by_username(username: str):
    if not username:
        return None
    with db.get_db() as conn:
        return conn.execute(
            "SELECT * FROM admins WHERE panel_username IS NOT NULL AND lower(panel_username)=lower(?)",
            (username.strip(),)
        ).fetchone()


def credentialed_admin_count() -> int:
    with db.get_db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM admins "
            "WHERE panel_username IS NOT NULL AND panel_password_hash IS NOT NULL"
        ).fetchone()
        return row["c"] if row else 0


def admin_claims(row) -> dict:
    """Build JWT claims from an admins table row."""
    try:
        from config import ADMIN_IDS
    except Exception:
        ADMIN_IDS = []
    uid = row["user_id"]
    perms = row["permissions"] or "all"
    is_super = bool(row["is_super"]) or uid in ADMIN_IDS or perms == "all"
    return {
        "sub": row["panel_username"] or f"admin-{uid}",
        "uid": uid,
        "is_super": is_super,
        "perms": "all" if is_super else perms,
        "purpose": "full",
    }


def public_admin_info(claims: dict, totp_enabled: bool = False) -> dict:
    """Info that is safe to hand to the frontend after login."""
    return {
        "username": claims.get("sub"),
        "user_id": claims.get("uid"),
        "is_super": bool(claims.get("is_super")),
        "perms": claims.get("perms", "all"),
        "totp_enabled": bool(totp_enabled),
    }


# ──────── Tokens ────────
def create_token(claims: dict = None, hours: float = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        hours=hours if hours is not None else JWT_EXPIRE_HOURS
    )
    payload = {"sub": "admin", "purpose": "full", **(claims or {}), "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def try_decode(token: str):
    """Decode without raising; returns None on failure."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None


def session_revoked(payload: dict) -> bool:
    """Check whether the panel session tied to this token was rejected by an admin."""
    sid = payload.get("sid")
    if not sid:
        return False
    try:
        sess = db.get_panel_session(sid)
    except Exception:
        return False
    return bool(sess and sess.get("status") == "revoked")


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = decode_token(credentials.credentials)
    if payload.get("purpose", "full") != "full":
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if session_revoked(payload):
        raise HTTPException(status_code=401, detail="Session revoked")
    return payload


def require_super(payload: dict = Depends(verify_token)) -> dict:
    if not payload_has_perm(payload, "__super__"):
        raise HTTPException(status_code=403, detail="Super admin access required")
    return payload


# ──────── Section permissions ────────
# Maps API path prefixes to the bot's admin permission keys.
PERM_MAP = (
    ("/api/admins", "__super__"),
    ("/api/users", "users"),
    ("/api/products", "products"),
    ("/api/orders", "products"),
    ("/api/payments", "payments"),
    ("/api/methods", "payments"),
    ("/api/tickets", "tickets"),
    ("/api/discounts", "discounts"),
    ("/api/warranty", "warranty"),
    ("/api/broadcast", "broadcast"),
    ("/api/settings", "settings"),
    ("/api/lock", "settings"),
    ("/api/buttons", "settings"),
    ("/api/faq", "tickets"),
    ("/api/texts", "settings"),
    ("/api/menu-buttons", "settings"),
)


def permission_for_path(path: str):
    for prefix, perm in PERM_MAP:
        if path == prefix or path.startswith(prefix + "/"):
            return perm
    return None


def payload_has_perm(payload: dict, perm: str) -> bool:
    if not perm:
        return True
    if payload.get("is_super"):
        return True
    perms = payload.get("perms") or "all"
    if perms == "all":
        return True
    if perm == "__super__":
        return False
    allowed = {p.strip() for p in str(perms).split(",") if p.strip()}
    return perm in allowed
