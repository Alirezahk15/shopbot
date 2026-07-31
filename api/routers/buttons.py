from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db
from lang import T
from api.auth import verify_token

router = APIRouter(prefix="/api/buttons", tags=["buttons"])

# تعریف هر منوی قابل چیدمان: کلید دکمه‌ها و برچسب نمایشی خود منو
MENUS = {
    "main_reply": {
        "label": {"fa": "دکمه‌های پایین صفحه (کیبورد)", "en": "Bottom Keyboard"},
        "keys": ["kb_start", "kb_products", "kb_support", "kb_lang"],
    },
    "main_inline": {
        "label": {"fa": "منوی اصلی (دکمه‌های شیشه‌ای)", "en": "Main Menu (Inline Buttons)"},
        "keys": ["btn_browse", "btn_orders", "btn_recharge", "btn_profile",
                 "btn_support", "btn_invite", "btn_lang", "btn_admin"],
    },
    "admin_panel": {
        "label": {"fa": "پنل مدیریت داخل ربات", "en": "In-Bot Admin Panel"},
        "keys": ["adm_btn_products", "adm_btn_users", "adm_btn_codes", "adm_btn_cards",
                 "adm_btn_tickets", "adm_btn_warranty", "adm_btn_lock", "adm_btn_admins",
                 "adm_btn_payment", "adm_btn_apis", "adm_btn_settings", "adm_btn_broadcast"],
    },
    "profile_menu": {
        "label": {"fa": "زیرمنوی پروفایل", "en": "Profile Submenu"},
        "keys": ["btn_recharge", "btn_orders", "btn_invite", "btn_back"],
    },
    "recharge_menu": {
        "label": {"fa": "زیرمنوی شارژ حساب", "en": "Recharge Submenu"},
        "keys": ["pay_usdt", "pay_usdt_trc20", "pay_ton", "pay_stars", "pay_zarinpal", "pay_card", "btn_back"],
    },
    "support_menu": {
        "label": {"fa": "زیرمنوی پشتیبانی", "en": "Support Submenu"},
        "keys": ["btn_tickets", "btn_new_ticket", "btn_back"],
    },
    "invite_menu": {
        "label": {"fa": "زیرمنوی دعوت دوستان", "en": "Invite Submenu"},
        "keys": ["btn_reftop", "btn_back"],
    },
}


def _default_config(menu_key):
    keys = MENUS[menu_key]["keys"]
    rows = [keys[i:i + 2] for i in range(0, len(keys), 2)]
    return {"rows": rows, "hidden": [], "meta": {}}


def _load_config(menu_key):
    raw = db.get_setting(f"button_layout_{menu_key}", "")
    default_keys = MENUS[menu_key]["keys"]
    cfg = None
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "rows" in parsed:
                cfg = parsed
        except Exception:
            cfg = None
    if cfg is None:
        cfg = _default_config(menu_key)

    rows = cfg.get("rows") or []
    hidden = cfg.get("hidden") or []
    meta = cfg.get("meta") or {}

    seen = set()
    clean_rows = []
    for row in rows:
        out_row = [k for k in row if k in default_keys and k not in seen]
        for k in out_row:
            seen.add(k)
        if out_row:
            clean_rows.append(out_row)
    clean_hidden = [k for k in hidden if k in default_keys and k not in seen]
    for k in clean_hidden:
        seen.add(k)
    # هر کلیدی که نه در ردیف‌ها و نه در مخفی‌هاست (مثلاً دکمه‌ی تازه افزوده‌شده) به صورت پیش‌فرض نمایش داده می‌شود
    for k in default_keys:
        if k not in seen:
            clean_rows.append([k])
            seen.add(k)

    return {"rows": clean_rows, "hidden": clean_hidden, "meta": meta}


def _button_info(menu_key, key):
    meta = _load_config(menu_key)["meta"].get(key, {}) or {}
    return {
        "key": key,
        "label": meta.get("label", "") or "",
        "color": meta.get("color", "") or "",
        "default_label_fa": T.get(key, {}).get("fa", key),
        "default_label_en": T.get(key, {}).get("en", key),
    }


@router.get("")
def list_menus(_: str = Depends(verify_token)):
    result = {}
    for menu_key, meta_info in MENUS.items():
        cfg = _load_config(menu_key)
        meta = cfg["meta"]

        def build(key):
            m = meta.get(key, {}) or {}
            return {
                "key": key,
                "label": m.get("label", "") or "",
                "color": m.get("color", "") or "",
                "default_label_fa": T.get(key, {}).get("fa", key),
                "default_label_en": T.get(key, {}).get("en", key),
            }

        result[menu_key] = {
            "label": meta_info["label"],
            "rows": [[build(k) for k in row] for row in cfg["rows"]],
            "hidden": [build(k) for k in cfg["hidden"]],
        }
    return result


class ButtonMeta(BaseModel):
    label: str = ""
    color: str = ""


class SaveLayoutRequest(BaseModel):
    rows: List[List[str]]
    hidden: List[str] = []
    meta: Dict[str, ButtonMeta] = {}


@router.post("/{menu_key}")
def save_layout(menu_key: str, body: SaveLayoutRequest, _: str = Depends(verify_token)):
    if menu_key not in MENUS:
        raise HTTPException(status_code=404, detail="Unknown menu")
    valid_keys = set(MENUS[menu_key]["keys"])

    seen = set()
    clean_rows = []
    for row in body.rows:
        out_row = [k for k in row if k in valid_keys and k not in seen]
        for k in out_row:
            seen.add(k)
        if out_row:
            clean_rows.append(out_row)

    clean_hidden = [k for k in body.hidden if k in valid_keys and k not in seen]
    for k in clean_hidden:
        seen.add(k)

    for k in MENUS[menu_key]["keys"]:
        if k not in seen:
            clean_rows.append([k])

    clean_meta = {}
    for k, m in body.meta.items():
        if k in valid_keys:
            clean_meta[k] = {"label": (m.label or "").strip(), "color": (m.color or "").strip()}

    db.set_setting(f"button_layout_{menu_key}", json.dumps({
        "rows": clean_rows, "hidden": clean_hidden, "meta": clean_meta,
    }))
    return {"success": True}


@router.post("/{menu_key}/reset")
def reset_layout(menu_key: str, _: str = Depends(verify_token)):
    if menu_key not in MENUS:
        raise HTTPException(status_code=404, detail="Unknown menu")
    db.set_setting(f"button_layout_{menu_key}", "")
    return {"success": True}
