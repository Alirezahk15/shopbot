from fastapi import APIRouter, Depends
from api.auth import verify_token
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/funnel")
def funnel(days: int = 30, _: str = Depends(verify_token)):
    """قیف فروش: تعداد کاربران یکتا در هر مرحله از مسیر خرید"""
    days = max(1, min(int(days), 365))
    out = {}
    with db.get_db() as conn:
        for ev in ("start", "view_product", "buy_click", "purchase"):
            out[ev] = conn.execute(
                "SELECT COUNT(DISTINCT user_id) c FROM events "
                "WHERE event=? AND created_at >= datetime('now', ?)",
                (ev, f"-{days} days")).fetchone()["c"]
    out["days"] = days
    return out


@router.get("/stock-forecast")
def stock_forecast(_: str = Depends(verify_token)):
    """پیش‌بینی اتمام موجودی بر اساس سرعت فروش ۷ روز اخیر"""
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT p.id, p.name, "
            "(SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.is_sold=0) stock_count, "
            "(SELECT COALESCE(SUM(o.quantity),0) FROM orders o WHERE o.product_id=p.id "
            " AND o.created_at >= datetime('now','-7 days')) sold_7d "
            "FROM products p WHERE p.active=1").fetchall()
    out = []
    for r in rows:
        velocity = round((r["sold_7d"] or 0) / 7.0, 2)
        days_left = round(r["stock_count"] / velocity, 1) if velocity > 0 else None
        out.append({"id": r["id"], "name": r["name"], "stock": r["stock_count"],
                    "sold_7d": r["sold_7d"], "velocity_per_day": velocity,
                    "days_left": days_left})
    out.sort(key=lambda x: (x["days_left"] is None,
                            x["days_left"] if x["days_left"] is not None else 1e9))
    return {"forecast": out}


@router.get("/ratings")
def ratings(_: str = Depends(verify_token)):
    """میانگین امتیاز محصولات از دید خریداران"""
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT p.id, p.name, ROUND(AVG(r.stars),1) avg_stars, COUNT(r.id) votes "
            "FROM ratings r JOIN products p ON r.product_id=p.id "
            "GROUP BY p.id, p.name ORDER BY avg_stars DESC").fetchall()
    return {"ratings": [dict(r) for r in rows]}
