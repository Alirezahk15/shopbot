#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShopBot — Web Setup Wizard
Self-contained HTTP server; no pip install needed to start.
Usage: python3 setup/wizard.py
"""

import http.server, json, os, re, secrets, socket, subprocess
import sys, threading, time, urllib.request, urllib.error
from pathlib import Path
from urllib.parse import urlparse

# ─── Paths ───────────────────────────────────────────────────────────────────
WIZARD_PORT = 8080
PROJECT_DIR = Path(__file__).parent.parent.resolve()
INSTALL_DIR = Path("/opt/shopbot")

# ─── Shared state ─────────────────────────────────────────────────────────────
_state = {
    "lang": "fa",
    "config": {},
    "logs": [],
    "progress": 0,
    "done": False,
    "error": None,
    "panel_url": "",
    "panel_password": "",
}
_lock = threading.Lock()

def _log(msg: str):
    with _lock:
        _state["logs"].append(msg)
    print(f"[install] {msg}", flush=True)

def _progress(pct: int, msg: str = ""):
    with _lock:
        _state["progress"] = pct
    if msg:
        _log(msg)

def get_server_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except:
        return "127.0.0.1"

def validate_bot_token(token: str):
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url, headers={"User-Agent": "ShopBot-Setup/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        if data.get("ok"):
            return True, data["result"]
        return False, data.get("description", "Invalid token")
    except urllib.error.URLError as e:
        return False, f"اتصال ناموفق: {e.reason}"
    except Exception as e:
        return False, str(e)

# ─── Installation runner ──────────────────────────────────────────────────────
def _cmd(command: str, label: str, timeout: int = 300):
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, timeout=timeout
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()[:300]
        raise RuntimeError(f"{label}: {err}")
    return result.stdout

def run_install():
    cfg = _state["config"]
    proto = "https" if cfg.get("ssl") else "http"
    domain = cfg.get("domain", "localhost")
    panel_url = f"{proto}://{domain}"

    try:
        # ── 1. System packages ────────────────────────────────────────────────
        _progress(5, "─── مرحله ۱/۹: نصب بسته‌های سیستمی ───")
        _cmd("apt-get update -qq", "apt update")
        _cmd(
            "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "
            "python3 python3-pip python3-venv nginx curl wget git "
            "build-essential libssl-dev certbot python3-certbot-nginx "
            "ufw sqlite3 openssl rsync",
            "نصب بسته‌ها"
        )
        _progress(12, "✅ بسته‌های سیستمی نصب شدند")

        # ── 2. Node.js ────────────────────────────────────────────────────────
        _progress(13, "─── مرحله ۲/۹: Node.js ───")
        r = subprocess.run("node -v 2>/dev/null", shell=True, capture_output=True, text=True)
        ver = r.stdout.strip().lstrip("v").split(".")[0] or "0"
        if int(ver) < 18:
            _log("دانلود Node.js 20...")
            _cmd("curl -fsSL https://deb.nodesource.com/setup_20.x | bash -", "NodeSource", 120)
            _cmd("apt-get install -y -qq nodejs", "نصب nodejs")
        _progress(20, "✅ Node.js آماده است")

        # ── 3. System user ────────────────────────────────────────────────────
        _progress(21, "─── مرحله ۳/۹: کاربر سیستمی ───")
        subprocess.run(
            "id shopbot &>/dev/null || useradd -r -m -d /home/shopbot -s /bin/bash shopbot",
            shell=True
        )
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        _progress(23, "✅ کاربر shopbot آماده است")

        # ── 4. Copy files ─────────────────────────────────────────────────────
        _progress(24, "─── مرحله ۴/۹: کپی فایل‌های پروژه ───")
        _cmd(
            f"rsync -a "
            f"--exclude='.env' --exclude='__pycache__' --exclude='*.pyc' "
            f"--exclude='*.db' --exclude='.git' --exclude='node_modules' "
            f"--exclude='panel/dist' --exclude='venv' --exclude='setup' "
            f"'{PROJECT_DIR}/' '{INSTALL_DIR}/'",
            "rsync"
        )
        _progress(30, "✅ فایل‌ها کپی شدند")

        # ── 5. .env file ──────────────────────────────────────────────────────
        _progress(31, "─── مرحله ۵/۹: فایل تنظیمات ───")
        jwt = secrets.token_hex(32)
        env_lines = [
            "# Telegram Bot",
            f"BOT_TOKEN={cfg.get('bot_token', '')}",
            "",
            "# Admin Panel",
            f"PANEL_PASSWORD={cfg.get('panel_password', '')}",
            f"JWT_SECRET={jwt}",
            "PANEL_PORT=8000",
            f"PANEL_CORS_ORIGINS=https://{domain},http://{domain}",
            "",
            "# Payment APIs (optional)",
            f"BSCSCAN_API_KEY={cfg.get('bscscan_key', '')}",
            f"USD_RATE_API_KEY={cfg.get('navasan_key', '')}",
            f"ZARINPAL_MERCHANT_ID={cfg.get('zarinpal_id', '')}",
        ]
        env_file = INSTALL_DIR / ".env"
        env_file.write_text("\n".join(env_lines) + "\n")
        os.chmod(env_file, 0o600)
        # patch ADMIN_IDS in config.py
        cfg_py = INSTALL_DIR / "config.py"
        if cfg_py.exists():
            txt = cfg_py.read_text()
            txt = re.sub(
                r'ADMIN_IDS\s*=\s*\[.*?\]',
                f'ADMIN_IDS = [{cfg.get("admin_id", "")}]',
                txt
            )
            cfg_py.write_text(txt)
        _progress(38, "✅ فایل .env ساخته شد")

        # ── 6. Python venv ────────────────────────────────────────────────────
        _progress(39, "─── مرحله ۶/۹: محیط Python ───")
        _cmd(f"python3 -m venv {INSTALL_DIR}/venv", "ساخت venv")
        _cmd(f"{INSTALL_DIR}/venv/bin/pip install --upgrade pip -q", "upgrade pip")
        pkgs = (
            "'python-telegram-bot>=20.0' 'fastapi>=0.100.0' "
            "'uvicorn[standard]>=0.23.0' 'python-jose[cryptography]>=3.3.0' "
            "'bcrypt>=4.0.0' 'pydantic>=2.0.0' python-dotenv requests 'passlib[bcrypt]'"
        )
        _cmd(f"{INSTALL_DIR}/venv/bin/pip install -q {pkgs}", "نصب کتابخانه‌ها", 300)
        _progress(58, "✅ کتابخانه‌های Python نصب شدند")

        # ── 7. Build React panel ──────────────────────────────────────────────
        _progress(59, "─── مرحله ۷/۹: Build پنل React ───")
        if (INSTALL_DIR / "panel").exists():
            _log("npm install در حال اجرا (۲-۳ دقیقه)...")
            _cmd(f"cd {INSTALL_DIR}/panel && npm install --silent --no-progress", "npm install", 600)
            _log("npm run build در حال اجرا...")
            _cmd(f"cd {INSTALL_DIR}/panel && npm run build --silent", "npm build", 300)
        _progress(75, "✅ پنل React build شد")

        # ── 8. Nginx + systemd ────────────────────────────────────────────────
        _progress(76, "─── مرحله ۸/۹: Nginx و سرویس‌ها ───")

        # Nginx config — no f-string for $ signs inside nginx directives
        nginx_conf = (
            "server {\n"
            f"    listen 80;\n"
            f"    server_name {domain};\n"
            "    client_max_body_size 20M;\n"
            "    add_header X-Frame-Options SAMEORIGIN always;\n"
            "    add_header X-Content-Type-Options nosniff always;\n\n"
            "    location /api/ {\n"
            "        proxy_pass http://127.0.0.1:8000;\n"
            "        proxy_http_version 1.1;\n"
            "        proxy_set_header Host $host;\n"
            "        proxy_set_header X-Real-IP $remote_addr;\n"
            "        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
            "        proxy_set_header X-Forwarded-Proto $scheme;\n"
            "        proxy_read_timeout 120s;\n"
            "    }\n\n"
            "    location /assets/ {\n"
            f"        root {INSTALL_DIR}/panel/dist;\n"
            "        expires 30d;\n"
            '        add_header Cache-Control "public, immutable";\n'
            "    }\n\n"
            "    location / {\n"
            f"        root {INSTALL_DIR}/panel/dist;\n"
            "        try_files $uri $uri/ /index.html;\n"
            "    }\n"
            "}\n"
        )
        Path("/etc/nginx/sites-available/shopbot").write_text(nginx_conf)
        subprocess.run("ln -sf /etc/nginx/sites-available/shopbot /etc/nginx/sites-enabled/shopbot", shell=True)
        subprocess.run("rm -f /etc/nginx/sites-enabled/default", shell=True)
        _cmd("nginx -t", "تست nginx config")
        _cmd("systemctl reload nginx", "reload nginx")

        svc_bot = (
            "[Unit]\nDescription=ShopBot Bot\nAfter=network-online.target\n\n"
            "[Service]\nType=simple\nUser=shopbot\n"
            f"WorkingDirectory={INSTALL_DIR}\nEnvironmentFile={INSTALL_DIR}/.env\n"
            f"ExecStart={INSTALL_DIR}/venv/bin/python main.py\n"
            "Restart=always\nRestartSec=10\nNoNewPrivileges=true\n\n"
            "[Install]\nWantedBy=multi-user.target\n"
        )
        svc_panel = (
            "[Unit]\nDescription=ShopBot Panel\nAfter=network-online.target\n\n"
            "[Service]\nType=simple\nUser=shopbot\n"
            f"WorkingDirectory={INSTALL_DIR}\nEnvironmentFile={INSTALL_DIR}/.env\n"
            f"ExecStart={INSTALL_DIR}/venv/bin/uvicorn api.main:app "
            "--host 127.0.0.1 --port 8000 --workers 2 --proxy-headers\n"
            "Restart=always\nRestartSec=5\nNoNewPrivileges=true\n\n"
            "[Install]\nWantedBy=multi-user.target\n"
        )
        Path("/etc/systemd/system/shopbot.service").write_text(svc_bot)
        Path("/etc/systemd/system/shopbot-panel.service").write_text(svc_panel)
        _progress(87, "✅ Nginx و systemd پیکربندی شدند")

        # ── 9. Firewall + start ───────────────────────────────────────────────
        _progress(88, "─── مرحله ۹/۹: فایروال و راه‌اندازی ───")
        subprocess.run("ufw --force enable", shell=True, capture_output=True)
        for rule in ["22/tcp", "80/tcp", "443/tcp"]:
            subprocess.run(f"ufw allow {rule}", shell=True, capture_output=True)
        subprocess.run("ufw deny 8000/tcp", shell=True, capture_output=True)
        subprocess.run("ufw deny 8080/tcp", shell=True, capture_output=True)

        if cfg.get("ssl") and domain not in ("localhost", "127.0.0.1"):
            _log("دریافت گواهی SSL از Let's Encrypt...")
            r = subprocess.run(
                f"certbot --nginx -d {domain} --non-interactive --agree-tos "
                f"--email admin@{domain} --redirect",
                shell=True, capture_output=True, text=True, timeout=120
            )
            if r.returncode == 0:
                _log("✅ SSL فعال شد")
                panel_url = f"https://{domain}"
            else:
                _log("⚠️ SSL ناموفق — DNS دامنه را بررسی کنید")

        _cmd(f"chown -R shopbot:shopbot {INSTALL_DIR}", "مجوزها")
        _cmd(f"chmod 600 {INSTALL_DIR}/.env", "امنیت .env")
        _cmd("systemctl daemon-reload", "daemon-reload")
        _cmd("systemctl enable shopbot shopbot-panel", "enable services")
        _cmd("systemctl restart shopbot shopbot-panel", "start services")

        time.sleep(3)
        _progress(100, "🎉 نصب با موفقیت کامل شد!")

        with _lock:
            _state["done"] = True
            _state["panel_url"] = panel_url
            _state["panel_password"] = cfg.get("panel_password", "")

    except Exception as exc:
        _log(f"❌ خطا: {exc}")
        with _lock:
            _state["error"] = str(exc)


# ─── HTTP Handler ─────────────────────────────────────────────────────────────
class WizardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *_): pass

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try: return json.loads(raw)
        except: return {}

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers(); self.wfile.write(body)

    def _html(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self._html(WIZARD_HTML)

        elif path == "/api/state":
            with _lock:
                snap = {k: v for k, v in _state.items() if k != "config"}
            self._json(snap)

        elif path == "/api/logs/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            sent = 0
            try:
                while True:
                    with _lock:
                        logs = list(_state["logs"])
                        prog = _state["progress"]
                        done = _state["done"]
                        err  = _state["error"]
                    while sent < len(logs):
                        payload = json.dumps({"msg": logs[sent], "progress": prog}, ensure_ascii=False)
                        self.wfile.write(f"data: {payload}\n\n".encode())
                        self.wfile.flush()
                        sent += 1
                    if done or err:
                        fin = json.dumps({"msg": "__DONE__", "error": err, "progress": prog}, ensure_ascii=False)
                        self.wfile.write(f"data: {fin}\n\n".encode())
                        self.wfile.flush()
                        break
                    time.sleep(0.4)
            except (BrokenPipeError, ConnectionResetError):
                pass

        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/validate-token":
            ok, info = validate_bot_token(body.get("token", ""))
            self._json({"ok": ok, "info": info})

        elif path == "/api/save":
            with _lock:
                _state["config"].update(body)
            self._json({"ok": True})

        elif path == "/api/install":
            with _lock:
                _state["config"].update(body)
                _state["logs"] = []
                _state["progress"] = 0
                _state["done"] = False
                _state["error"] = None
            threading.Thread(target=run_install, daemon=True).start()
            self._json({"ok": True})

        elif path == "/api/retry":
            with _lock:
                _state["logs"] = []
                _state["progress"] = 0
                _state["done"] = False
                _state["error"] = None
            threading.Thread(target=run_install, daemon=True).start()
            self._json({"ok": True})

        else:
            self.send_error(404)


# ─── Embedded HTML ────────────────────────────────────────────────────────────
WIZARD_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ShopBot Setup</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<style>
:root{--p:#6366f1;--p2:#8b5cf6}
*{box-sizing:border-box}
body{font-family:'Vazirmatn',system-ui,sans-serif;background:#0d0f17;color:#e2e8f0;min-height:100vh}
.card{background:#141720;border:1px solid rgba(255,255,255,.07);border-radius:1rem;padding:1.75rem}
.inp{width:100%;background:#0d0f17;border:1px solid rgba(255,255,255,.1);border-radius:.625rem;
     padding:.75rem 1rem;color:#e2e8f0;font-size:.9rem;outline:none;transition:border .15s}
.inp:focus{border-color:var(--p)}.inp.err{border-color:#f87171}.inp.ok{border-color:#34d399}
.btn{display:inline-flex;align-items:center;gap:.5rem;padding:.7rem 1.5rem;border-radius:.625rem;
     font-weight:600;font-size:.875rem;cursor:pointer;transition:all .15s;border:none}
.btn-primary{background:var(--p);color:#fff;box-shadow:0 4px 15px rgba(99,102,241,.35)}
.btn-primary:hover{filter:brightness(1.1)}.btn-primary:disabled{opacity:.5;cursor:not-allowed}
.btn-secondary{background:rgba(255,255,255,.06);color:#94a3b8;border:1px solid rgba(255,255,255,.08)}
.btn-secondary:hover{background:rgba(255,255,255,.1)}
.step-dot{width:2rem;height:2rem;border-radius:50%;display:flex;align-items:center;
          justify-content:center;font-size:.75rem;font-weight:700;transition:all .3s;flex-shrink:0}
.step-dot.done{background:rgba(52,211,153,.15);color:#34d399;border:1px solid rgba(52,211,153,.3)}
.step-dot.active{background:var(--p);color:#fff;box-shadow:0 0 0 4px rgba(99,102,241,.2)}
.step-dot.pending{background:rgba(255,255,255,.05);color:#64748b;border:1px solid rgba(255,255,255,.08)}
.toggle-wrap{display:flex;background:#0d0f17;border:1px solid rgba(255,255,255,.08);border-radius:.5rem;padding:.2rem}
.toggle-btn{padding:.35rem .8rem;border-radius:.3rem;font-size:.78rem;font-weight:600;cursor:pointer;transition:all .15s;border:none}
.toggle-btn.active{background:var(--p);color:#fff}.toggle-btn.inactive{background:transparent;color:#64748b}
.pay-card{padding:.875rem 1rem;background:#0d0f17;border:1px solid rgba(255,255,255,.07);
          border-radius:.75rem;display:flex;align-items:center;gap:.75rem;cursor:pointer;transition:all .15s;user-select:none}
.pay-card.sel{border-color:rgba(99,102,241,.5);background:rgba(99,102,241,.06)}
.pay-card input[type=checkbox]{width:1rem;height:1rem;accent-color:var(--p);flex-shrink:0;pointer-events:none}
.log-box{font-family:'Courier New',monospace;font-size:.78rem;line-height:1.7;color:#94a3b8;
         background:#0a0c12;border:1px solid rgba(255,255,255,.06);border-radius:.75rem;
         padding:1rem;height:300px;overflow-y:auto}
.log-box .ok{color:#34d399}.log-box .err{color:#f87171}.log-box .info{color:#60a5fa}.log-box .sep{color:#475569}
.prog-bar{height:6px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin-bottom:.5rem}
.prog-fill{height:100%;background:linear-gradient(90deg,var(--p),var(--p2));border-radius:999px;transition:width .4s}
.badge{display:inline-flex;align-items:center;font-size:.72rem;font-weight:600;padding:.2rem .6rem;border-radius:.3rem}
.badge-green{background:rgba(52,211,153,.12);color:#34d399}.badge-red{background:rgba(248,113,113,.12);color:#f87171}
.fade{animation:fadeIn .25s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}
.ltr-inp{direction:ltr;text-align:left}
.hidden{display:none!important}
</style>
</head>
<body class="flex flex-col items-center py-8 px-4">

<!-- Language toggle -->
<div class="w-full max-w-xl mb-4 flex justify-end">
  <div class="toggle-wrap">
    <button class="toggle-btn active"  id="btn-fa" onclick="setLang('fa')">فارسی</button>
    <button class="toggle-btn inactive" id="btn-en" onclick="setLang('en')">English</button>
  </div>
</div>

<!-- Logo -->
<div class="w-full max-w-xl mb-6 text-center fade">
  <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-3"
       style="background:linear-gradient(135deg,#6366f1,#8b5cf6);box-shadow:0 8px 24px rgba(99,102,241,.4)">
    <svg width="32" height="32" fill="none" viewBox="0 0 24 24" stroke="white" stroke-width="1.8">
      <path stroke-linecap="round" stroke-linejoin="round"
        d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-4 4v-4z"/>
    </svg>
  </div>
  <h1 class="text-2xl font-bold text-white" id="t-title">راه‌اندازی ShopBot</h1>
  <p class="text-sm text-gray-500 mt-1" id="t-sub">نصب‌کننده تعاملی — چند مرحله تا راه‌اندازی کامل</p>
</div>

<!-- Step bar -->
<div class="w-full max-w-xl mb-6">
  <div class="flex items-center" id="step-bar"></div>
</div>

<!-- Steps -->
<div class="w-full max-w-xl space-y-0" id="steps-wrap">

  <!-- Step 1: Welcome -->
  <div id="step-1" class="card fade">
    <h2 class="text-lg font-bold text-white mb-1" id="s1-h">خوش‌آمدید 👋</h2>
    <p  class="text-sm text-gray-400 mb-5" id="s1-p">این wizard شما را در نصب کامل ShopBot روی سرور راهنمایی می‌کند.</p>
    <div class="space-y-2.5 mb-6 text-sm text-gray-300">
      <div class="flex items-center gap-2"><span class="text-emerald-400">✓</span><span id="f1">ربات تلگرام فروشگاهی</span></div>
      <div class="flex items-center gap-2"><span class="text-emerald-400">✓</span><span id="f2">پنل مدیریت وب حرفه‌ای</span></div>
      <div class="flex items-center gap-2"><span class="text-emerald-400">✓</span><span id="f3">پرداخت کارت، USDT، TON، زرین‌پال</span></div>
      <div class="flex items-center gap-2"><span class="text-emerald-400">✓</span><span id="f4">VIP، رفرال، گارانتی، کد تخفیف</span></div>
    </div>
    <div class="flex justify-end">
      <button class="btn btn-primary" onclick="goTo(2)">
        <span id="s1-btn">شروع نصب</span>
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7"/>
        </svg>
      </button>
    </div>
  </div>

  <!-- Step 2: Bot Token -->
  <div id="step-2" class="card fade hidden">
    <h2 class="text-lg font-bold text-white mb-1" id="s2-h">🤖 توکن ربات تلگرام</h2>
    <p class="text-sm text-gray-400 mb-4" id="s2-p">از <a href="https://t.me/BotFather" target="_blank" class="text-indigo-400 underline">@BotFather</a> توکن ربات خود را دریافت کنید.</p>
    <label class="block text-xs text-gray-500 mb-1.5" id="s2-lbl">توکن ربات</label>
    <div class="flex gap-2 mb-2">
      <input id="bot-token" class="inp ltr-inp flex-1" placeholder="123456789:AAxxxx..." oninput="clearTokenState()">
      <button class="btn btn-secondary text-xs px-3" id="check-btn" onclick="checkToken()">
        <span id="check-lbl">بررسی</span>
      </button>
    </div>
    <div id="bot-ok" class="hidden mb-3 p-2.5 rounded-lg text-sm"
         style="background:rgba(52,211,153,.08);border:1px solid rgba(52,211,153,.2);color:#34d399"></div>
    <div id="token-err" class="hidden mb-3 text-sm text-red-400"></div>
    <div class="flex justify-between mt-4">
      <button class="btn btn-secondary" onclick="goTo(1)"><span id="s2-back">بازگشت</span></button>
      <button class="btn btn-primary" id="s2-next" onclick="saveToken()" disabled><span id="s2-next-lbl">بعدی</span></button>
    </div>
  </div>

  <!-- Step 3: Admin ID -->
  <div id="step-3" class="card fade hidden">
    <h2 class="text-lg font-bold text-white mb-1" id="s3-h">👤 تنظیمات ادمین</h2>
    <p class="text-sm text-gray-400 mb-4" id="s3-p">آیدی عددی تلگرام خود را وارد کنید (از <a href="https://t.me/userinfobot" target="_blank" class="text-indigo-400 underline">@userinfobot</a> بگیرید).</p>
    <label class="block text-xs text-gray-500 mb-1.5" id="s3-lbl">آیدی عددی تلگرام</label>
    <input id="admin-id" class="inp ltr-inp" placeholder="123456789" type="number">
    <div id="admin-err" class="hidden mt-2 text-sm text-red-400"></div>
    <div class="flex justify-between mt-4">
      <button class="btn btn-secondary" onclick="goTo(2)"><span id="s3-back">بازگشت</span></button>
      <button class="btn btn-primary" onclick="saveAdmin()"><span id="s3-next">بعدی</span></button>
    </div>
  </div>

  <!-- Step 4: Panel config -->
  <div id="step-4" class="card fade hidden">
    <h2 class="text-lg font-bold text-white mb-1" id="s4-h">⚙️ تنظیمات پنل</h2>
    <p class="text-sm text-gray-400 mb-4" id="s4-p">دامنه و رمز ورود پنل مدیریت را مشخص کنید.</p>
    <label class="block text-xs text-gray-500 mb-1.5" id="s4-domain-lbl">دامنه یا IP سرور</label>
    <input id="domain" class="inp ltr-inp mb-3" placeholder="shop.example.com">
    <label class="block text-xs text-gray-500 mb-1.5" id="s4-pass-lbl">رمز پنل مدیریت</label>
    <div class="flex gap-2 mb-3">
      <input id="panel-pass" class="inp ltr-inp flex-1" placeholder="حداقل ۸ کاراکتر">
      <button class="btn btn-secondary text-xs px-3" onclick="genPass()" id="gen-btn">تولید</button>
    </div>
    <label class="flex items-center gap-2 text-sm text-gray-300 cursor-pointer mb-4">
      <input type="checkbox" id="ssl-check" class="w-4 h-4" style="accent-color:var(--p)">
      <span id="s4-ssl">نصب SSL رایگان (Let's Encrypt)</span>
    </label>
    <div id="panel-err" class="hidden text-sm text-red-400 mb-3"></div>
    <div class="flex justify-between">
      <button class="btn btn-secondary" onclick="goTo(3)"><span id="s4-back">بازگشت</span></button>
      <button class="btn btn-primary" onclick="savePanel()"><span id="s4-next">بعدی</span></button>
    </div>
  </div>

  <!-- Step 5: Payments -->
  <div id="step-5" class="card fade hidden">
    <h2 class="text-lg font-bold text-white mb-1" id="s5-h">💳 روش‌های پرداخت</h2>
    <p class="text-sm text-gray-400 mb-4" id="s5-p">روش‌هایی که می‌خواهید فعال باشند را انتخاب کنید.</p>
    <div class="space-y-2 mb-4">
      <div class="pay-card sel" id="pc-card" onclick="togglePay('pay-card','pc-card')">
        <input type="checkbox" id="pay-card" checked>
        <span class="text-xl">🏦</span>
        <div><div class="text-sm font-medium text-white" id="p-card-t">کارت به کارت</div>
             <div class="text-xs text-gray-500" id="p-card-d">تأیید دستی یا خودکار توسط ادمین</div></div>
      </div>
      <div class="pay-card" id="pc-bep20" onclick="togglePay('pay-bep20','pc-bep20')">
        <input type="checkbox" id="pay-bep20">
        <span class="text-xl">💎</span>
        <div><div class="text-sm font-medium text-white">USDT BEP20</div>
             <div class="text-xs text-gray-500" id="p-bep-d">شبکه BSC — نیاز به BscScan API</div></div>
      </div>
      <div class="pay-card" id="pc-trc20" onclick="togglePay('pay-trc20','pc-trc20')">
        <input type="checkbox" id="pay-trc20">
        <span class="text-xl">💠</span>
        <div><div class="text-sm font-medium text-white">USDT TRC20</div>
             <div class="text-xs text-gray-500" id="p-trc-d">شبکه TRON</div></div>
      </div>
      <div class="pay-card" id="pc-ton" onclick="togglePay('pay-ton','pc-ton')">
        <input type="checkbox" id="pay-ton">
        <span class="text-xl">💎</span>
        <div><div class="text-sm font-medium text-white">TON</div>
             <div class="text-xs text-gray-500" id="p-ton-d">شبکه TON Blockchain</div></div>
      </div>
      <div class="pay-card" id="pc-zarinpal" onclick="togglePay('pay-zarinpal','pc-zarinpal')">
        <input type="checkbox" id="pay-zarinpal">
        <span class="text-xl">💰</span>
        <div><div class="text-sm font-medium text-white">زرین‌پال</div>
             <div class="text-xs text-gray-500" id="p-zp-d">درگاه پرداخت ایرانی — نیاز به MerchantID</div></div>
      </div>
    </div>
    <div class="flex justify-between">
      <button class="btn btn-secondary" onclick="goTo(4)"><span id="s5-back">بازگشت</span></button>
      <button class="btn btn-primary" onclick="savePayments()"><span id="s5-next">بعدی</span></button>
    </div>
  </div>

  <!-- Step 6: API Keys -->
  <div id="step-6" class="card fade hidden">
    <h2 class="text-lg font-bold text-white mb-1" id="s6-h">🔑 کلیدهای API</h2>
    <p class="text-sm text-gray-400 mb-4" id="s6-p">برای روش‌های پرداخت انتخابی، کلیدهای API را وارد کنید (اختیاری).</p>
    <div id="api-fields" class="space-y-3"></div>
    <div class="flex justify-between mt-4">
      <button class="btn btn-secondary" onclick="goTo(5)"><span id="s6-back">بازگشت</span></button>
      <button class="btn btn-primary" onclick="saveApiKeys()"><span id="s6-next">بعدی</span></button>
    </div>
  </div>

  <!-- Step 7: Review -->
  <div id="step-7" class="card fade hidden">
    <h2 class="text-lg font-bold text-white mb-1" id="s7-h">📋 مرور نهایی</h2>
    <p class="text-sm text-gray-400 mb-4" id="s7-p">تنظیمات را بررسی کنید سپس نصب را شروع کنید.</p>
    <div id="review-list" class="space-y-0 mb-6 text-sm divide-y" style="border-color:rgba(255,255,255,.05)"></div>
    <div class="flex justify-between">
      <button class="btn btn-secondary" onclick="goTo(6)"><span id="s7-back">بازگشت</span></button>
      <button class="btn btn-primary" id="s7-go" onclick="startInstall()">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
        </svg>
        <span id="s7-btn">شروع نصب</span>
      </button>
    </div>
  </div>

  <!-- Step 8: Installing -->
  <div id="step-8" class="card fade hidden">
    <h2 class="text-lg font-bold text-white mb-1" id="s8-h">⚙️ در حال نصب...</h2>
    <p class="text-sm text-gray-400 mb-4" id="s8-p">لطفاً صبر کنید. این فرآیند ۵ تا ۱۰ دقیقه طول می‌کشد.</p>
    <div class="prog-bar"><div class="prog-fill" id="prog-fill" style="width:0%"></div></div>
    <div class="flex justify-between text-xs text-gray-500 mb-4">
      <span id="prog-label">آماده‌سازی...</span><span id="prog-pct">0%</span>
    </div>
    <div class="log-box" id="log-box"></div>
    <div id="retry-wrap" class="hidden mt-4 space-y-3">
      <div class="text-sm text-red-400 p-3 rounded-lg" style="background:rgba(248,113,113,.08);border:1px solid rgba(248,113,113,.2)" id="err-detail"></div>
      <button class="btn btn-primary w-full justify-center" onclick="retryInstall()">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
        </svg>
        <span id="s8-retry">تلاش مجدد</span>
      </button>
    </div>
  </div>

  <!-- Step 9: Done -->
  <div id="step-9" class="card fade hidden text-center">
    <div class="text-6xl mb-4">🎉</div>
    <h2 class="text-xl font-bold text-white mb-2" id="s9-h">نصب کامل شد!</h2>
    <p class="text-sm text-gray-400 mb-6" id="s9-p">ShopBot با موفقیت روی سرور شما نصب و راه‌اندازی شد.</p>
    <div class="rounded-xl p-4 mb-6 text-start space-y-3"
         style="background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.2)">
      <div class="flex items-center justify-between">
        <span class="text-xs text-gray-500" id="s9-url-lbl">آدرس پنل</span>
        <a id="panel-link" href="#" target="_blank" class="text-indigo-400 text-sm font-mono font-semibold hover:underline">—</a>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-xs text-gray-500" id="s9-pass-lbl">رمز پنل</span>
        <span id="panel-pass-show" class="text-sm font-mono font-bold text-emerald-400">—</span>
      </div>
    </div>
    <a id="go-btn" href="#" target="_blank" class="btn btn-primary w-full justify-center text-base">
      <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
      </svg>
      <span id="s9-go">ورود به پنل مدیریت</span>
    </a>
  </div>

</div><!-- /steps-wrap -->

<script>
// ── State ─────────────────────────────────────────────────────────────────────
let lang = "fa", step = 1;
const cfg = {};
const STEPS = 8;

// ── i18n ──────────────────────────────────────────────────────────────────────
const T = {
  fa:{
    "t-title":"راه‌اندازی ShopBot","t-sub":"نصب‌کننده تعاملی — چند مرحله تا راه‌اندازی کامل",
    "s1-h":"خوش‌آمدید 👋","s1-p":"این wizard شما را در نصب کامل ShopBot روی سرور راهنمایی می‌کند.",
    "s1-btn":"شروع نصب","f1":"ربات تلگرام فروشگاهی","f2":"پنل مدیریت وب حرفه‌ای",
    "f3":"پرداخت کارت، USDT، TON، زرین‌پال","f4":"VIP، رفرال، گارانتی، کد تخفیف",
    "s2-h":"🤖 توکن ربات تلگرام",
    "s2-p":'از <a href="https://t.me/BotFather" target="_blank" class="text-indigo-400 underline">@BotFather</a> توکن ربات خود را دریافت کنید.',
    "s2-lbl":"توکن ربات","check-lbl":"بررسی","s2-back":"بازگشت","s2-next-lbl":"بعدی",
    "s3-h":"👤 تنظیمات ادمین",
    "s3-p":'آیدی عددی تلگرام خود را وارد کنید (از <a href="https://t.me/userinfobot" target="_blank" class="text-indigo-400 underline">@userinfobot</a> بگیرید).',
    "s3-lbl":"آیدی عددی تلگرام","s3-back":"بازگشت","s3-next":"بعدی",
    "s4-h":"⚙️ تنظیمات پنل","s4-p":"دامنه و رمز ورود پنل مدیریت را مشخص کنید.",
    "s4-domain-lbl":"دامنه یا IP سرور","s4-pass-lbl":"رمز پنل مدیریت","gen-btn":"تولید",
    "s4-ssl":"نصب SSL رایگان (Let's Encrypt)","s4-back":"بازگشت","s4-next":"بعدی",
    "s5-h":"💳 روش‌های پرداخت","s5-p":"روش‌هایی که می‌خواهید فعال باشند را انتخاب کنید.",
    "p-card-t":"کارت به کارت","p-card-d":"تأیید دستی یا خودکار توسط ادمین",
    "p-bep-d":"شبکه BSC — نیاز به BscScan API","p-trc-d":"شبکه TRON",
    "p-ton-d":"شبکه TON Blockchain","p-zp-d":"درگاه پرداخت ایرانی — نیاز به MerchantID",
    "s5-back":"بازگشت","s5-next":"بعدی",
    "s6-h":"🔑 کلیدهای API","s6-p":"برای روش‌های پرداخت انتخابی، کلیدهای API را وارد کنید (اختیاری).",
    "s6-back":"بازگشت","s6-next":"بعدی",
    "s7-h":"📋 مرور نهایی","s7-p":"تنظیمات را بررسی کنید سپس نصب را شروع کنید.",
    "s7-back":"بازگشت","s7-btn":"شروع نصب",
    "s8-h":"⚙️ در حال نصب...","s8-p":"لطفاً صبر کنید. این فرآیند ۵ تا ۱۰ دقیقه طول می‌کشد.",
    "s8-retry":"تلاش مجدد",
    "s9-h":"نصب کامل شد! 🎉","s9-p":"ShopBot با موفقیت روی سرور شما نصب و راه‌اندازی شد.",
    "s9-url-lbl":"آدرس پنل","s9-pass-lbl":"رمز پنل","s9-go":"ورود به پنل مدیریت",
    "rv-token":"توکن ربات","rv-admin":"آیدی ادمین","rv-domain":"دامنه",
    "rv-pass":"رمز پنل","rv-ssl":"SSL","rv-pay":"روش‌های پرداخت",
    "yes":"بله","no":"خیر","no-api":"نیازی به کلید API ندارید.",
    "steps":["خوش‌آمد","ربات","ادمین","پنل","پرداخت","API","مرور","نصب"]
  },
  en:{
    "t-title":"ShopBot Setup","t-sub":"Interactive installer — a few steps to full deployment",
    "s1-h":"Welcome 👋","s1-p":"This wizard will guide you through installing ShopBot on your server.",
    "s1-btn":"Start Setup","f1":"Telegram Shop Bot","f2":"Professional Web Admin Panel",
    "f3":"Card, USDT, TON, Zarinpal payments","f4":"VIP, Referral, Warranty, Discounts",
    "s2-h":"🤖 Telegram Bot Token",
    "s2-p":'Get your bot token from <a href="https://t.me/BotFather" target="_blank" class="text-indigo-400 underline">@BotFather</a>.',
    "s2-lbl":"Bot Token","check-lbl":"Validate","s2-back":"Back","s2-next-lbl":"Next",
    "s3-h":"👤 Admin Settings",
    "s3-p":'Enter your Telegram numeric ID (get from <a href="https://t.me/userinfobot" target="_blank" class="text-indigo-400 underline">@userinfobot</a>).',
    "s3-lbl":"Telegram Numeric ID","s3-back":"Back","s3-next":"Next",
    "s4-h":"⚙️ Panel Settings","s4-p":"Set your domain and admin panel password.",
    "s4-domain-lbl":"Server domain or IP","s4-pass-lbl":"Panel password","gen-btn":"Generate",
    "s4-ssl":"Install free SSL (Let's Encrypt)","s4-back":"Back","s4-next":"Next",
    "s5-h":"💳 Payment Methods","s5-p":"Select which payment methods to enable.",
    "p-card-t":"Card Transfer","p-card-d":"Manual or automatic confirmation",
    "p-bep-d":"BSC network — requires BscScan API","p-trc-d":"TRON network",
    "p-ton-d":"TON Blockchain","p-zp-d":"Iranian gateway — requires MerchantID",
    "s5-back":"Back","s5-next":"Next",
    "s6-h":"🔑 API Keys","s6-p":"Enter API keys for selected payment methods (optional).",
    "s6-back":"Back","s6-next":"Next",
    "s7-h":"📋 Review","s7-p":"Review your settings then start installation.",
    "s7-back":"Back","s7-btn":"Start Installation",
    "s8-h":"⚙️ Installing...","s8-p":"Please wait. This takes 5–10 minutes.",
    "s8-retry":"Retry",
    "s9-h":"Installation Complete! 🎉","s9-p":"ShopBot has been successfully installed on your server.",
    "s9-url-lbl":"Panel URL","s9-pass-lbl":"Panel password","s9-go":"Open Admin Panel",
    "rv-token":"Bot token","rv-admin":"Admin ID","rv-domain":"Domain",
    "rv-pass":"Panel password","rv-ssl":"SSL","rv-pay":"Payment methods",
    "yes":"Yes","no":"No","no-api":"No API keys needed.",
    "steps":["Welcome","Bot","Admin","Panel","Payment","API","Review","Install"]
  }
};
const t = k => (T[lang][k] ?? T.fa[k] ?? k);

// ── Language ──────────────────────────────────────────────────────────────────
function setLang(l) {
  lang = l;
  document.documentElement.lang = l;
  document.documentElement.dir  = l === "fa" ? "rtl" : "ltr";
  document.getElementById("btn-fa").className = "toggle-btn " + (l==="fa" ? "active" : "inactive");
  document.getElementById("btn-en").className = "toggle-btn " + (l==="en" ? "active" : "inactive");
  Object.keys(T.fa).forEach(k => {
    const el = document.getElementById(k);
    if (el && el.tagName !== "INPUT") el.innerHTML = t(k);
  });
  buildStepBar();
  buildApiFields();
  buildReview();
}

// ── Step bar ──────────────────────────────────────────────────────────────────
function buildStepBar() {
  const labels = t("steps");
  const bar = document.getElementById("step-bar");
  let html = "";
  for (let i = 1; i <= STEPS; i++) {
    const s = step > i ? "done" : step === i ? "active" : "pending";
    const icon = s === "done"
      ? '<svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>'
      : i;
    const lbl = Array.isArray(labels) ? labels[i-1] : "";
    const lineColor = step > i ? "rgba(52,211,153,.35)" : "rgba(255,255,255,.06)";
    html += `<div class="flex flex-col items-center gap-1" style="flex:1 1 0;min-width:0">
      <div class="step-dot ${s}">${icon}</div>
      <span class="text-[10px] hidden sm:block text-center leading-tight whitespace-nowrap overflow-hidden"
            style="color:${s==="active"?"#818cf8":s==="done"?"#34d399":"#475569"}">${lbl}</span>
    </div>`;
    if (i < STEPS) html += `<div style="flex:1 1 0;height:2px;background:${lineColor};margin-top:.9rem;min-width:4px"></div>`;
  }
  bar.innerHTML = html;
}

// ── Navigation ────────────────────────────────────────────────────────────────
function goTo(n) {
  document.getElementById("step-" + step)?.classList.add("hidden");
  step = n;
  const el = document.getElementById("step-" + n);
  if (el) { el.classList.remove("hidden"); el.classList.add("fade"); }
  buildStepBar();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── Step 2: Token ─────────────────────────────────────────────────────────────
function clearTokenState() {
  ["bot-ok","token-err"].forEach(id => document.getElementById(id)?.classList.add("hidden"));
  document.getElementById("s2-next").disabled = true;
  document.getElementById("bot-token").classList.remove("ok","err");
}
async function checkToken() {
  const token = document.getElementById("bot-token").value.trim();
  if (!token) { showErr("token-err","این فیلد الزامی است"); return; }
  const btn = document.getElementById("check-btn");
  btn.disabled = true;
  btn.innerHTML = '<svg class="spin w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>';
  try {
    const res = await fetch("/api/validate-token", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({token}) });
    const d = await res.json();
    if (d.ok) {
      document.getElementById("bot-ok").innerHTML = `✅ @${d.info.username} — ${d.info.first_name}`;
      document.getElementById("bot-ok").classList.remove("hidden");
      document.getElementById("bot-token").classList.add("ok");
      document.getElementById("s2-next").disabled = false;
      cfg.bot_token = token;
    } else {
      showErr("token-err","❌ " + d.info);
      document.getElementById("bot-token").classList.add("err");
    }
  } catch(e) { showErr("token-err","❌ " + e.message); }
  btn.disabled = false;
  btn.innerHTML = `<span>${t("check-lbl")}</span>`;
}
function saveToken() { if (cfg.bot_token) goTo(3); else checkToken(); }

// ── Step 3: Admin ─────────────────────────────────────────────────────────────
function saveAdmin() {
  const v = document.getElementById("admin-id").value.trim();
  if (!v || !/^\\d+$/.test(v)) { showErr("admin-err", lang==="fa"?"آیدی باید عدد باشد":"ID must be a number"); return; }
  cfg.admin_id = v; goTo(4);
}

// ── Step 4: Panel ─────────────────────────────────────────────────────────────
function genPass() {
  const c = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$";
  let p = ""; for (let i=0;i<16;i++) p += c[Math.floor(Math.random()*c.length)];
  document.getElementById("panel-pass").value = p;
}
function savePanel() {
  const domain = document.getElementById("domain").value.trim();
  const pass   = document.getElementById("panel-pass").value.trim();
  if (!domain) { showErr("panel-err", lang==="fa"?"دامنه الزامی است":"Domain is required"); return; }
  if (pass.length < 8) { showErr("panel-err", lang==="fa"?"رمز باید حداقل ۸ کاراکتر باشد":"Password must be at least 8 characters"); return; }
  cfg.domain = domain; cfg.panel_password = pass; cfg.ssl = document.getElementById("ssl-check").checked;
  goTo(5);
}

// ── Step 5: Payments ──────────────────────────────────────────────────────────
function togglePay(checkId, cardId) {
  const cb = document.getElementById(checkId);
  cb.checked = !cb.checked;
  document.getElementById(cardId).classList.toggle("sel", cb.checked);
}
function savePayments() {
  ["card","bep20","trc20","ton","zarinpal"].forEach(k => {
    cfg["pay_"+k] = document.getElementById("pay-"+k).checked;
  });
  buildApiFields(); goTo(6);
}

// ── Step 6: API Keys ──────────────────────────────────────────────────────────
function buildApiFields() {
  const wrap = document.getElementById("api-fields");
  if (!wrap) return;
  let html = "";
  if (cfg.pay_bep20)
    html += apiField("bscscan-key","BscScan API Key","bscscan_key", lang==="fa"?"برای USDT BEP20":"For USDT BEP20");
  if (cfg.pay_zarinpal)
    html += apiField("zarinpal-id","Zarinpal MerchantID","zarinpal_id", lang==="fa"?"از داشبورد زرین‌پال":"From Zarinpal dashboard");
  html += apiField("navasan-key",
    lang==="fa"?"کلید API نرخ دلار (navasan.tech)":"USD Rate API (navasan.tech)",
    "navasan_key",
    lang==="fa"?"اختیاری":"Optional");
  if (!html) html = `<p class="text-sm text-gray-500 py-2">${t("no-api")}</p>`;
  wrap.innerHTML = html;
  // restore saved values
  ["bscscan_key","zarinpal_id","navasan_key"].forEach(k => {
    const el = document.getElementById(k.replace(/_/g,"-"));
    if (el && cfg[k]) el.value = cfg[k];
  });
}
function apiField(id, label, key, hint) {
  return `<div><label class="block text-xs text-gray-500 mb-1">${label}
    ${hint ? `<span class="text-gray-600 ms-1">(${hint})</span>` : ""}</label>
    <input id="${id}" data-key="${key}" class="inp ltr-inp" placeholder="..."></div>`;
}
function saveApiKeys() {
  document.querySelectorAll("#api-fields input[data-key]").forEach(el => {
    cfg[el.dataset.key] = el.value.trim();
  });
  buildReview(); goTo(7);
}

// ── Step 7: Review ────────────────────────────────────────────────────────────
function buildReview() {
  const el = document.getElementById("review-list");
  if (!el) return;
  const pays = ["card","bep20","trc20","ton","zarinpal"].filter(k => cfg["pay_"+k]);
  const rows = [
    [t("rv-token"),  cfg.bot_token   ? "••••" + cfg.bot_token.slice(-8) : "—"],
    [t("rv-admin"),  cfg.admin_id    || "—"],
    [t("rv-domain"), cfg.domain      || "—"],
    [t("rv-pass"),   cfg.panel_password ? "••••••••" : "—"],
    [t("rv-ssl"),    cfg.ssl ? `<span class="badge badge-green">${t("yes")}</span>` : `<span class="badge badge-red">${t("no")}</span>`],
    [t("rv-pay"),    pays.join(", ") || "—"],
  ];
  el.innerHTML = rows.map(([k,v]) =>
    `<div class="flex items-center justify-between py-2.5">
       <span class="text-gray-400 text-sm">${k}</span>
       <span class="text-white font-medium text-sm">${v}</span>
     </div>`
  ).join("");
}

// ── Step 8: Install ───────────────────────────────────────────────────────────
async function startInstall() {
  document.getElementById("s7-go").disabled = true;
  goTo(8);
  await fetch("/api/install", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(cfg) });
  streamLogs();
}
async function retryInstall() {
  document.getElementById("retry-wrap").classList.add("hidden");
  document.getElementById("log-box").innerHTML = "";
  document.getElementById("prog-fill").style.width = "0%";
  document.getElementById("prog-pct").textContent = "0%";
  document.getElementById("s8-h").textContent = t("s8-h");
  await fetch("/api/retry", { method:"POST", headers:{"Content-Type":"application/json"}, body:"{}" });
  streamLogs();
}
function streamLogs() {
  const box  = document.getElementById("log-box");
  const fill = document.getElementById("prog-fill");
  const pct  = document.getElementById("prog-pct");
  const src  = new EventSource("/api/logs/stream");
  src.onmessage = e => {
    const d = JSON.parse(e.data);
    if (d.msg === "__DONE__") {
      src.close();
      if (d.error) {
        document.getElementById("s8-h").textContent = lang==="fa" ? "خطا در نصب ❌" : "Installation Failed ❌";
        document.getElementById("err-detail").textContent = d.error;
        document.getElementById("retry-wrap").classList.remove("hidden");
      } else {
        fill.style.width = "100%"; pct.textContent = "100%";
        fetch("/api/state").then(r => r.json()).then(s => {
          document.getElementById("panel-link").href = s.panel_url;
          document.getElementById("panel-link").textContent = s.panel_url;
          document.getElementById("panel-pass-show").textContent = s.panel_password;
          document.getElementById("go-btn").href = s.panel_url;
          goTo(9);
        });
      }
      return;
    }
    fill.style.width = d.progress + "%";
    pct.textContent  = d.progress + "%";
    const line = document.createElement("div");
    let cls = "";
    if      (d.msg.startsWith("✅")) cls = "ok";
    else if (d.msg.startsWith("❌") || d.msg.startsWith("⚠️")) cls = "err";
    else if (d.msg.startsWith("───")) cls = "sep";
    else if (d.msg.startsWith("⏳") || d.msg.startsWith("🎉")) cls = "info";
    line.className = cls; line.textContent = d.msg;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
    document.getElementById("prog-label").textContent = d.msg.replace(/^[✅❌⚠️⏳🎉📦─ ]+/, "").slice(0, 40);
  };
  src.onerror = () => src.close();
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function showErr(id, msg) {
  const el = document.getElementById(id);
  if (el) { el.textContent = msg; el.classList.remove("hidden"); }
}

// ── Init ──────────────────────────────────────────────────────────────────────
buildStepBar();
setLang("fa");
</script>
</body>
</html>"""


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ip = get_server_ip()
    server = http.server.HTTPServer(("0.0.0.0", WIZARD_PORT), WizardHandler)

    print()
    print("=" * 56)
    print("  🤖  ShopBot Web Setup Wizard")
    print("=" * 56)
    print()
    print("  برای شروع نصب، این آدرس را در مرورگر باز کنید:")
    print()
    print(f"  ➜  http://{ip}:{WIZARD_PORT}")
    print()
    print("=" * 56)
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Wizard stopped.")
        server.shutdown()
