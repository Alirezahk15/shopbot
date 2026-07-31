from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, List
from api.auth import verify_token
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/discounts", tags=["discounts"])


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


@router.get("")
def list_discounts(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        codes = conn.execute("SELECT * FROM discounts ORDER BY code ASC").fetchall()
    return {"discounts": [row_to_dict(c) for c in codes]}


@router.get("/export.csv")
def export_discounts_csv(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        rows = conn.execute("SELECT * FROM discounts ORDER BY created_at DESC").fetchall()
    lines = ["code,percent,max_uses,used,active,expires_at,created_at"]
    for r in rows:
        lines.append(
            f"{r['code']},{r['percent']},{r['max_uses']},{r['used']},"
            f"{r['active']},{r['expires_at'] or ''},{r['created_at']}"
        )
    return Response(
        content="\n".join(lines),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=discounts.csv"}
    )


class DiscountRequest(BaseModel):
    code: str
    percent: int
    max_uses: int
    expires_at: Optional[str] = None
    product_ids: Optional[str] = None  # comma-separated product IDs or None


@router.post("")
def add_discount(body: DiscountRequest, _: str = Depends(verify_token)):
    if not 1 <= body.percent <= 100:
        raise HTTPException(status_code=400, detail="Percent must be 1-100")
    if body.max_uses < 1:
        raise HTTPException(status_code=400, detail="Max uses must be >= 1")
    with db.get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO discounts (code, percent, max_uses, used, active, expires_at, product_ids) "
            "VALUES (?,?,?,0,1,?,?)",
            (body.code.upper(), body.percent, body.max_uses, body.expires_at, body.product_ids)
        )
    return {"success": True, "code": body.code.upper()}


class DiscountUpdateRequest(BaseModel):
    percent: Optional[int] = None
    max_uses: Optional[int] = None
    expires_at: Optional[str] = None
    product_ids: Optional[str] = None


@router.put("/{code}")
def update_discount(code: str, body: DiscountUpdateRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        d = conn.execute("SELECT * FROM discounts WHERE code=?", (code.upper(),)).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Discount code not found")
        updates = {}
        if body.percent is not None:
            if not 1 <= body.percent <= 100:
                raise HTTPException(status_code=400, detail="Percent must be 1-100")
            updates["percent"] = body.percent
        if body.max_uses is not None:
            if body.max_uses < 1:
                raise HTTPException(status_code=400, detail="Max uses must be >= 1")
            updates["max_uses"] = body.max_uses
        if body.expires_at is not None:
            updates["expires_at"] = body.expires_at if body.expires_at else None
        if body.product_ids is not None:
            updates["product_ids"] = body.product_ids if body.product_ids else None
        if updates:
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE discounts SET {sets} WHERE code=?", (*updates.values(), code.upper()))
    return {"success": True}


@router.post("/{code}/toggle")
def toggle_discount(code: str, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        d = conn.execute("SELECT * FROM discounts WHERE code=?", (code.upper(),)).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Discount code not found")
        new_active = 0 if d["active"] else 1
        conn.execute("UPDATE discounts SET active=? WHERE code=?", (new_active, code.upper()))
    return {"success": True, "active": bool(new_active)}


@router.post("/{code}/reset")
def reset_discount_usage(code: str, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        d = conn.execute("SELECT * FROM discounts WHERE code=?", (code.upper(),)).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Discount code not found")
        old_used = d["used"]
        conn.execute("UPDATE discounts SET used=0 WHERE code=?", (code.upper(),))
    return {"success": True, "reset_from": old_used}


@router.get("/{code}/usage")
def get_discount_usage(code: str, _: str = Depends(verify_token)):
    """Get usage history for a discount code."""
    with db.get_db() as conn:
        d = conn.execute("SELECT * FROM discounts WHERE code=?", (code.upper(),)).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Discount code not found")
        usage = conn.execute(
            "SELECT du.*, u.username FROM discount_usage du "
            "LEFT JOIN users u ON du.user_id = u.user_id "
            "WHERE du.code=? ORDER BY du.id DESC LIMIT 50",
            (code.upper(),)
        ).fetchall()
    return {
        "code": row_to_dict(d),
        "usage": [row_to_dict(u) for u in usage],
    }


@router.delete("/{code}")
def delete_discount(code: str, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        d = conn.execute("SELECT * FROM discounts WHERE code=?", (code.upper(),)).fetchone()
        if not d:
            raise HTTPException(status_code=404, detail="Discount code not found")
        conn.execute("DELETE FROM discounts WHERE code=?", (code.upper(),))
        conn.execute("DELETE FROM discount_usage WHERE code=?", (code.upper(),))
    return {"success": True}


@router.get("/check-expired")
def check_expired_discounts(_: str = Depends(verify_token)):
    """Deactivate expired discount codes."""
    from datetime import date
    today = date.today().isoformat()
    with db.get_db() as conn:
        expired = conn.execute(
            "SELECT code FROM discounts WHERE expires_at IS NOT NULL AND expires_at < ? AND active=1",
            (today,)
        ).fetchall()
        deactivated = []
        for row in expired:
            conn.execute("UPDATE discounts SET active=0 WHERE code=?", (row["code"],))
            deactivated.append(row["code"])
    return {"deactivated": deactivated, "count": len(deactivated)}
