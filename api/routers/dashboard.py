from fastapi import APIRouter, Depends
from api.auth import verify_token
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def get_dashboard(_: str = Depends(verify_token)):
    stats = db.get_stats()
    return {
        "users": stats["users"],
        "orders": stats["orders"],
        "revenue": stats["revenue"],
        "deposits": stats["deposits"],
        "today_orders": stats["today_orders"],
        "today_revenue": stats["today_revenue"],
        "pending_tickets": stats["pending_tickets"],
        "pending_cards": stats["pending_cards"],
        "pending_warranty": stats["pending_warranty"],
        "blocked_users": stats["blocked_users"],
    }


@router.get("/chart")
def get_chart_data(days: int = 7, _: str = Depends(verify_token)):
    """Returns last N days (7/30/90) of orders and revenue for charts."""
    if days not in (7, 30, 90):
        days = 7

    with db.get_db() as conn:
        rows = conn.execute("""
            SELECT
                date(created_at) as day,
                COUNT(*) as orders,
                COALESCE(SUM(price), 0) as revenue
            FROM orders
            WHERE created_at >= date('now', ?)
            GROUP BY date(created_at)
            ORDER BY day ASC
        """, (f"-{days - 1} days",)).fetchall()

        # Fill missing days with zeros
        from datetime import date, timedelta
        result = {}
        for i in range(days):
            d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
            result[d] = {"day": d, "orders": 0, "revenue": 0.0}
        for row in rows:
            result[row["day"]] = {
                "day": row["day"],
                "orders": row["orders"],
                "revenue": round(row["revenue"], 2),
            }

        # Top products
        top_products = conn.execute("""
            SELECT p.name, COUNT(o.id) as order_count, COALESCE(SUM(o.price), 0) as revenue
            FROM orders o
            JOIN products p ON o.product_id = p.id
            GROUP BY o.product_id
            ORDER BY order_count DESC
            LIMIT 5
        """).fetchall()

        # Recent transactions
        recent_tx = conn.execute("""
            SELECT t.user_id, t.amount, t.method, t.created_at, u.username
            FROM transactions t
            LEFT JOIN users u ON t.user_id = u.user_id
            ORDER BY t.id DESC LIMIT 5
        """).fetchall()

    return {
        "daily": list(result.values()),
        "top_products": [dict(r) for r in top_products],
        "recent_transactions": [dict(r) for r in recent_tx],
    }
