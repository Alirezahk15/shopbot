from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Optional
from api.auth import verify_token
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/orders", tags=["orders"])


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


@router.get("")
def list_orders(
    offset: int = 0,
    limit: int = 20,
    search: Optional[str] = None,       # search by username or user_id
    product_id: Optional[int] = None,
    date_from: Optional[str] = None,    # YYYY-MM-DD
    date_to: Optional[str] = None,
    sort: Optional[str] = None,         # "price" | "date"
    _: str = Depends(verify_token)
):
    with db.get_db() as conn:
        where = ["1=1"]
        params = []

        if search:
            # Try numeric (user_id) or string (username)
            try:
                uid = int(search)
                where.append("o.user_id=?")
                params.append(uid)
            except ValueError:
                where.append("u.username LIKE ?")
                params.append(f"%{search}%")

        if product_id:
            where.append("o.product_id=?")
            params.append(product_id)

        if date_from:
            where.append("date(o.created_at) >= ?")
            params.append(date_from)

        if date_to:
            where.append("date(o.created_at) <= ?")
            params.append(date_to)

        order = "o.id DESC"
        if sort == "price":
            order = "o.price DESC"

        total = conn.execute(
            f"SELECT COUNT(*) c FROM orders o "
            f"LEFT JOIN users u ON o.user_id=u.user_id "
            f"WHERE {' AND '.join(where)}",
            params
        ).fetchone()["c"]

        rows = conn.execute(
            f"SELECT o.*, COALESCE(p.name, '(deleted)') as product_name, "
            f"COALESCE(p.has_warranty, 0) as has_warranty, "
            f"u.username FROM orders o "
            f"LEFT JOIN products p ON o.product_id=p.id "
            f"LEFT JOIN users u ON o.user_id=u.user_id "
            f"WHERE {' AND '.join(where)} ORDER BY {order} LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()

    return {"total": total, "orders": [row_to_dict(r) for r in rows]}


@router.get("/stats")
def get_order_stats(_: str = Depends(verify_token)):
    """Order stats for charts."""
    with db.get_db() as conn:
        # Daily orders + revenue for last 30 days
        daily = conn.execute("""
            SELECT date(created_at) as day,
                   COUNT(*) as orders,
                   COALESCE(SUM(price), 0) as revenue
            FROM orders
            WHERE created_at >= date('now', '-29 days')
            GROUP BY date(created_at)
            ORDER BY day ASC
        """).fetchall()

        # Summary stats
        summary = conn.execute("""
            SELECT
                COUNT(*) as total_orders,
                COALESCE(SUM(price), 0) as total_revenue,
                COALESCE(AVG(price), 0) as avg_order_value,
                COUNT(DISTINCT user_id) as unique_buyers,
                COUNT(CASE WHEN date(created_at) = date('now') THEN 1 END) as today_orders,
                COALESCE(SUM(CASE WHEN date(created_at) = date('now') THEN price ELSE 0 END), 0) as today_revenue,
                COUNT(CASE WHEN date(created_at) >= date('now', '-7 days') THEN 1 END) as week_orders,
                COALESCE(SUM(CASE WHEN date(created_at) >= date('now', '-7 days') THEN price ELSE 0 END), 0) as week_revenue
            FROM orders
        """).fetchone()

        # Fill missing days
        from datetime import date, timedelta
        result = {}
        for i in range(30):
            d = (date.today() - timedelta(days=29-i)).isoformat()
            result[d] = {"day": d, "orders": 0, "revenue": 0.0}
        for row in daily:
            result[row["day"]] = {"day": row["day"], "orders": row["orders"], "revenue": round(row["revenue"], 2)}

    return {
        "daily": list(result.values()),
        "summary": row_to_dict(summary),
    }


@router.get("/export.csv")
def export_orders_csv(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    _: str = Depends(verify_token)
):
    """Export orders as CSV."""
    with db.get_db() as conn:
        where = ["1=1"]
        params = []
        if date_from:
            where.append("date(o.created_at) >= ?")
            params.append(date_from)
        if date_to:
            where.append("date(o.created_at) <= ?")
            params.append(date_to)

        rows = conn.execute(
            f"SELECT o.id, o.user_id, u.username, "
            f"COALESCE(p.name, '(deleted)') as product_name, "
            f"o.price, o.quantity, o.created_at "
            f"FROM orders o "
            f"LEFT JOIN products p ON o.product_id=p.id "
            f"LEFT JOIN users u ON o.user_id=u.user_id "
            f"WHERE {' AND '.join(where)} ORDER BY o.id DESC",
            params
        ).fetchall()

    lines = ["order_id,user_id,username,product,price,quantity,date"]
    for r in rows:
        lines.append(
            f"{r['id']},{r['user_id']},{r['username'] or ''},"
            f"\"{r['product_name']}\",{r['price']},{r['quantity'] or 1},{r['created_at']}"
        )
    return Response(
        content="\n".join(lines),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders.csv"}
    )


@router.get("/{oid}")
def get_order(oid: int, _: str = Depends(verify_token)):
    order = db.get_order(oid)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    # Get user info
    user = db.get_user(order["user_id"])
    return {
        "order": row_to_dict(order),
        "user": row_to_dict(user),
    }


class ResendRequest(BaseModel):
    message: Optional[str] = None  # custom message, or None to use default


@router.post("/{oid}/resend")
def resend_order_content(oid: int, body: ResendRequest, _: str = Depends(verify_token)):
    """Queue a resend of order content to the user (bot picks it up)."""
    order = db.get_order(oid)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    import json, time
    content = order["delivered_content"] or ""
    message = body.message or f"📦 Order #{oid} resend:\n\n{content}"

    key = f"pending_dm_{order['user_id']}_{int(time.time())}"
    db.set_setting(key, json.dumps({
        "user_id": order["user_id"],
        "message": message,
        "type": "order_resend",
        "order_id": oid,
    }))
    return {"success": True, "note": "Resend queued for delivery by the bot"}
