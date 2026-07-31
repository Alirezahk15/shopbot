from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from api.auth import verify_token, PANEL_PASSWORD, require_super
from api import auth as auth_module
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db
from config import ADMIN_IDS

router = APIRouter(prefix="/api/admins", tags=["admins"])

ALL_PERMISSIONS = ["products", "users", "payments", "tickets", "discounts", "warranty", "broadcast", "settings"]


# Columns that must never leave the API
SENSITIVE_COLS = {"panel_password_hash", "totp_secret", "totp_pending_secret", "reset_code_hash", "reset_code_expires"}


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for key in SENSITIVE_COLS:
        d.pop(key, None)
    return d


def log_action(admin_id: int, action: str, detail: str = ""):
    """Record an admin action in the activity log."""
    try:
        with db.get_db() as conn:
            conn.execute(
                "INSERT INTO admin_logs (admin_id, action, detail) VALUES (?,?,?)",
                (admin_id, action, detail)
            )
    except Exception:
        pass


@router.get("")
def list_admins(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        admins = conn.execute(
            "SELECT a.*, u.username FROM admins a "
            "LEFT JOIN users u ON a.user_id = u.user_id "
            "ORDER BY a.added_at DESC"
        ).fetchall()
    return {"admins": [row_to_dict(a) for a in admins]}


@router.get("/logs")
def get_activity_logs(limit: int = 50, admin_id: Optional[int] = None, _: str = Depends(verify_token)):
    """Get admin activity log."""
    with db.get_db() as conn:
        if admin_id:
            rows = conn.execute(
                "SELECT l.*, a.permissions FROM admin_logs l "
                "LEFT JOIN admins a ON l.admin_id = a.user_id "
                "WHERE l.admin_id=? ORDER BY l.id DESC LIMIT ?",
                (admin_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT l.*, a.permissions FROM admin_logs l "
                "LEFT JOIN admins a ON l.admin_id = a.user_id "
                "ORDER BY l.id DESC LIMIT ?",
                (limit,)
            ).fetchall()
    return {"logs": [row_to_dict(r) for r in rows]}


@router.get("/stats")
def get_admin_stats(_: str = Depends(verify_token)):
    """Get performance stats for each admin."""
    with db.get_db() as conn:
        admins = conn.execute(
            "SELECT a.*, u.username FROM admins a LEFT JOIN users u ON a.user_id = u.user_id"
        ).fetchall()
        result = []
        for a in admins:
            uid = a["user_id"]
            tickets_replied = conn.execute(
                "SELECT COUNT(*) c FROM admin_logs WHERE admin_id=? AND action='ticket_reply'", (uid,)
            ).fetchone()["c"]
            payments_approved = conn.execute(
                "SELECT COUNT(*) c FROM admin_logs WHERE admin_id=? AND action='payment_approve'", (uid,)
            ).fetchone()["c"]
            payments_rejected = conn.execute(
                "SELECT COUNT(*) c FROM admin_logs WHERE admin_id=? AND action='payment_reject'", (uid,)
            ).fetchone()["c"]
            warranty_processed = conn.execute(
                "SELECT COUNT(*) c FROM admin_logs WHERE admin_id=? AND action LIKE 'warranty_%'", (uid,)
            ).fetchone()["c"]
            total_actions = conn.execute(
                "SELECT COUNT(*) c FROM admin_logs WHERE admin_id=?", (uid,)
            ).fetchone()["c"]
            result.append({
                **row_to_dict(a),
                "tickets_replied": tickets_replied,
                "payments_approved": payments_approved,
                "payments_rejected": payments_rejected,
                "warranty_processed": warranty_processed,
                "total_actions": total_actions,
            })
    return {"stats": result}


class AddAdminRequest(BaseModel):
    user_id: int
    permissions: Optional[str] = "all"
    expires_at: Optional[str] = None  # ISO date string or None
    notify_prefs: Optional[str] = "all"


@router.post("")
def add_admin(body: AddAdminRequest, _: str = Depends(verify_token)):
    is_super = 1 if body.permissions == "all" else 0
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO admins (user_id, is_super, permissions, expires_at, notify_prefs) VALUES (?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET is_super=excluded.is_super, permissions=excluded.permissions, "
            "expires_at=excluded.expires_at, notify_prefs=excluded.notify_prefs",
            (body.user_id, is_super, body.permissions, body.expires_at, body.notify_prefs or "all")
        )
    log_action(0, "admin_add", f"Added admin {body.user_id} with perms={body.permissions}")
    return {"success": True}


class UpdateAdminRequest(BaseModel):
    permissions: Optional[str] = None
    expires_at: Optional[str] = None
    notify_prefs: Optional[str] = None


@router.put("/{user_id}")
def update_admin(user_id: int, body: UpdateAdminRequest, _: str = Depends(verify_token)):
    adm = db.get_admin(user_id)
    if not adm:
        raise HTTPException(status_code=404, detail="Admin not found")

    updates = {}
    if body.permissions is not None:
        updates["permissions"] = body.permissions
        updates["is_super"] = 1 if body.permissions == "all" else 0
    if body.expires_at is not None:
        updates["expires_at"] = body.expires_at if body.expires_at else None
    if body.notify_prefs is not None:
        updates["notify_prefs"] = body.notify_prefs

    if updates:
        sets = ", ".join(f"{k}=?" for k in updates)
        with db.get_db() as conn:
            conn.execute(f"UPDATE admins SET {sets} WHERE user_id=?", (*updates.values(), user_id))

    log_action(0, "admin_update", f"Updated admin {user_id}: {updates}")
    return {"success": True}


@router.delete("/{user_id}")
def delete_admin(user_id: int, _: str = Depends(verify_token)):
    if user_id in ADMIN_IDS:
        raise HTTPException(status_code=400, detail="Cannot delete main admin")
    adm = db.get_admin(user_id)
    if not adm:
        raise HTTPException(status_code=404, detail="Admin not found")
    db.delete_admin(user_id)
    log_action(0, "admin_remove", f"Removed admin {user_id}")
    return {"success": True}


class CredentialsRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    reset_totp: Optional[bool] = False


@router.patch("/{user_id}/credentials")
def set_panel_credentials(user_id: int, body: CredentialsRequest, payload: dict = Depends(require_super)):
    """Set the panel username/password for an admin (super admin only)."""
    with db.get_db() as conn:
        row = conn.execute("SELECT * FROM admins WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            if user_id in ADMIN_IDS:
                conn.execute(
                    "INSERT OR IGNORE INTO admins (user_id, is_super, permissions) VALUES (?,1,'all')",
                    (user_id,)
                )
            else:
                raise HTTPException(status_code=404, detail="Admin not found")

        updates, values = [], []
        if body.username is not None:
            uname = body.username.strip()
            if uname:
                if len(uname) < 3:
                    raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
                dup = conn.execute(
                    "SELECT user_id FROM admins WHERE lower(panel_username)=lower(?) AND user_id<>?",
                    (uname, user_id)
                ).fetchone()
                if dup:
                    raise HTTPException(status_code=400, detail="Username already taken")
                updates.append("panel_username=?")
                values.append(uname)
            else:
                updates.append("panel_username=NULL")
        if body.password:
            if len(body.password) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
            updates.append("panel_password_hash=?")
            values.append(auth_module.hash_password(body.password))
        if body.reset_totp:
            updates.append("totp_enabled=0")
            updates.append("totp_secret=''")
            updates.append("totp_pending_secret=''")
        if updates:
            conn.execute(f"UPDATE admins SET {', '.join(updates)} WHERE user_id=?", (*values, user_id))

    log_action(payload.get("uid") or 0, "admin_credentials", f"Updated panel credentials for {user_id}")
    return {"success": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
def change_panel_password(body: ChangePasswordRequest, _: str = Depends(verify_token)):
    """Change the panel admin password (stored in .env)."""
    if body.current_password != PANEL_PASSWORD:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    # Update the .env file
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Replace PANEL_PASSWORD line
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

        # Update in-memory value
        auth_module.PANEL_PASSWORD = body.new_password
        os.environ["PANEL_PASSWORD"] = body.new_password

        log_action(0, "password_change", "Panel password changed")
        return {"success": True, "note": "Password updated. Please log in again."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update .env: {e}")


@router.get("/check-expired")
def check_expired_admins(_: str = Depends(verify_token)):
    """Check and remove expired temporary admins."""
    from datetime import date
    today = date.today().isoformat()
    with db.get_db() as conn:
        expired = conn.execute(
            "SELECT user_id FROM admins WHERE expires_at IS NOT NULL AND expires_at < ? AND user_id NOT IN ({})".format(
                ",".join(str(i) for i in ADMIN_IDS)
            ),
            (today,)
        ).fetchall()
        removed = []
        for row in expired:
            conn.execute("DELETE FROM admins WHERE user_id=?", (row["user_id"],))
            removed.append(row["user_id"])
    return {"removed": removed, "count": len(removed)}
