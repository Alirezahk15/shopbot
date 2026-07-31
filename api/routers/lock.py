from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from api.auth import verify_token
import sys, os, requests as _requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/api/lock", tags=["lock"])

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def get_chat_info(chat_id: int) -> dict:
    """Get chat info from Telegram Bot API."""
    if not BOT_TOKEN:
        return {}
    try:
        resp = _requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
            params={"chat_id": chat_id},
            timeout=8
        ).json()
        if resp.get("ok"):
            return resp["result"]
    except Exception:
        pass
    return {}


def get_member_count(chat_id: int) -> int:
    """Get member count from Telegram Bot API."""
    if not BOT_TOKEN:
        return 0
    try:
        resp = _requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMemberCount",
            params={"chat_id": chat_id},
            timeout=8
        ).json()
        if resp.get("ok"):
            return resp["result"]
    except Exception:
        pass
    return 0


@router.get("")
def get_locked(_: str = Depends(verify_token)):
    channels = db.get_locked_channels()
    groups = db.get_locked_groups()
    return {
        "channels": [row_to_dict(c) for c in channels],
        "groups": [row_to_dict(g) for g in groups],
    }


@router.get("/channel/{channel_id}/info")
def get_channel_info(channel_id: int, _: str = Depends(verify_token)):
    """Get live info from Telegram for a locked channel."""
    info = get_chat_info(channel_id)
    member_count = get_member_count(channel_id)
    return {
        "chat_id": channel_id,
        "title": info.get("title", ""),
        "username": info.get("username", ""),
        "invite_link": info.get("invite_link", ""),
        "member_count": member_count,
        "type": info.get("type", ""),
    }


@router.get("/group/{group_id}/info")
def get_group_info(group_id: int, _: str = Depends(verify_token)):
    """Get live info from Telegram for a locked group."""
    info = get_chat_info(group_id)
    member_count = get_member_count(group_id)
    return {
        "chat_id": group_id,
        "title": info.get("title", ""),
        "username": info.get("username", ""),
        "invite_link": info.get("invite_link", ""),
        "member_count": member_count,
        "type": info.get("type", ""),
    }


class LockRequest(BaseModel):
    id: int
    title: Optional[str] = ""
    invite_link: Optional[str] = ""
    custom_message: Optional[str] = ""
    expires_at: Optional[str] = None


@router.post("/channel")
def lock_channel(body: LockRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO locked_channels (channel_id, title, invite_link, custom_message, expires_at) "
            "VALUES (?,?,?,?,?)",
            (body.id, body.title or str(body.id), body.invite_link or "", body.custom_message or "", body.expires_at)
        )
    return {"success": True}


@router.delete("/channel/{channel_id}")
def unlock_channel(channel_id: int, _: str = Depends(verify_token)):
    db.unlock_channel(channel_id)
    return {"success": True}


class UpdateLockRequest(BaseModel):
    title: Optional[str] = None
    invite_link: Optional[str] = None
    custom_message: Optional[str] = None
    expires_at: Optional[str] = None


@router.put("/channel/{channel_id}")
def update_channel(channel_id: int, body: UpdateLockRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        ch = conn.execute("SELECT * FROM locked_channels WHERE channel_id=?", (channel_id,)).fetchone()
        if not ch:
            raise HTTPException(status_code=404, detail="Channel not found")
        updates = {}
        if body.title is not None:
            updates["title"] = body.title
        if body.invite_link is not None:
            updates["invite_link"] = body.invite_link
        if body.custom_message is not None:
            updates["custom_message"] = body.custom_message
        if body.expires_at is not None:
            updates["expires_at"] = body.expires_at if body.expires_at else None
        if updates:
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE locked_channels SET {sets} WHERE channel_id=?", (*updates.values(), channel_id))
    return {"success": True}


@router.post("/group")
def lock_group(body: LockRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO locked_groups (group_id, title, invite_link, custom_message, expires_at) "
            "VALUES (?,?,?,?,?)",
            (body.id, body.title or str(body.id), body.invite_link or "", body.custom_message or "", body.expires_at)
        )
    return {"success": True}


@router.delete("/group/{group_id}")
def unlock_group(group_id: int, _: str = Depends(verify_token)):
    db.unlock_group(group_id)
    return {"success": True}


@router.put("/group/{group_id}")
def update_group(group_id: int, body: UpdateLockRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        gr = conn.execute("SELECT * FROM locked_groups WHERE group_id=?", (group_id,)).fetchone()
        if not gr:
            raise HTTPException(status_code=404, detail="Group not found")
        updates = {}
        if body.title is not None:
            updates["title"] = body.title
        if body.invite_link is not None:
            updates["invite_link"] = body.invite_link
        if body.custom_message is not None:
            updates["custom_message"] = body.custom_message
        if body.expires_at is not None:
            updates["expires_at"] = body.expires_at if body.expires_at else None
        if updates:
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE locked_groups SET {sets} WHERE group_id=?", (*updates.values(), group_id))
    return {"success": True}


@router.get("/check-expired")
def check_expired_locks(_: str = Depends(verify_token)):
    """Remove expired temporary locks."""
    from datetime import date
    today = date.today().isoformat()
    with db.get_db() as conn:
        expired_ch = conn.execute(
            "SELECT channel_id FROM locked_channels WHERE expires_at IS NOT NULL AND expires_at < ?", (today,)
        ).fetchall()
        expired_gr = conn.execute(
            "SELECT group_id FROM locked_groups WHERE expires_at IS NOT NULL AND expires_at < ?", (today,)
        ).fetchall()

        for row in expired_ch:
            conn.execute("DELETE FROM locked_channels WHERE channel_id=?", (row["channel_id"],))
        for row in expired_gr:
            conn.execute("DELETE FROM locked_groups WHERE group_id=?", (row["group_id"],))

    return {
        "removed_channels": [r["channel_id"] for r in expired_ch],
        "removed_groups": [r["group_id"] for r in expired_gr],
        "count": len(expired_ch) + len(expired_gr),
    }
