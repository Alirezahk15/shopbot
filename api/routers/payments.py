from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, List
from api.auth import verify_token
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db
from lang import t

router = APIRouter(prefix="/api/payments", tags=["payments"])


def _queue_dm(uid, message, suffix=""):
    """قرار دادن یک پیام در صف ارسال تا ربات به محض روشن شدن ارسال شود"""
    key = f"pending_dm_{uid}_{int(time.time()*1000)}{suffix}"
    db.set_setting(key, json.dumps({"user_id": uid, "message": message}))


def _user_lang(uid):
    u = db.get_user(uid)
    return (u["lang"] if u and u["lang"] else "fa")


def _pay_referral(uid, amount, suffix=""):
    """واریز پورسانت رفرال — دقیقا مطابق منطق ربات: دو سطح، سقف روزانه و ثبت لاگ"""
    if db.get_setting("feature_referral", "1") != "1":
        return
    user = db.get_user(uid)
    if not user or not user["referrer"]:
        return
    daily_cap = float(db.get_setting("referral_daily_cap", "0") or 0)

    def _pay(ref_id, percent, tag):
        bonus = round(amount * percent / 100, 2)
        if bonus <= 0:
            return
        if daily_cap:
            earned = db.ref_earned_today(ref_id)
            if earned >= daily_cap:
                return
            bonus = min(bonus, round(daily_cap - earned, 2))
        db.add_balance(ref_id, bonus, ref_earning=True)
        db.log_ref_earning(ref_id, bonus)
        _queue_dm(ref_id, t("ref_bonus", _user_lang(ref_id), a=bonus), suffix + tag)

    _pay(user["referrer"], float(db.get_setting("referral_percent", "10") or 10), "_ref")
    percent2 = float(db.get_setting("referral_l2_percent", "0") or 0)
    if percent2 > 0:
        ref1 = db.get_user(user["referrer"])
        if ref1 and ref1["referrer"]:
            _pay(ref1["referrer"], percent2, "_ref2")


def _apply_deposit_bonus(uid, amount):
    """بونوس شارژ — همان منطق apply_deposit_bonus ربات"""
    try:
        percent = float(db.get_setting("deposit_bonus_percent", "0") or 0)
        min_amt = float(db.get_setting("deposit_bonus_min", "0") or 0)
        if percent > 0 and amount >= min_amt:
            bonus = round(amount * percent / 100, 2)
            if bonus > 0:
                db.add_balance(uid, bonus)
                return bonus
    except Exception:
        pass
    return 0


def _notify_card_approved(uid, amount, suffix=""):
    lang = _user_lang(uid)
    bonus = _apply_deposit_bonus(uid, amount)
    msg = t("card_approved", lang)
    if bonus:
        msg += f"\n🎁 +${bonus:.2f}"
    _queue_dm(uid, msg, suffix)
    _pay_referral(uid, amount, suffix)


def _notify_card_rejected(uid, reason="", suffix=""):
    lang = _user_lang(uid)
    msg = t("card_rejected", lang)
    if reason:
        msg += f"\n\n💬 {reason}"
    _queue_dm(uid, msg, suffix)


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


@router.get("/pending")
def get_pending(_: str = Depends(verify_token)):
    payments = db.get_pending_card_payments()
    return {"payments": [row_to_dict(p) for p in payments]}


@router.get("/all")
def get_all_payments(
    offset: int = 0,
    limit: int = 20,
    status: Optional[str] = None,       # "pending" | "approved" | "rejected"
    search: Optional[str] = None,       # user_id or username
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    _: str = Depends(verify_token)
):
    with db.get_db() as conn:
        where = ["1=1"]
        params = []

        if status:
            where.append("cp.status=?")
            params.append(status)

        if search:
            try:
                uid = int(search)
                where.append("cp.user_id=?")
                params.append(uid)
            except ValueError:
                where.append("u.username LIKE ?")
                params.append(f"%{search}%")

        if date_from:
            where.append("date(cp.created_at) >= ?")
            params.append(date_from)

        if date_to:
            where.append("date(cp.created_at) <= ?")
            params.append(date_to)

        total = conn.execute(
            f"SELECT COUNT(*) c FROM card_payments cp "
            f"LEFT JOIN users u ON cp.user_id=u.user_id "
            f"WHERE {' AND '.join(where)}",
            params
        ).fetchone()["c"]

        rows = conn.execute(
            f"SELECT cp.*, u.username FROM card_payments cp "
            f"LEFT JOIN users u ON cp.user_id=u.user_id "
            f"WHERE {' AND '.join(where)} ORDER BY cp.id DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()

    return {"total": total, "payments": [row_to_dict(r) for r in rows]}


@router.get("/stats")
def get_payment_stats(_: str = Depends(verify_token)):
    """Payment statistics."""
    with db.get_db() as conn:
        summary = conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN status='approved' THEN 1 END) as approved,
                COUNT(CASE WHEN status='rejected' THEN 1 END) as rejected,
                COUNT(CASE WHEN status='pending' THEN 1 END) as pending,
                COALESCE(SUM(CASE WHEN status='approved' THEN amount ELSE 0 END), 0) as total_approved_amount,
                COALESCE(AVG(CASE WHEN status='approved' THEN amount END), 0) as avg_amount,
                COUNT(CASE WHEN date(created_at)=date('now') THEN 1 END) as today_total,
                COALESCE(SUM(CASE WHEN status='approved' AND date(created_at)=date('now') THEN amount ELSE 0 END), 0) as today_amount
            FROM card_payments
        """).fetchone()

        # Daily stats for last 14 days
        daily = conn.execute("""
            SELECT date(created_at) as day,
                   COUNT(*) as total,
                   COUNT(CASE WHEN status='approved' THEN 1 END) as approved,
                   COALESCE(SUM(CASE WHEN status='approved' THEN amount ELSE 0 END), 0) as amount
            FROM card_payments
            WHERE created_at >= date('now', '-13 days')
            GROUP BY date(created_at)
            ORDER BY day ASC
        """).fetchall()

        # Fill missing days
        from datetime import date, timedelta
        result = {}
        for i in range(14):
            d = (date.today() - timedelta(days=13-i)).isoformat()
            result[d] = {"day": d, "total": 0, "approved": 0, "amount": 0.0}
        for row in daily:
            result[row["day"]] = {"day": row["day"], "total": row["total"], "approved": row["approved"], "amount": round(row["amount"], 2)}

    return {
        "summary": row_to_dict(summary),
        "daily": list(result.values()),
    }


@router.get("/export.csv")
def export_payments_csv(
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    _: str = Depends(verify_token)
):
    with db.get_db() as conn:
        where = ["1=1"]
        params = []
        if status:
            where.append("cp.status=?")
            params.append(status)
        if date_from:
            where.append("date(cp.created_at) >= ?")
            params.append(date_from)
        if date_to:
            where.append("date(cp.created_at) <= ?")
            params.append(date_to)

        rows = conn.execute(
            f"SELECT cp.id, cp.user_id, u.username, cp.amount, cp.status, "
            f"cp.reject_reason, cp.created_at FROM card_payments cp "
            f"LEFT JOIN users u ON cp.user_id=u.user_id "
            f"WHERE {' AND '.join(where)} ORDER BY cp.id DESC",
            params
        ).fetchall()

    lines = ["id,user_id,username,amount,status,reject_reason,date"]
    for r in rows:
        lines.append(
            f"{r['id']},{r['user_id']},{r['username'] or ''},"
            f"{r['amount']},{r['status']},{r['reject_reason'] or ''},{r['created_at']}"
        )
    return Response(
        content="\n".join(lines),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=payments.csv"}
    )


class ApproveRequest(BaseModel):
    pass


@router.post("/{pay_id}/approve")
def approve_payment(pay_id: int, _: str = Depends(verify_token)):
    current = db.get_card_payment(pay_id)
    if not current:
        raise HTTPException(status_code=404, detail="Payment not found")
    if current["status"] == "approved":
        raise HTTPException(status_code=400, detail="Payment already approved")
    # If previously rejected, we can re-approve
    if current["status"] == "pending" or current["status"] == "rejected":
        pay = db.set_card_status(pay_id, "approved")
        if not db.tx_exists(f"card_{pay_id}"):
            db.save_tx(pay["user_id"], f"card_{pay_id}", pay["amount"], "card")
            _notify_card_approved(pay["user_id"], pay["amount"], f"_{pay_id}")
    return {"success": True, "user_id": current["user_id"], "amount": current["amount"]}


class RejectRequest(BaseModel):
    reason: Optional[str] = ""


@router.post("/{pay_id}/reject")
def reject_payment(pay_id: int, body: RejectRequest, _: str = Depends(verify_token)):
    current = db.get_card_payment(pay_id)
    if not current:
        raise HTTPException(status_code=404, detail="Payment not found")
    if current["status"] == "rejected":
        raise HTTPException(status_code=400, detail="Payment already rejected")
    with db.get_db() as conn:
        conn.execute(
            "UPDATE card_payments SET status='rejected', reject_reason=? WHERE id=?",
            (body.reason or "", pay_id)
        )
    _notify_card_rejected(current["user_id"], body.reason or "", f"_{pay_id}")
    return {"success": True, "reason": body.reason}


class BulkActionRequest(BaseModel):
    payment_ids: List[int]
    action: str  # "approve" | "reject"
    reason: Optional[str] = ""


@router.post("/bulk-action")
def bulk_action(body: BulkActionRequest, _: str = Depends(verify_token)):
    """Approve or reject multiple payments at once."""
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")

    results = []
    for pay_id in body.payment_ids:
        current = db.get_card_payment(pay_id)
        if not current or current["status"] != "pending":
            continue
        if body.action == "approve":
            pay = db.set_card_status(pay_id, "approved")
            if not db.tx_exists(f"card_{pay_id}"):
                db.save_tx(pay["user_id"], f"card_{pay_id}", pay["amount"], "card")
                _notify_card_approved(pay["user_id"], pay["amount"], f"_{pay_id}")
            results.append({"id": pay_id, "status": "approved"})
        else:
            with db.get_db() as conn:
                conn.execute(
                    "UPDATE card_payments SET status='rejected', reject_reason=? WHERE id=?",
                    (body.reason or "", pay_id)
                )
            _notify_card_rejected(current["user_id"], body.reason or "", f"_{pay_id}")
            results.append({"id": pay_id, "status": "rejected"})

    return {"success": True, "processed": results, "count": len(results)}


@router.get("/{pay_id}")
def get_payment(pay_id: int, _: str = Depends(verify_token)):
    payment = db.get_card_payment(pay_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    user = db.get_user(payment["user_id"])
    return {
        "payment": row_to_dict(payment),
        "user": row_to_dict(user),
    }
