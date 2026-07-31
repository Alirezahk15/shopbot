"""مدیریت متن‌های ربات (Text Overrides) — ویرایش همه متن‌ها از پنل"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import database as db
from lang import T
from api.auth import verify_token

router = APIRouter(prefix="/api/texts", tags=["texts"])


@router.get("")
def list_texts(_: str = Depends(verify_token)):
    """همه کلیدهای متنی ربات + مقادیر پیش‌فرض و بازنویسی‌شده"""
    ovr = db.get_text_overrides()
    out = []
    for key, v in T.items():
        if not isinstance(v, dict) or "fa" not in v:
            continue
        out.append({
            "key": key,
            "default_fa": v.get("fa", ""),
            "default_en": v.get("en", ""),
            "override_fa": ovr.get(f"{key}|fa", ""),
            "override_en": ovr.get(f"{key}|en", ""),
        })
    return {"texts": out}


class TextRequest(BaseModel):
    lang: str
    text: str = ""


@router.put("/{key}")
def set_text(key: str, body: TextRequest, _: str = Depends(verify_token)):
    if key not in T:
        raise HTTPException(status_code=404, detail="Unknown text key")
    if body.lang not in ("fa", "en"):
        raise HTTPException(status_code=400, detail="lang must be fa or en")
    if body.text.strip():
        db.set_text_override(key, body.lang, body.text)
    else:
        db.delete_text_override(key, body.lang)
    return {"success": True}


@router.delete("/{key}/{lang}")
def reset_text(key: str, lang: str, _: str = Depends(verify_token)):
    db.delete_text_override(key, lang)
    return {"success": True}
