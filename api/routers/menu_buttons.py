"""منوساز — دکمه‌های سفارشی منوی اصلی ربات (لینک / متن / زیرمنو)"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import database as db
from api.auth import verify_token

router = APIRouter(prefix="/api/menu-buttons", tags=["menu-buttons"])

VALID_TYPES = ("text", "link", "submenu")


def _row(r):
    return {
        "id": r["id"], "label": r["label"], "type": r["type"],
        "content": r["content"], "parent_id": r["parent_id"],
        "position": r["position"], "active": r["active"],
    }


@router.get("")
def list_buttons(_: str = Depends(verify_token)):
    return {"buttons": [_row(r) for r in db.get_all_custom_buttons()]}


class ButtonRequest(BaseModel):
    label: str
    type: str = "text"
    content: str = ""
    parent_id: int | None = None
    position: int = 0
    active: bool = True


def _validate(body: ButtonRequest):
    if not body.label.strip():
        raise HTTPException(status_code=400, detail="Label is required")
    if body.type not in VALID_TYPES:
        raise HTTPException(status_code=400, detail="Invalid type")
    if body.type == "link" and not (body.content or "").startswith(("http://", "https://", "tg://")):
        raise HTTPException(status_code=400, detail="Link buttons need a valid URL")
    if body.parent_id:
        parent = db.get_custom_button(body.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="Parent not found")
        if parent["type"] != "submenu":
            raise HTTPException(status_code=400, detail="Parent must be a submenu")


@router.post("")
def add_button(body: ButtonRequest, _: str = Depends(verify_token)):
    _validate(body)
    bid = db.add_custom_button(body.label.strip(), body.type, body.content,
                               body.parent_id or None, body.position)
    return {"success": True, "id": bid}


@router.put("/{bid}")
def update_button(bid: int, body: ButtonRequest, _: str = Depends(verify_token)):
    if not db.get_custom_button(bid):
        raise HTTPException(status_code=404, detail="Button not found")
    if body.parent_id == bid:
        raise HTTPException(status_code=400, detail="Button cannot be its own parent")
    _validate(body)
    db.update_custom_button(bid, body.label.strip(), body.type, body.content,
                            body.parent_id or None, body.position, body.active)
    return {"success": True}


@router.delete("/{bid}")
def delete_button(bid: int, _: str = Depends(verify_token)):
    if not db.get_custom_button(bid):
        raise HTTPException(status_code=404, detail="Button not found")
    db.delete_custom_button(bid)
    return {"success": True}
