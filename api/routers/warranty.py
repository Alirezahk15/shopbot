from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Optional
from api.auth import verify_token
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db
from lang import t

router = APIRouter(prefix="/api/warranty", tags=["warranty"])


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
def list_claims(
    status: Optional[str] = None,
    search: Optional[str] = None,   # user_id or username or product name
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    _: str = Depends(verify_token)
):
    with db.get_db() as conn:
        where = ["1=1"]
        params = []

        if status:
            where.append("wc.status=?")
            params.append(status)

        if search:
            try:
                uid = int(search)
                where.append("wc.user_id=?")
                params.append(uid)
            except ValueError:
                where.append("(u.username LIKE ? OR p.name LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])

        if date_from:
            where.append("date(wc.created_at) >= ?")
            params.append(date_from)

        if date_to:
            where.append("date(wc.created_at) <= ?")
            params.append(date_to)

        rows = conn.execute(
            f"SELECT wc.*, u.username, o.price as order_price, "
            f"COALESCE(p.name, '(deleted)') as product_name, "
            f"o.delivered_content, o.product_id "
            f"FROM warranty_claims wc "
            f"JOIN users u ON wc.user_id=u.user_id "
            f"JOIN orders o ON wc.order_id=o.id "
            f"LEFT JOIN products p ON o.product_id=p.id "
            f"WHERE {' AND '.join(where)} ORDER BY wc.id DESC",
            params
        ).fetchall()

    return {"claims": [row_to_dict(r) for r in rows]}


@router.get("/stats")
def get_warranty_stats(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        summary = conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN status='pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status='approved' THEN 1 END) as approved,
                COUNT(CASE WHEN status='rejected' THEN 1 END) as rejected,
                COUNT(CASE WHEN date(created_at)=date('now') THEN 1 END) as today
            FROM warranty_claims
        """).fetchone()

        # Daily claims for last 14 days
        daily = conn.execute("""
            SELECT date(created_at) as day, COUNT(*) as count
            FROM warranty_claims
            WHERE created_at >= date('now', '-13 days')
            GROUP BY date(created_at)
            ORDER BY day ASC
        """).fetchall()

        # Products with most warranty claims
        top_products = conn.execute("""
            SELECT COALESCE(p.name, '(deleted)') as product_name,
                   COUNT(wc.id) as claim_count
            FROM warranty_claims wc
            JOIN orders o ON wc.order_id = o.id
            LEFT JOIN products p ON o.product_id = p.id
            GROUP BY o.product_id
            ORDER BY claim_count DESC
            LIMIT 5
        """).fetchall()

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
        "top_products": [row_to_dict(r) for r in top_products],
    }


@router.get("/export.csv")
def export_warranty_csv(status: Optional[str] = None, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        where = "1=1"
        params = []
        if status:
            where = "wc.status=?"
            params.append(status)
        rows = conn.execute(
            f"SELECT wc.id, wc.user_id, u.username, "
            f"COALESCE(p.name, '(deleted)') as product_name, "
            f"wc.reason, wc.status, wc.admin_note, wc.created_at "
            f"FROM warranty_claims wc "
            f"JOIN users u ON wc.user_id=u.user_id "
            f"JOIN orders o ON wc.order_id=o.id "
            f"LEFT JOIN products p ON o.product_id=p.id "
            f"WHERE {where} ORDER BY wc.id DESC",
            params
        ).fetchall()

    lines = ["id,user_id,username,product,reason,status,admin_note,date"]
    for r in rows:
        lines.append(
            f"{r['id']},{r['user_id']},{r['username'] or ''},"
            f"\"{r['product_name']}\",\"{r['reason']}\","
            f"{r['status']},\"{r['admin_note'] or ''}\",{r['created_at']}"
        )
    return Response(
        content="\n".join(lines),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=warranty_claims.csv"}
    )


@router.get("/{claim_id}")
def get_claim(claim_id: int, _: str = Depends(verify_token)):
    """Get full details of a warranty claim."""
    with db.get_db() as conn:
        claim = conn.execute(
            "SELECT wc.*, u.username, u.balance, "
            "o.price as order_price, o.delivered_content, o.product_id, o.quantity, "
            "COALESCE(p.name, '(deleted)') as product_name, "
            "p.has_warranty "
            "FROM warranty_claims wc "
            "JOIN users u ON wc.user_id=u.user_id "
            "JOIN orders o ON wc.order_id=o.id "
            "LEFT JOIN products p ON o.product_id=p.id "
            "WHERE wc.id=?",
            (claim_id,)
        ).fetchone()

        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")

        # Get user's warranty history
        history = conn.execute(
            "SELECT wc.id, wc.status, wc.created_at, "
            "COALESCE(p.name, '(deleted)') as product_name "
            "FROM warranty_claims wc "
            "JOIN orders o ON wc.order_id=o.id "
            "LEFT JOIN products p ON o.product_id=p.id "
            "WHERE wc.user_id=? AND wc.id!=? ORDER BY wc.id DESC LIMIT 5",
            (claim["user_id"], claim_id)
        ).fetchall()

        # Get available stock for the product (for resend)
        stock_count = 0
        if claim["product_id"]:
            stock_count = conn.execute(
                "SELECT COUNT(*) c FROM stock WHERE product_id=? AND is_sold=0",
                (claim["product_id"],)
            ).fetchone()["c"]

    return {
        "claim": row_to_dict(claim),
        "user_history": [row_to_dict(h) for h in history],
        "available_stock": stock_count,
    }


class UpdateClaimRequest(BaseModel):
    status: str  # "approved" | "rejected"
    note: Optional[str] = ""
    resend_product: Optional[bool] = False  # if True, send a new stock item to user


@router.post("/{claim_id}")
def update_claim(claim_id: int, body: UpdateClaimRequest, _: str = Depends(verify_token)):
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    with db.get_db() as conn:
        claim = conn.execute(
            "SELECT wc.*, o.product_id, o.user_id FROM warranty_claims wc "
            "JOIN orders o ON wc.order_id=o.id WHERE wc.id=?",
            (claim_id,)
        ).fetchone()

        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")

        db.update_warranty_claim(claim_id, body.status, body.note or "")

        resent_content = None
        if body.status == "approved" and body.resend_product and claim["product_id"]:
            # Get a new stock item and mark it as sold
            item = conn.execute(
                "SELECT * FROM stock WHERE product_id=? AND is_sold=0 LIMIT 1",
                (claim["product_id"],)
            ).fetchone()
            if item:
                conn.execute("UPDATE stock SET is_sold=1 WHERE id=?", (item["id"],))
                resent_content = item["content"]

    # اطلاع کاربر از نتیجه گارانتی از طریق ربات (ربات این پیام را مصرف می‌کند)
    if claim:
        target_lang = _user_lang(claim["user_id"])
        if body.status == "approved":
            _queue_dm(claim["user_id"], t("warranty_approved_user", target_lang, oid=claim["order_id"]), f"_w{claim_id}")
            if resent_content:
                _queue_dm(claim["user_id"], t("warranty_resend_content", target_lang, content=resent_content), f"_w{claim_id}_c")
        else:
            _queue_dm(claim["user_id"], t("warranty_rejected_user", target_lang, oid=claim["order_id"]), f"_w{claim_id}")

    return {
        "success": True,
        "resent_content": resent_content,
        "user_id": claim["user_id"] if claim else None,
    }
