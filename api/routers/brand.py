"""برند پنل (لوگو + نام) — در دسترس همه ادمین‌ها برای نمایش سایدبار"""
from fastapi import APIRouter, Depends
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import database as db
from api.auth import verify_token

router = APIRouter(prefix="/api/brand", tags=["brand"])


@router.get("")
def get_brand(_: str = Depends(verify_token)):
    return {
        "title": db.get_setting("panel_title", ""),
        "logo": db.get_setting("panel_logo_url", ""),
    }
