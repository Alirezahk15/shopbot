from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, List
from api.auth import verify_token
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

router = APIRouter(prefix="/api/products", tags=["products"])


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


# ── Categories ──

@router.get("/categories")
def list_categories(_: str = Depends(verify_token)):
    cats = db.get_categories()
    return {"categories": [row_to_dict(c) for c in cats]}


class CategoryRequest(BaseModel):
    name: str


@router.post("/categories")
def add_category(body: CategoryRequest, _: str = Depends(verify_token)):
    db.add_category(body.name)
    with db.get_db() as conn:
        cat = conn.execute("SELECT * FROM categories WHERE name=?", (body.name,)).fetchone()
    return {"success": True, "category": row_to_dict(cat)}


class CategoryUpdateRequest(BaseModel):
    name: str
    image: str | None = None


@router.put("/categories/{cid}")
def update_category(cid: int, body: CategoryUpdateRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        cat = conn.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        conn.execute("UPDATE categories SET name=? WHERE id=?", (body.name, cid))
        if body.image is not None:
            conn.execute("UPDATE categories SET image=? WHERE id=?", (body.image, cid))
    return {"success": True}


@router.delete("/categories/{cid}")
def delete_category(cid: int, _: str = Depends(verify_token)):
    db.delete_category(cid)
    return {"success": True}


# ── Products ──

@router.get("")
def list_products(
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,   # "active" | "inactive"
    sort: Optional[str] = None,     # "price" | "sold" | "stock" | "name"
    _: str = Depends(verify_token)
):
    with db.get_db() as conn:
        where = ["1=1"]
        params = []
        if search:
            where.append("p.name LIKE ?")
            params.append(f"%{search}%")
        if category_id:
            where.append("p.category_id=?")
            params.append(category_id)
        if status == "active":
            where.append("p.active=1")
        elif status == "inactive":
            where.append("p.active=0")

        order = "p.id DESC"
        if sort == "price":
            order = "p.price DESC"
        elif sort == "sold":
            order = "p.sold DESC"
        elif sort == "name":
            order = "p.name ASC"
        elif sort == "stock":
            order = "stock_count DESC"

        prods = conn.execute(
            f"SELECT p.*, c.name as category_name, "
            f"(SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.is_sold=0) as stock_count "
            f"FROM products p LEFT JOIN categories c ON p.category_id=c.id "
            f"WHERE {' AND '.join(where)} ORDER BY {order}",
            params
        ).fetchall()

    return {"products": [row_to_dict(p) for p in prods]}


@router.get("/stats")
def get_product_stats(_: str = Depends(verify_token)):
    """Sales stats for charts."""
    with db.get_db() as conn:
        # Top products by revenue
        top = conn.execute("""
            SELECT p.id, p.name, p.price, p.sold,
                   COALESCE(SUM(o.price), 0) as revenue,
                   COUNT(o.id) as order_count,
                   (SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.is_sold=0) as stock_count
            FROM products p
            LEFT JOIN orders o ON p.id = o.product_id
            GROUP BY p.id
            ORDER BY revenue DESC
            LIMIT 10
        """).fetchall()

        # Sales per day (last 14 days)
        daily = conn.execute("""
            SELECT date(o.created_at) as day, COUNT(*) as orders, COALESCE(SUM(o.price), 0) as revenue
            FROM orders o
            WHERE o.created_at >= date('now', '-13 days')
            GROUP BY date(o.created_at)
            ORDER BY day ASC
        """).fetchall()

        # Fill missing days
        from datetime import date, timedelta
        result = {}
        for i in range(14):
            d = (date.today() - timedelta(days=13-i)).isoformat()
            result[d] = {"day": d, "orders": 0, "revenue": 0.0}
        for row in daily:
            result[row["day"]] = {"day": row["day"], "orders": row["orders"], "revenue": round(row["revenue"], 2)}

    return {
        "top_products": [row_to_dict(r) for r in top],
        "daily_sales": list(result.values()),
    }


class ProductRequest(BaseModel):
    category_id: int
    name: str
    price: float
    description: str
    features: Optional[str] = ""
    has_warranty: Optional[int] = 0
    banner_url: Optional[str] = ""


@router.post("")
def add_product(body: ProductRequest, _: str = Depends(verify_token)):
    pid = db.add_product(
        body.category_id, body.name, body.price,
        body.description, body.features or "", body.has_warranty or 0
    )
    if body.banner_url:
        db.update_product(pid, banner_url=body.banner_url)
    return {"success": True, "product_id": pid}


@router.post("/{pid}/duplicate")
def duplicate_product(pid: int, _: str = Depends(verify_token)):
    """Create a copy of a product (without stock)."""
    p = db.get_product(pid)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    new_pid = db.add_product(
        p["category_id"],
        f"{p['name']} (Copy)",
        p["price"],
        p["description"],
        p["features"] or "",
        p["has_warranty"]
    )
    if p["banner_url"]:
        db.update_product(new_pid, banner_url=p["banner_url"])
    return {"success": True, "new_product_id": new_pid}


class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    description: Optional[str] = None
    features: Optional[str] = None
    has_warranty: Optional[int] = None
    active: Optional[int] = None
    banner_url: Optional[str] = None
    category_id: Optional[int] = None


@router.put("/{pid}")
def update_product(pid: int, body: ProductUpdateRequest, _: str = Depends(verify_token)):
    p = db.get_product(pid)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    kwargs = {k: v for k, v in body.dict().items() if v is not None}
    # Handle category_id separately (not in _ALLOWED_PRODUCT_COLS)
    if "category_id" in kwargs:
        with db.get_db() as conn:
            conn.execute("UPDATE products SET category_id=? WHERE id=?", (kwargs.pop("category_id"), pid))
    if kwargs:
        db.update_product(pid, **kwargs)
    return {"success": True}


class BulkDeleteRequest(BaseModel):
    product_ids: List[int]


@router.post("/bulk-delete")
def bulk_delete_products(body: BulkDeleteRequest, _: str = Depends(verify_token)):
    """Delete multiple products at once."""
    deleted = []
    for pid in body.product_ids:
        p = db.get_product(pid)
        if p:
            db.delete_product(pid)
            deleted.append(pid)
    return {"success": True, "deleted": deleted, "count": len(deleted)}


class BulkPriceRequest(BaseModel):
    product_ids: List[int]
    operation: str   # "set" | "increase_pct" | "decrease_pct" | "increase_abs" | "decrease_abs"
    value: float


@router.post("/bulk-price")
def bulk_price_update(body: BulkPriceRequest, _: str = Depends(verify_token)):
    """Update prices for multiple products at once."""
    updated = []
    with db.get_db() as conn:
        for pid in body.product_ids:
            p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
            if not p:
                continue
            if body.operation == "set":
                new_price = body.value
            elif body.operation == "increase_pct":
                new_price = round(p["price"] * (1 + body.value / 100), 2)
            elif body.operation == "decrease_pct":
                new_price = round(p["price"] * (1 - body.value / 100), 2)
            elif body.operation == "increase_abs":
                new_price = round(p["price"] + body.value, 2)
            elif body.operation == "decrease_abs":
                new_price = max(0, round(p["price"] - body.value, 2))
            else:
                continue
            new_price = max(0.01, new_price)
            conn.execute("UPDATE products SET price=? WHERE id=?", (new_price, pid))
            updated.append({"id": pid, "old_price": p["price"], "new_price": new_price})
    return {"success": True, "updated": updated}


@router.delete("/{pid}")
def delete_product(pid: int, _: str = Depends(verify_token)):
    p = db.get_product(pid)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete_product(pid)
    return {"success": True}


@router.post("/{pid}/toggle")
def toggle_product(pid: int, _: str = Depends(verify_token)):
    p = db.get_product(pid)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    active = db.toggle_product_active(pid)
    return {"success": True, "active": bool(active)}


# ── Stock management ──

@router.get("/{pid}/stock")
def get_stock(pid: int, page: int = 0, limit: int = 50, _: str = Depends(verify_token)):
    """Get unsold stock items for a product."""
    with db.get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) c FROM stock WHERE product_id=? AND is_sold=0", (pid,)
        ).fetchone()["c"]
        items = conn.execute(
            "SELECT * FROM stock WHERE product_id=? AND is_sold=0 ORDER BY id DESC LIMIT ? OFFSET ?",
            (pid, limit, page * limit)
        ).fetchall()
    return {"total": total, "items": [row_to_dict(i) for i in items]}


class StockRequest(BaseModel):
    items: List[str]


@router.post("/{pid}/stock")
def add_stock(pid: int, body: StockRequest, _: str = Depends(verify_token)):
    p = db.get_product(pid)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    db.add_stock(pid, body.items)
    count = db.stock_count(pid)
    return {"success": True, "stock_count": count}


@router.post("/{pid}/stock/import-csv")
def import_stock_csv(pid: int, body: StockRequest, _: str = Depends(verify_token)):
    """Import stock from CSV content (items separated by newlines or commas)."""
    p = db.get_product(pid)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    # Parse: support both newline and comma separated
    raw = "\n".join(body.items)
    items = [i.strip() for line in raw.split("\n") for i in line.split(",") if i.strip()]
    db.add_stock(pid, items)
    count = db.stock_count(pid)
    return {"success": True, "added": len(items), "stock_count": count}


@router.delete("/{pid}/stock/{item_id}")
def delete_stock_item(pid: int, item_id: int, _: str = Depends(verify_token)):
    """Delete a specific unsold stock item."""
    with db.get_db() as conn:
        item = conn.execute(
            "SELECT * FROM stock WHERE id=? AND product_id=? AND is_sold=0", (item_id, pid)
        ).fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Stock item not found or already sold")
        conn.execute("DELETE FROM stock WHERE id=?", (item_id,))
    return {"success": True}


@router.delete("/{pid}/stock")
def clear_all_stock(pid: int, _: str = Depends(verify_token)):
    """Delete ALL unsold stock items for a product."""
    with db.get_db() as conn:
        count = conn.execute(
            "SELECT COUNT(*) c FROM stock WHERE product_id=? AND is_sold=0", (pid,)
        ).fetchone()["c"]
        conn.execute("DELETE FROM stock WHERE product_id=? AND is_sold=0", (pid,))
    return {"success": True, "deleted": count}
