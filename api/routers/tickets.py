from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, List
from api.auth import verify_token
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db
from lang import t

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _queue_dm(uid, message, suffix=""):
    """قرار دادن یک پیام در صف ارسال تا ربات به محض روشن شدن ارسال شود"""
    key = f"pending_dm_{uid}_{int(time.time()*1000)}{suffix}"
    db.set_setting(key, json.dumps({"user_id": uid, "message": message}))


def _user_lang(uid):
    u = db.get_user(uid)
    return (u["lang"] if u and u["lang"] else "fa")


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


@router.get("")
def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort: Optional[str] = None,  # "newest" | "oldest" | "priority"
    user_id: Optional[int] = None,
    _: str = Depends(verify_token)
):
    with db.get_db() as conn:
        where = ["1=1"]
        params = []

        if status:
            where.append("t.status=?")
            params.append(status)
        if priority:
            where.append("t.priority=?")
            params.append(priority)
        if search:
            where.append("(t.subject LIKE ? OR t.message LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if tag:
            where.append("t.tags LIKE ?")
            params.append(f"%{tag}%")
        if date_from:
            where.append("date(t.created_at) >= ?")
            params.append(date_from)
        if date_to:
            where.append("date(t.created_at) <= ?")
            params.append(date_to)
        if user_id:
            where.append("t.user_id=?")
            params.append(user_id)

        order = "t.id DESC"
        if sort == "oldest":
            order = "t.id ASC"
        elif sort == "priority":
            order = "CASE t.priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'normal' THEN 2 END ASC, t.id DESC"

        rows = conn.execute(
            f"SELECT t.*, u.username FROM tickets t "
            f"JOIN users u ON t.user_id=u.user_id "
            f"WHERE {' AND '.join(where)} ORDER BY {order}",
            params
        ).fetchall()

    return {"tickets": [row_to_dict(r) for r in rows]}


@router.get("/stats")
def get_ticket_stats(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        summary = conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN status='open' THEN 1 END) as open,
                COUNT(CASE WHEN status='answered' THEN 1 END) as answered,
                COUNT(CASE WHEN status='closed' THEN 1 END) as closed,
                COUNT(CASE WHEN priority='urgent' THEN 1 END) as urgent,
                COUNT(CASE WHEN priority='high' THEN 1 END) as high_priority,
                COUNT(CASE WHEN date(created_at)=date('now') THEN 1 END) as today
            FROM tickets
        """).fetchone()

        # Daily tickets for last 14 days
        daily = conn.execute("""
            SELECT date(created_at) as day, COUNT(*) as count
            FROM tickets
            WHERE created_at >= date('now', '-13 days')
            GROUP BY date(created_at)
            ORDER BY day ASC
        """).fetchall()

        # Avg response time (for answered tickets)
        avg_resp = conn.execute("""
            SELECT AVG(
                (julianday(replied_at) - julianday(created_at)) * 24
            ) as avg_hours
            FROM tickets
            WHERE status IN ('answered', 'closed') AND replied_at != ''
        """).fetchone()

        # Fill missing days
        from datetime import date, timedelta
        result = {}
        for i in range(14):
            d = (date.today() - timedelta(days=13-i)).isoformat()
            result[d] = {"day": d, "count": 0}
        for row in daily:
            result[row["day"]] = {"day": row["day"], "count": row["count"]}

    return {
        "summary": row_to_dict(summary),
        "daily": list(result.values()),
        "avg_response_hours": round(avg_resp["avg_hours"] or 0, 1),
    }


@router.get("/export.csv")
def export_tickets_csv(status: Optional[str] = None, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        where = "1=1"
        params = []
        if status:
            where = "t.status=?"
            params.append(status)
        rows = conn.execute(
            f"SELECT t.id, t.user_id, u.username, t.subject, t.status, t.priority, t.tags, t.created_at "
            f"FROM tickets t JOIN users u ON t.user_id=u.user_id "
            f"WHERE {where} ORDER BY t.id DESC",
            params
        ).fetchall()

    lines = ["id,user_id,username,subject,status,priority,tags,date"]
    for r in rows:
        lines.append(
            f"{r['id']},{r['user_id']},{r['username'] or ''},"
            f"\"{r['subject']}\",{r['status']},{r['priority'] or 'normal'},"
            f"\"{r['tags'] or ''}\",{r['created_at']}"
        )
    return Response(
        content="\n".join(lines),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tickets.csv"}
    )


@router.get("/quick-replies")
def list_quick_replies(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        rows = conn.execute("SELECT * FROM ticket_quick_replies ORDER BY id DESC").fetchall()
    return {"quick_replies": [row_to_dict(r) for r in rows]}


class QuickReplyRequest(BaseModel):
    title: str
    content: str


@router.post("/quick-replies")
def add_quick_reply(body: QuickReplyRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        conn.execute("INSERT INTO ticket_quick_replies (title, content) VALUES (?,?)", (body.title, body.content))
    return {"success": True}


@router.delete("/quick-replies/{qr_id}")
def delete_quick_reply(qr_id: int, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        conn.execute("DELETE FROM ticket_quick_replies WHERE id=?", (qr_id,))
    return {"success": True}


@router.get("/{tid}")
def get_ticket(tid: int, _: str = Depends(verify_token)):
    ticket = db.get_ticket(tid)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return row_to_dict(ticket)


class ReplyRequest(BaseModel):
    reply: str


@router.post("/{tid}/reply")
def reply_ticket(tid: int, body: ReplyRequest, _: str = Depends(verify_token)):
    ticket = db.get_ticket(tid)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.reply_ticket(tid, body.reply)
    target_lang = _user_lang(ticket["user_id"])
    _queue_dm(ticket["user_id"], t("adm_ticket_reply_notify", target_lang, id=tid, reply=body.reply), f"_t{tid}")
    return {"success": True}


@router.post("/{tid}/close")
def close_ticket(tid: int, _: str = Depends(verify_token)):
    ticket = db.get_ticket(tid)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.close_ticket(tid)
    return {"success": True}


class UpdateTicketRequest(BaseModel):
    priority: Optional[str] = None    # "normal" | "high" | "urgent"
    tags: Optional[str] = None        # comma-separated tags
    internal_note: Optional[str] = None
    assigned_to: Optional[int] = None
    status: Optional[str] = None


@router.put("/{tid}")
def update_ticket(tid: int, body: UpdateTicketRequest, _: str = Depends(verify_token)):
    ticket = db.get_ticket(tid)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    updates = {}
    if body.priority is not None:
        if body.priority not in ("normal", "high", "urgent"):
            raise HTTPException(status_code=400, detail="Priority must be normal, high, or urgent")
        updates["priority"] = body.priority
    if body.tags is not None:
        updates["tags"] = body.tags
    if body.internal_note is not None:
        updates["internal_note"] = body.internal_note
    if body.assigned_to is not None:
        updates["assigned_to"] = body.assigned_to
    if body.status is not None:
        updates["status"] = body.status

    if updates:
        with db.get_db() as conn:
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE tickets SET {sets} WHERE id=?", (*updates.values(), tid))

    return {"success": True}


class TransferRequest(BaseModel):
    admin_id: int
    note: Optional[str] = ""


@router.post("/{tid}/transfer")
def transfer_ticket(tid: int, body: TransferRequest, _: str = Depends(verify_token)):
    """Assign ticket to a different admin."""
    ticket = db.get_ticket(tid)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    admin = db.get_admin(body.admin_id)
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    with db.get_db() as conn:
        conn.execute("UPDATE tickets SET assigned_to=? WHERE id=?", (body.admin_id, tid))
        if body.note:
            # Append to internal note
            existing = ticket.get("internal_note", "") or ""
            new_note = f"{existing}\n[Transfer to {body.admin_id}]: {body.note}".strip()
            conn.execute("UPDATE tickets SET internal_note=? WHERE id=?", (new_note, tid))

    return {"success": True}
