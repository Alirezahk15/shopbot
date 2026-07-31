from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from api.auth import verify_token
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/methods", tags=["payment_methods"])


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def log_method_action(method_id: int, action: str, detail: str = ""):
    try:
        with db.get_db() as conn:
            conn.execute(
                "INSERT INTO payment_method_logs (method_id, action, detail) VALUES (?,?,?)",
                (method_id, action, detail)
            )
    except Exception:
        pass


@router.get("")
def list_methods(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        methods = conn.execute(
            "SELECT * FROM payment_methods ORDER BY display_order ASC, id ASC"
        ).fetchall()
    return {"methods": [row_to_dict(m) for m in methods]}


@router.get("/stats")
def get_method_stats(_: str = Depends(verify_token)):
    """Stats for each payment method."""
    with db.get_db() as conn:
        methods = conn.execute("SELECT * FROM payment_methods ORDER BY display_order ASC, id ASC").fetchall()
        result = []
        for m in methods:
            # Card payments stats
            if m["name"] == "card":
                stats = conn.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(CASE WHEN status='approved' THEN 1 END) as approved,
                        COALESCE(SUM(CASE WHEN status='approved' THEN amount ELSE 0 END), 0) as total_amount
                    FROM card_payments
                """).fetchone()
            else:
                # USDT/other — from transactions
                stats = conn.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) as approved,
                        COALESCE(SUM(amount), 0) as total_amount
                    FROM transactions WHERE method=?
                """, (m["name"],)).fetchone()

            result.append({
                **row_to_dict(m),
                "total_transactions": stats["total"] if stats else 0,
                "approved_transactions": stats["approved"] if stats else 0,
                "total_amount": round(stats["total_amount"] if stats else 0, 2),
            })
    return {"stats": result}


@router.get("/{method_id}/logs")
def get_method_logs(method_id: int, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        logs = conn.execute(
            "SELECT * FROM payment_method_logs WHERE method_id=? ORDER BY id DESC LIMIT 50",
            (method_id,)
        ).fetchall()
    return {"logs": [row_to_dict(l) for l in logs]}


class AddMethodRequest(BaseModel):
    name: str
    details: Optional[str] = ""
    min_amount: Optional[float] = 0
    max_amount: Optional[float] = 0
    guide_message: Optional[str] = ""


@router.post("")
def add_method(body: AddMethodRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        # Get next display_order
        max_order = conn.execute("SELECT COALESCE(MAX(display_order), 0) m FROM payment_methods").fetchone()["m"]
        conn.execute(
            "INSERT OR IGNORE INTO payment_methods (name, details, active, display_order, min_amount, max_amount, guide_message) "
            "VALUES (?,?,1,?,?,?,?)",
            (body.name, body.details or "", max_order + 1, body.min_amount or 0, body.max_amount or 0, body.guide_message or "")
        )
        m = conn.execute("SELECT * FROM payment_methods WHERE name=?", (body.name,)).fetchone()
    if m:
        log_method_action(m["id"], "add", f"Added method: {body.name}")
    return {"success": True}


class UpdateMethodRequest(BaseModel):
    name: Optional[str] = None
    details: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    guide_message: Optional[str] = None


@router.put("/{method_id}")
def update_method(method_id: int, body: UpdateMethodRequest, _: str = Depends(verify_token)):
    m = db.get_payment_method(method_id)
    if not m:
        raise HTTPException(status_code=404, detail="Method not found")

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.details is not None:
        updates["details"] = body.details
    if body.min_amount is not None:
        updates["min_amount"] = body.min_amount
    if body.max_amount is not None:
        updates["max_amount"] = body.max_amount
    if body.guide_message is not None:
        updates["guide_message"] = body.guide_message

    if updates:
        with db.get_db() as conn:
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(f"UPDATE payment_methods SET {sets} WHERE id=?", (*updates.values(), method_id))
        log_method_action(method_id, "update", f"Updated: {list(updates.keys())}")

    return {"success": True}


class ReorderRequest(BaseModel):
    ordered_ids: list  # list of method IDs in desired order


@router.post("/reorder")
def reorder_methods(body: ReorderRequest, _: str = Depends(verify_token)):
    """Set display order for payment methods."""
    with db.get_db() as conn:
        for i, method_id in enumerate(body.ordered_ids):
            conn.execute("UPDATE payment_methods SET display_order=? WHERE id=?", (i, method_id))
    return {"success": True}


@router.post("/{method_id}/toggle")
def toggle_method(method_id: int, _: str = Depends(verify_token)):
    m = db.get_payment_method(method_id)
    if not m:
        raise HTTPException(status_code=404, detail="Method not found")
    new_active = 0 if m["active"] else 1
    db.update_payment_method(method_id, active=new_active)
    log_method_action(method_id, "toggle", f"{'Activated' if new_active else 'Deactivated'}: {m['name']}")
    return {"success": True, "active": bool(new_active)}


@router.delete("/{method_id}")
def delete_method(method_id: int, _: str = Depends(verify_token)):
    m = db.get_payment_method(method_id)
    if not m:
        raise HTTPException(status_code=404, detail="Method not found")
    log_method_action(method_id, "delete", f"Deleted: {m['name']}")
    db.delete_payment_method(method_id)
    return {"success": True}
