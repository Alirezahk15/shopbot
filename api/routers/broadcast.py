from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from api.auth import verify_token
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/broadcast", tags=["broadcast"])


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


# ── History ──

@router.get("/history")
def get_history(limit: int = 20, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM broadcast_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"history": [row_to_dict(r) for r in rows]}


@router.delete("/history/{bid}")
def delete_history(bid: int, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        conn.execute("DELETE FROM broadcast_history WHERE id=?", (bid,))
    return {"success": True}


# ── Templates ──

@router.get("/templates")
def list_templates(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        rows = conn.execute("SELECT * FROM broadcast_templates ORDER BY id DESC").fetchall()
    return {"templates": [row_to_dict(r) for r in rows]}


class TemplateRequest(BaseModel):
    title: str
    message: str
    media_type: Optional[str] = "text"
    media_url: Optional[str] = ""


@router.post("/templates")
def add_template(body: TemplateRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        conn.execute(
            "INSERT INTO broadcast_templates (title, message, media_type, media_url) VALUES (?,?,?,?)",
            (body.title, body.message, body.media_type or "text", body.media_url or "")
        )
    return {"success": True}


@router.delete("/templates/{tid}")
def delete_template(tid: int, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        conn.execute("DELETE FROM broadcast_templates WHERE id=?", (tid,))
    return {"success": True}


# ── Stats ──

@router.get("/stats")
def get_stats(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        summary = conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN status='sent' THEN 1 END) as sent,
                COUNT(CASE WHEN status='pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status='cancelled' THEN 1 END) as cancelled,
                COALESCE(SUM(user_count), 0) as total_users_reached,
                COALESCE(SUM(success_count), 0) as total_success
            FROM broadcast_history
        """).fetchone()
    return {"summary": row_to_dict(summary)}


# ── Send / Schedule ──

class BroadcastRequest(BaseModel):
    message: str
    media_type: Optional[str] = "text"   # "text" | "photo" | "video" | "document"
    media_url: Optional[str] = ""         # URL or Telegram file_id
    target_filter: Optional[str] = "all" # "all" | "fa" | "en" | "has_balance" | "has_orders"
    button_text: Optional[str] = ""       # Inline button text
    button_url: Optional[str] = ""        # Inline button URL
    scheduled_at: Optional[str] = None    # ISO datetime or None for immediate


@router.post("")
def send_broadcast(body: BroadcastRequest, _: str = Depends(verify_token)):
    """Queue a broadcast message."""
    # Count target users
    with db.get_db() as conn:
        if body.target_filter == "fa":
            users = conn.execute("SELECT user_id FROM users WHERE blocked=0 AND lang='fa'").fetchall()
        elif body.target_filter == "en":
            users = conn.execute("SELECT user_id FROM users WHERE blocked=0 AND lang='en'").fetchall()
        elif body.target_filter == "has_balance":
            users = conn.execute("SELECT user_id FROM users WHERE blocked=0 AND balance > 0").fetchall()
        elif body.target_filter == "has_orders":
            users = conn.execute(
                "SELECT DISTINCT u.user_id FROM users u "
                "JOIN orders o ON u.user_id=o.user_id WHERE u.blocked=0"
            ).fetchall()
        else:
            users = conn.execute("SELECT user_id FROM users WHERE blocked=0").fetchall()

        user_count = len(users)

        # Save to broadcast_history
        cur = conn.execute(
            "INSERT INTO broadcast_history "
            "(message, media_type, media_url, target_filter, button_text, button_url, "
            "scheduled_at, user_count, status) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                body.message,
                body.media_type or "text",
                body.media_url or "",
                body.target_filter or "all",
                body.button_text or "",
                body.button_url or "",
                body.scheduled_at,
                user_count,
                "pending" if body.scheduled_at else "queued",
            )
        )
        broadcast_id = cur.lastrowid

        # Store as pending broadcast for the bot to pick up
        # Use the same connection to avoid database lock conflicts
        broadcast_data = {
            "id": broadcast_id,
            "message": body.message,
            "media_type": body.media_type or "text",
            "media_url": body.media_url or "",
            "target_filter": body.target_filter or "all",
            "button_text": body.button_text or "",
            "button_url": body.button_url or "",
            "user_ids": [u["user_id"] for u in users],
        }

        if not body.scheduled_at:
            # Use same connection to avoid "database is locked" error
            broadcast_json = json.dumps(broadcast_data)
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
                ("pending_broadcast_v2", broadcast_json)
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
                ("pending_broadcast_id", str(broadcast_id))
            )

    return {
        "success": True,
        "broadcast_id": broadcast_id,
        "user_count": user_count,
        "scheduled": bool(body.scheduled_at),
        "note": "Broadcast queued. The bot will send it on next check." if not body.scheduled_at else f"Scheduled for {body.scheduled_at}",
    }


@router.post("/{bid}/cancel")
def cancel_broadcast(bid: int, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        bcast = conn.execute("SELECT * FROM broadcast_history WHERE id=?", (bid,)).fetchone()
        if not bcast:
            raise HTTPException(status_code=404, detail="Broadcast not found")
        if bcast["status"] == "sent":
            raise HTTPException(status_code=400, detail="Cannot cancel a sent broadcast")
        conn.execute("UPDATE broadcast_history SET status='cancelled' WHERE id=?", (bid,))

    # Clear pending broadcast if it's the current one
    with db.get_db() as conn:
        current_id = conn.execute("SELECT value FROM settings WHERE key='pending_broadcast_id'").fetchone()
        if current_id and current_id["value"] == str(bid):
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('pending_broadcast_v2', '')")
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('pending_broadcast_id', '')")

    return {"success": True}


@router.get("/status")
def get_broadcast_status(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        pending_row = conn.execute("SELECT value FROM settings WHERE key='pending_broadcast_v2'").fetchone()
        pending_id_row = conn.execute("SELECT value FROM settings WHERE key='pending_broadcast_id'").fetchone()
    pending = pending_row["value"] if pending_row else ""
    pending_id = pending_id_row["value"] if pending_id_row else ""
    if pending:
        try:
            data = json.loads(pending)
            return {
                "pending": True,
                "broadcast_id": pending_id,
                "user_count": len(data.get("user_ids", [])),
                "target_filter": data.get("target_filter", "all"),
                "media_type": data.get("media_type", "text"),
            }
        except Exception:
            pass
    return {"pending": False}
