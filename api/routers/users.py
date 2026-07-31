from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Optional
from api.auth import verify_token
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/users", tags=["users"])


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


@router.get("")
def list_users(
    offset: int = 0,
    limit: int = 20,
    status: Optional[str] = None,   # "active" | "blocked"
    lang: Optional[str] = None,     # "fa" | "en"
    sort: Optional[str] = None,     # "balance" | "joined" | "orders"
    _: str = Depends(verify_token)
):
    with db.get_db() as conn:
        where = ["1=1"]
        params = []
        if status == "blocked":
            where.append("blocked=1")
        elif status == "active":
            where.append("blocked=0")
        if lang:
            where.append("lang=?")
            params.append(lang)

        order = "joined_at DESC"
        if sort == "balance":
            order = "balance DESC"
        elif sort == "orders":
            order = "(SELECT COUNT(*) FROM orders o WHERE o.user_id=users.user_id) DESC"

        total = conn.execute(
            f"SELECT COUNT(*) c FROM users WHERE {' AND '.join(where)}", params
        ).fetchone()["c"]

        rows = conn.execute(
            f"SELECT * FROM users WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()

    return {"total": total, "users": [row_to_dict(u) for u in rows]}


@router.get("/stats")
def get_user_stats_chart(_: str = Depends(verify_token)):
    """User growth chart + language distribution."""
    with db.get_db() as conn:
        # Daily new users for last 14 days
        growth = conn.execute("""
            SELECT date(joined_at) as day, COUNT(*) as count
            FROM users
            WHERE joined_at >= date('now', '-13 days')
            GROUP BY date(joined_at)
            ORDER BY day ASC
        """).fetchall()

        # Language distribution
        langs = conn.execute("""
            SELECT COALESCE(lang, 'unknown') as lang, COUNT(*) as count
            FROM users
            GROUP BY lang
        """).fetchall()

        # Top spenders
        top_spenders = conn.execute("""
            SELECT u.user_id, u.username, u.balance,
                   COALESCE(SUM(o.price), 0) as total_spent,
                   COUNT(o.id) as order_count
            FROM users u
            LEFT JOIN orders o ON u.user_id = o.user_id
            GROUP BY u.user_id
            ORDER BY total_spent DESC
            LIMIT 5
        """).fetchall()

        # Fill missing days
        from datetime import date, timedelta
        result = {}
        for i in range(14):
            d = (date.today() - timedelta(days=13-i)).isoformat()
            result[d] = {"day": d, "count": 0}
        for row in growth:
            result[row["day"]] = {"day": row["day"], "count": row["count"]}

    return {
        "growth": list(result.values()),
        "languages": [row_to_dict(r) for r in langs],
        "top_spenders": [row_to_dict(r) for r in top_spenders],
    }


@router.get("/export.csv")
def export_users_csv(_: str = Depends(verify_token)):
    """Export all users as CSV."""
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT user_id, username, balance, lang, blocked, joined_at, ref_earnings "
            "FROM users ORDER BY joined_at DESC"
        ).fetchall()

    lines = ["user_id,username,balance,lang,blocked,joined_at,ref_earnings"]
    for r in rows:
        lines.append(
            f"{r['user_id']},{r['username'] or ''},"
            f"{r['balance']},{r['lang'] or ''},"
            f"{r['blocked']},{r['joined_at']},{r['ref_earnings']}"
        )
    csv_content = "\n".join(lines)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users.csv"}
    )


@router.get("/{uid}")
def get_user(uid: int, _: str = Depends(verify_token)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    stats = db.get_user_stats(uid)
    orders = db.get_orders(uid, 10)
    # Get user's transactions
    with db.get_db() as conn:
        transactions = conn.execute(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (uid,)
        ).fetchall()
        tickets = conn.execute(
            "SELECT id, subject, status, created_at FROM tickets WHERE user_id=? ORDER BY id DESC LIMIT 5",
            (uid,)
        ).fetchall()
    return {
        "user": row_to_dict(user),
        "stats": row_to_dict(stats),
        "recent_orders": [row_to_dict(o) for o in orders],
        "recent_transactions": [row_to_dict(t) for t in transactions],
        "recent_tickets": [row_to_dict(t) for t in tickets],
    }


class BalanceRequest(BaseModel):
    amount: float
    operation: Optional[str] = "add"  # "add" | "subtract" | "set"


@router.post("/{uid}/balance")
def update_balance(uid: int, body: BalanceRequest, _: str = Depends(verify_token)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.operation == "subtract":
        if user["balance"] < body.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")
        db.add_balance(uid, -body.amount)
    elif body.operation == "set":
        with db.get_db() as conn:
            conn.execute("UPDATE users SET balance=? WHERE user_id=?", (body.amount, uid))
    else:  # add
        db.add_balance(uid, body.amount)

    updated = db.get_user(uid)
    return {"success": True, "new_balance": updated["balance"]}


@router.post("/{uid}/block")
def toggle_block(uid: int, _: str = Depends(verify_token)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_status = 0 if user["blocked"] else 1
    db.set_blocked(uid, new_status)
    return {"success": True, "blocked": bool(new_status)}


class NoteRequest(BaseModel):
    note: str


@router.post("/{uid}/note")
def set_note(uid: int, body: NoteRequest, _: str = Depends(verify_token)):
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.set_user_note(uid, body.note)
    return {"success": True}


class MessageRequest(BaseModel):
    message: str


@router.post("/{uid}/message")
def send_message_to_user(uid: int, body: MessageRequest, _: str = Depends(verify_token)):
    """Queue a direct message to a specific user (bot picks it up)."""
    user = db.get_user(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Store in settings as a pending direct message
    import json, time
    key = f"pending_dm_{uid}_{int(time.time())}"
    db.set_setting(key, json.dumps({"user_id": uid, "message": body.message}))
    return {"success": True, "note": "Message queued for delivery by the bot"}


@router.get("/search/{query}")
def search_users(query: str, _: str = Depends(verify_token)):
    results = db.search_users(query)
    return {"users": [row_to_dict(u) for u in results]}
