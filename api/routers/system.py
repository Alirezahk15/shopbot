"""System monitoring, backup/restore, and Linux panel management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from api.auth import verify_token
import sys, os, io, csv, time, shutil, sqlite3, platform, tempfile
import requests as _rq
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import database as db

try:
    import psutil
except Exception:
    psutil = None

router = APIRouter(prefix="/api/system", tags=["system"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "shop.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
ENV_PATH = os.path.join(BASE_DIR, ".env")

try:
    from config import ADMIN_IDS as _ADMIN_IDS
except Exception:
    _ADMIN_IDS = []


# ────────────────── helpers ──────────────────

def _find_procs():
    """Locate the bot and the panel (API) python processes."""
    found = {"bot": None, "panel": None}
    if psutil is None:
        return found
    for p in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            cmd = " ".join(p.info.get("cmdline") or [])
        except Exception:
            continue
        low = cmd.lower().replace("\\", "/")
        if "python" not in low and "uvicorn" not in low:
            continue
        if "uvicorn" in low or "api.main" in low or "api/main" in low:
            found["panel"] = p
        elif low.endswith("main.py") or " main.py" in low or "/main.py" in low:
            found["bot"] = p
    if found["panel"] is None:
        try:
            found["panel"] = psutil.Process(os.getpid())
        except Exception:
            pass
    return found


def _proc_info(p):
    if p is None:
        return {"running": False}
    try:
        with p.oneshot():
            mem = p.memory_info().rss
            return {
                "running": True,
                "pid": p.pid,
                "cpu_percent": p.cpu_percent(interval=None),
                "memory_mb": round(mem / (1024 * 1024), 1),
                "uptime_seconds": int(time.time() - p.create_time()),
            }
    except Exception:
        return {"running": False}


def _make_backup_file(dest_path):
    """Create a consistent snapshot of the live database using the SQLite backup API."""
    src = sqlite3.connect(DB_PATH)
    try:
        dst = sqlite3.connect(dest_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _prune_backups():
    """Keep only the newest N auto/manual backups (pre_restore safety copies are kept)."""
    try:
        keep = int(float(db.get_setting("backup_keep_last", "10") or 10))
    except Exception:
        keep = 10
    if keep <= 0:
        return
    try:
        files = [f for f in os.listdir(BACKUP_DIR) if f.startswith("shop_backup_") and f.endswith(".db")]
        files.sort(reverse=True)
        for name in files[keep:]:
            try:
                os.remove(os.path.join(BACKUP_DIR, name))
            except Exception:
                pass
    except Exception:
        pass


def _tg_send_document(chat_id, path, caption, topic=None):
    token = os.environ.get("BOT_TOKEN", "")
    if not token:
        return False
    try:
        with open(path, "rb") as f:
            data = {"chat_id": chat_id, "caption": caption}
            if topic:
                data["message_thread_id"] = int(topic)
            resp = _rq.post(
                f"https://api.telegram.org/bot{token}/sendDocument",
                data=data,
                files={"document": (os.path.basename(path), f)},
                timeout=60,
            ).json()
        return bool(resp.get("ok"))
    except Exception:
        return False


def _send_backup_to_telegram(path):
    gid = db.get_setting("report_group_id", "") or ""
    topic = db.get_setting("report_topic_backups", "") or ""
    mode = db.get_setting("report_mode", "dm") or "dm"
    caption = "\U0001F5C4 بکاپ دیتابیس — " + datetime.now().strftime("%Y-%m-%d %H:%M")
    sent = False
    if gid and mode in ("group", "both"):
        sent = _tg_send_document(gid, path, caption, topic or None)
    if mode in ("dm", "both") or not sent:
        admin_ids = set(_ADMIN_IDS)
        try:
            admin_ids |= {a["user_id"] for a in db.get_all_admins()}
        except Exception:
            pass
        for aid in admin_ids:
            if _tg_send_document(aid, path, caption):
                sent = True
    return sent


def _update_env(updates):
    lines = []
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
    for key, value in updates.items():
        replaced = False
        for i, ln in enumerate(lines):
            if ln.strip() and not ln.strip().startswith("#") and ln.split("=", 1)[0].strip() == key:
                lines[i] = f"{key}={value}"
                replaced = True
                break
        if not replaced:
            lines.append(f"{key}={value}")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ────────────────── live monitoring ──────────────────

@router.get("/live")
def system_live(_: str = Depends(verify_token)):
    """Real-time CPU / RAM / swap / uptime / per-process stats. Poll every 2-3s."""
    if psutil is None:
        raise HTTPException(status_code=500, detail="psutil is not installed on the server. Run: pip install psutil")
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    cpu_total = psutil.cpu_percent(interval=0.15)
    per_core = psutil.cpu_percent(interval=0.05, percpu=True)
    try:
        load = list(os.getloadavg())
    except Exception:
        load = []
    try:
        freq = psutil.cpu_freq()
        freq_mhz = round(freq.current) if freq else None
    except Exception:
        freq_mhz = None
    try:
        net = psutil.net_io_counters()
        net_info = {"bytes_sent": net.bytes_sent, "bytes_recv": net.bytes_recv}
    except Exception:
        net_info = {}
    procs = _find_procs()
    return {
        "ts": time.time(),
        "cpu": {
            "percent": cpu_total,
            "per_core": per_core,
            "cores": psutil.cpu_count(logical=True),
            "freq_mhz": freq_mhz,
            "load_avg": load,
        },
        "memory": {
            "total_mb": round(vm.total / (1024 * 1024)),
            "used_mb": round(vm.used / (1024 * 1024)),
            "available_mb": round(vm.available / (1024 * 1024)),
            "percent": vm.percent,
        },
        "swap": {
            "total_mb": round(sw.total / (1024 * 1024)),
            "used_mb": round(sw.used / (1024 * 1024)),
            "percent": sw.percent,
        },
        "boot_time": psutil.boot_time(),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "net": net_info,
        "processes": {
            "bot": _proc_info(procs["bot"]),
            "panel": _proc_info(procs["panel"]),
        },
    }


# ────────────────── database tools ──────────────────

@router.post("/db/optimize")
def db_optimize(_: str = Depends(verify_token)):
    size_before = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("VACUUM")
        conn.execute("ANALYZE")
        conn.commit()
    finally:
        conn.close()
    size_after = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    return {
        "success": True,
        "size_before_kb": round(size_before / 1024, 1),
        "size_after_kb": round(size_after / 1024, 1),
        "saved_kb": round((size_before - size_after) / 1024, 1),
    }


@router.get("/db/integrity")
def db_integrity(_: str = Depends(verify_token)):
    conn = sqlite3.connect(DB_PATH)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        tables = []
        for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            try:
                count = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            except Exception:
                count = None
            tables.append({"name": name, "rows": count})
    finally:
        conn.close()
    return {"ok": result == "ok", "result": result, "tables": tables}


# ────────────────── backup & restore ──────────────────

@router.get("/backup/config")
def get_backup_config(_: str = Depends(verify_token)):
    s = db.get_all_settings()
    value = s.get("backup_interval_value", "")
    unit = s.get("backup_interval_unit", "hours")
    # migrate legacy hours-based setting on first read
    if value == "":
        legacy = float(s.get("backup_interval_hours", "0") or 0)
        value = str(int(legacy)) if legacy else "0"
    return {
        "interval_value": value,
        "interval_unit": unit,
        "to_telegram": s.get("backup_to_telegram", "1") == "1",
        "keep_local": s.get("backup_keep_local", "1") == "1",
        "keep_last": s.get("backup_keep_last", "10"),
        "last_backup_ts": s.get("_backup_last_ts", ""),
    }


class BackupConfigRequest(BaseModel):
    interval_value: Optional[float] = None
    interval_unit: Optional[str] = None
    to_telegram: Optional[bool] = None
    keep_local: Optional[bool] = None
    keep_last: Optional[int] = None


@router.post("/backup/config")
def set_backup_config(body: BackupConfigRequest, _: str = Depends(verify_token)):
    if body.interval_unit is not None:
        if body.interval_unit not in ("minutes", "hours", "days"):
            raise HTTPException(status_code=400, detail="Invalid interval unit")
        db.set_setting("backup_interval_unit", body.interval_unit)
    if body.interval_value is not None:
        if body.interval_value < 0:
            raise HTTPException(status_code=400, detail="Invalid interval value")
        unit = body.interval_unit or db.get_setting("backup_interval_unit", "hours") or "hours"
        minutes = body.interval_value * (1 if unit == "minutes" else 60 if unit == "hours" else 1440)
        if 0 < minutes < 5:
            raise HTTPException(status_code=400, detail="Minimum interval is 5 minutes")
        db.set_setting("backup_interval_value", str(body.interval_value))
        # keep legacy key in sync so older code paths never fire twice
        db.set_setting("backup_interval_hours", "0")
    if body.to_telegram is not None:
        db.set_setting("backup_to_telegram", "1" if body.to_telegram else "0")
    if body.keep_local is not None:
        db.set_setting("backup_keep_local", "1" if body.keep_local else "0")
    if body.keep_last is not None:
        db.set_setting("backup_keep_last", str(max(1, min(100, body.keep_last))))
    return {"success": True}


@router.post("/backup/run")
def run_backup_now(_: str = Depends(verify_token)):
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Database file not found")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    name = f"shop_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    path = os.path.join(BACKUP_DIR, name)
    _make_backup_file(path)
    result = {"success": True, "file": name, "size_kb": round(os.path.getsize(path) / 1024, 1)}
    if db.get_setting("backup_to_telegram", "1") == "1":
        result["telegram_sent"] = _send_backup_to_telegram(path)
    if db.get_setting("backup_keep_local", "1") != "1" and result.get("telegram_sent"):
        try:
            os.remove(path)
            result["file"] = None
        except Exception:
            pass
    _prune_backups()
    db.set_setting("_backup_last_ts", str(time.time()))
    return result


@router.get("/backup/list")
def list_backups(_: str = Depends(verify_token)):
    items = []
    if os.path.isdir(BACKUP_DIR):
        for name in os.listdir(BACKUP_DIR):
            if not name.endswith(".db"):
                continue
            full = os.path.join(BACKUP_DIR, name)
            try:
                st = os.stat(full)
                items.append({
                    "name": name,
                    "size_kb": round(st.st_size / 1024, 1),
                    "mtime": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "is_safety": name.startswith("pre_restore_"),
                })
            except Exception:
                continue
    items.sort(key=lambda x: x["mtime"], reverse=True)
    return {"backups": items}


def _safe_backup_path(name: str) -> str:
    if "/" in name or "\\" in name or ".." in name or not name.endswith(".db"):
        raise HTTPException(status_code=400, detail="Invalid file name")
    path = os.path.join(BACKUP_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Backup not found")
    return path


@router.get("/backup/download/{name}")
def download_backup_file(name: str, _: str = Depends(verify_token)):
    path = _safe_backup_path(name)
    return FileResponse(path, media_type="application/octet-stream", filename=name)


@router.delete("/backup/{name}")
def delete_backup_file(name: str, _: str = Depends(verify_token)):
    path = _safe_backup_path(name)
    os.remove(path)
    return {"success": True}


@router.post("/backup/restore")
async def restore_backup(file: UploadFile = File(...), _: str = Depends(verify_token)):
    """Restore an uploaded shop.db. A safety backup of the current DB is made first."""
    content = await file.read()
    if len(content) < 512 or not content.startswith(b"SQLite format 3\x00"):
        raise HTTPException(status_code=400, detail="Not a valid SQLite database file")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.write(content)
    tmp.close()
    try:
        conn = sqlite3.connect(tmp.name)
        try:
            ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
        if ok != "ok":
            raise HTTPException(status_code=400, detail=f"Integrity check failed: {ok}")
        if not {"users", "settings"}.issubset(tables):
            raise HTTPException(status_code=400, detail="This does not look like a bot database (missing core tables)")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        safety_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        safety = os.path.join(BACKUP_DIR, safety_name)
        _make_backup_file(safety)
        try:
            with db.get_db() as c:
                c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except Exception:
            pass
        shutil.copyfile(tmp.name, DB_PATH)
        for ext in ("-wal", "-shm"):
            p = DB_PATH + ext
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
        return {"success": True, "safety_backup": safety_name}
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


# ────────────────── panel config (Linux server) ──────────────────

def _read_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for ln in f.read().splitlines():
                if ln.strip() and not ln.strip().startswith("#") and "=" in ln:
                    k, v = ln.split("=", 1)
                    env[k.strip()] = v.strip()
    return env


@router.get("/panel-config")
def get_panel_config(_: str = Depends(verify_token)):
    env = _read_env()
    s = db.get_all_settings()
    return {
        "port": env.get("PANEL_PORT", os.environ.get("PANEL_PORT", "8000")),
        "host": env.get("PANEL_HOST", os.environ.get("PANEL_HOST", "0.0.0.0")),
        "ip_allowlist": s.get("panel_ip_allowlist", ""),
        "panel_title": s.get("panel_title", ""),
        "os": platform.system(),
    }


class PanelConfigRequest(BaseModel):
    port: Optional[int] = None
    host: Optional[str] = None
    ip_allowlist: Optional[str] = None
    panel_title: Optional[str] = None


@router.post("/panel-config")
def set_panel_config(body: PanelConfigRequest, _: str = Depends(verify_token)):
    restart_required = False
    env_updates = {}
    if body.port is not None:
        if not (1 <= body.port <= 65535):
            raise HTTPException(status_code=400, detail="Invalid port")
        env_updates["PANEL_PORT"] = str(body.port)
        restart_required = True
    if body.host is not None:
        host = body.host.strip()
        if host and all(ch.isdigit() or ch == "." for ch in host) is False and host not in ("localhost",):
            raise HTTPException(status_code=400, detail="Invalid host/bind address")
        env_updates["PANEL_HOST"] = host or "0.0.0.0"
        restart_required = True
    if env_updates:
        _update_env(env_updates)
    if body.ip_allowlist is not None:
        cleaned = ",".join(p.strip() for p in body.ip_allowlist.split(",") if p.strip())
        db.set_setting("panel_ip_allowlist", cleaned)
    if body.panel_title is not None:
        db.set_setting("panel_title", body.panel_title.strip())
    return {"success": True, "restart_required": restart_required}


# ────────────────── panel sessions ──────────────────

@router.get("/sessions")
def list_sessions(_: str = Depends(verify_token)):
    with db.get_db() as conn:
        rows = conn.execute(
            "SELECT sid, user_id, username, ip, user_agent, created_at, status "
            "FROM panel_sessions ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
    return {"sessions": [dict(r) for r in rows]}


class RevokeSessionRequest(BaseModel):
    sid: str


@router.post("/sessions/revoke")
def revoke_session(body: RevokeSessionRequest, _: str = Depends(verify_token)):
    with db.get_db() as conn:
        conn.execute("UPDATE panel_sessions SET status='revoked' WHERE sid=?", (body.sid,))
    return {"success": True}


# ────────────────── CSV export ──────────────────

_EXPORT_TABLES = {
    "sales": "orders",
    "payments": "card_payments",
    "deposits": "transactions",
    "tickets": "tickets",
    "warranty": "warranty_claims",
    "new_users": "users",
}

_DATE_COLUMNS = ("created_at", "date", "timestamp", "joined_at", "created", "time", "updated_at")


@router.get("/export/{category}")
def export_csv(category: str, days: int = 0, _: str = Depends(verify_token)):
    table = _EXPORT_TABLES.get(category)
    if not table:
        raise HTTPException(status_code=404, detail="Unknown export category")
    with db.get_db() as conn:
        cols = [r["name"] for r in conn.execute(f'PRAGMA table_info("{table}")')]
        if not cols:
            raise HTTPException(status_code=404, detail="Table not found")
        date_col = next((c for c in cols if c in _DATE_COLUMNS), None)
        query = f'SELECT * FROM "{table}"'
        params = ()
        if days and date_col:
            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            query += f' WHERE substr("{date_col}", 1, 10) >= ?'
            params = (cutoff,)
        query += " ORDER BY rowid DESC"
        rows = conn.execute(query, params).fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(cols)
    for r in rows:
        writer.writerow([r[c] for c in cols])
    data = ("\ufeff" + buf.getvalue()).encode("utf-8")
    filename = f"{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ────────────────── Linux deploy files ──────────────────

@router.get("/deploy")
def deploy_files(_: str = Depends(verify_token)):
    """Generate ready-to-use Linux deploy files with the current panel port."""
    env = _read_env()
    port = env.get("PANEL_PORT", os.environ.get("PANEL_PORT", "8000"))
    host = env.get("PANEL_HOST", os.environ.get("PANEL_HOST", "0.0.0.0"))
    app_dir = "/opt/shopbot"

    install_sh = f"""#!/bin/bash
# نصب خودکار ربات + پنل روی سرور لینوکس (Ubuntu/Debian)
# اجرا: sudo bash install.sh
set -e
APP_DIR={app_dir}

echo "==> Installing system packages..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nodejs npm nginx

echo "==> Copying project to $APP_DIR ..."
mkdir -p $APP_DIR
cp -r . $APP_DIR
cd $APP_DIR

echo "==> Python virtualenv..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install -r api/requirements.txt

echo "==> Building the panel..."
cd panel && npm install && npm run build && cd ..

echo "==> Installing systemd services..."
cp deploy/shopbot.service /etc/systemd/system/
cp deploy/shopbot-panel.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now shopbot shopbot-panel

echo ""
echo "✅ Done! Panel: http://SERVER_IP:{port}"
echo "   systemctl status shopbot          # وضعیت ربات"
echo "   systemctl status shopbot-panel    # وضعیت پنل"
"""

    bot_service = f"""[Unit]
Description=Telegram Shop Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={app_dir}
ExecStart={app_dir}/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile={app_dir}/.env

[Install]
WantedBy=multi-user.target
"""

    panel_service = f"""[Unit]
Description=Shop Bot Admin Panel (FastAPI)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory={app_dir}
ExecStart={app_dir}/venv/bin/python -m uvicorn api.main:app --host {host} --port {port}
Restart=always
RestartSec=5
EnvironmentFile={app_dir}/.env

[Install]
WantedBy=multi-user.target
"""

    nginx_conf = f"""# /etc/nginx/sites-available/shopbot
# بعد از کپی: ln -s /etc/nginx/sites-available/shopbot /etc/nginx/sites-enabled/ && nginx -t && systemctl reload nginx
# SSL رایگان: apt install certbot python3-certbot-nginx && certbot --nginx -d YOUR_DOMAIN
server {{
    listen 80;
    server_name YOUR_DOMAIN;

    client_max_body_size 50m;

    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}
"""

    return {
        "port": port,
        "files": {
            "install.sh": install_sh,
            "deploy/shopbot.service": bot_service,
            "deploy/shopbot-panel.service": panel_service,
            "deploy/nginx-shopbot.conf": nginx_conf,
        },
    }
