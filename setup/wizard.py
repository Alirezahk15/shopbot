#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ShopBot - Web Setup Wizard
# Self-contained HTTP server; no pip install needed to start.
# Usage: python3 setup/wizard.py
# All backend/terminal output is English on purpose: most SSH terminals
# cannot render Persian correctly. The browser UI is still bilingual.

import http.server
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

WIZARD_PORT = int(os.environ.get("SHOPBOT_WIZARD_PORT", "8080"))
PROJECT_DIR = Path(__file__).parent.parent.resolve()
INSTALL_DIR = Path("/opt/shopbot")
STATE_FILE = Path("/var/lib/shopbot-install-state.json")
NGINX_SITE = Path("/etc/nginx/sites-available/shopbot")


class InstallError(Exception):
    def __init__(self, title, detail="", solutions=None, fatal=True):
        super().__init__(title)
        self.title = title
        self.detail = (detail or "").strip()[:600]
        self.solutions = solutions or []
        self.fatal = fatal

    def as_dict(self):
        return {
            "title": self.title,
            "detail": self.detail,
            "solutions": self.solutions,
            "fatal": self.fatal,
        }


STEPS = [
    ("packages", "System packages", 10),
    ("nodejs", "Node.js runtime", 8),
    ("user", "System user and directories", 4),
    ("files", "Copy project files", 8),
    ("env", "Environment configuration", 5),
    ("venv", "Python virtual environment", 20),
    ("panel", "Build admin panel", 20),
    ("nginx", "Nginx and systemd services", 10),
    ("firewall", "Firewall rules", 3),
    ("ssl", "SSL certificate", 7),
    ("launch", "Start services", 5),
]
TOTAL_WEIGHT = sum(w for _, _, w in STEPS)

_state = {
    "lang": "fa",
    "config": {},
    "logs": [],
    "progress": 0,
    "done": False,
    "error": None,
    "running": False,
    "panel_url": "",
    "panel_password": "",
    "completed": [],
    "steps": [{"key": k, "title": t, "status": "pending"} for k, t, _ in STEPS],
    "warnings": [],
}
_lock = threading.Lock()

# Built React wizard UI (setup/ui/dist). install.sh builds it with Node.
# When the build is missing or failed, we fall back to WIZARD_HTML so the
# installer can never be left without a usable interface.
UI_DIST = Path(__file__).resolve().parent / "ui" / "dist"

_MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".mjs": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".webp": "image/webp",
    ".ico": "image/x-icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".json": "application/json; charset=utf-8",
    ".map": "application/json; charset=utf-8",
}


def react_ui_available():
    try:
        return (UI_DIST / "index.html").is_file()
    except OSError:
        return False



def _log(msg):
    line = str(msg)
    with _lock:
        _state["logs"].append(line)
        if len(_state["logs"]) > 3000:
            del _state["logs"][:800]
    print("[install] " + line, flush=True)


def _warn(msg):
    with _lock:
        _state["warnings"].append(str(msg))
    _log("[WARN] " + str(msg))


def _set_step_status(key, status):
    with _lock:
        for s in _state["steps"]:
            if s["key"] == key:
                s["status"] = status


def _recalc_progress():
    with _lock:
        done = set(_state["completed"])
        earned = sum(w for k, _, w in STEPS if k in done)
        _state["progress"] = int(earned * 100 / TOTAL_WEIGHT)


def _save_state():
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            payload = {
                "completed": list(_state["completed"]),
                "config": _state["config"],
                "ts": time.time(),
            }
        STATE_FILE.write_text(json.dumps(payload))
        os.chmod(STATE_FILE, 0o600)
    except Exception:
        pass


def _load_state():
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            with _lock:
                _state["completed"] = list(data.get("completed", []))
                for s in _state["steps"]:
                    if s["key"] in _state["completed"]:
                        s["status"] = "done"
                saved = data.get("config") or {}
                if saved:
                    _state["config"].update(saved)
            _recalc_progress()
    except Exception:
        pass


def get_server_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_public_ip():
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ShopBot-Setup"})
            with urllib.request.urlopen(req, timeout=6) as r:
                ip = r.read().decode().strip()
            if re.match(r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$", ip):
                return ip
        except Exception:
            continue
    return get_server_ip()


def validate_bot_token(token):
    token = (token or "").strip()
    if not re.match(r"^[0-9]{6,}:[A-Za-z0-9_-]{30,}$", token):
        return False, "Token format looks wrong. Expected 123456789:AAExxxxxxxxxxxxxxxx"
    try:
        url = "https://api.telegram.org/bot" + token + "/getMe"
        req = urllib.request.Request(url, headers={"User-Agent": "ShopBot-Setup/1.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        if data.get("ok"):
            return True, data["result"]
        return False, data.get("description", "Invalid token")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "Telegram rejected this token (401). Create a new one with @BotFather."
        return False, "Telegram API error " + str(e.code)
    except urllib.error.URLError as e:
        return False, "Cannot reach api.telegram.org (" + str(e.reason) + "). Check server DNS/internet."
    except Exception as e:
        return False, str(e)


def _run(command, timeout=300):
    return subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)


def _guess_solutions(err):
    e = (err or "").lower()
    if "lock-frontend" in e or "could not get lock" in e or "unable to acquire" in e:
        return [
            "Another apt/dpkg process is running (usually unattended-upgrades).",
            "See it: ps -eo pid,etime,cmd | grep -E 'apt|dpkg' | grep -v grep",
            "Stop auto-updates: sudo systemctl stop unattended-upgrades",
            "Repair dpkg: sudo dpkg --configure -a && sudo apt-get update",
            "Come back here and click Resume.",
        ]
    if "temporary failure resolving" in e or "could not resolve host" in e or "name or service not known" in e:
        return [
            "The server has no working DNS.",
            "Fix it: echo 'nameserver 8.8.8.8' | sudo tee /etc/resolv.conf",
            "Test: ping -c 3 google.com",
            "Then click Resume.",
        ]
    if "no space left" in e or "disk full" in e:
        return [
            "The disk is full.",
            "Check usage: df -h",
            "Free space: sudo apt-get clean && sudo journalctl --vacuum-size=100M",
            "Then click Resume.",
        ]
    if "killed" in e or "out of memory" in e or "cannot allocate memory" in e or "enomem" in e:
        return [
            "The server ran out of RAM (common on 512MB/1GB VPS during the panel build).",
            "Add swap: sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile",
            "Make it permanent: echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab",
            "Then click Resume.",
        ]
    if "permission denied" in e:
        return [
            "The wizard is not running as root.",
            "Stop it (Ctrl+C) and restart with: sudo bash install.sh",
        ]
    if "address already in use" in e or "bind() to" in e:
        return [
            "Another service already owns port 80/443 (often Apache).",
            "Find it: sudo ss -ltnp | grep -E ':80 |:443 '",
            "Stop Apache if present: sudo systemctl disable --now apache2",
            "Then click Resume.",
        ]
    if "npm err" in e or "eresolve" in e:
        return [
            "npm failed to install the panel dependencies.",
            "Clear the cache: sudo npm cache clean --force",
            "Remove partial modules: sudo rm -rf /opt/shopbot/panel/node_modules",
            "Then click Resume.",
        ]
    if "externally-managed-environment" in e:
        return [
            "Debian/Ubuntu blocked a system-wide pip install.",
            "Install venv support: sudo apt-get install -y python3-venv",
            "Then click Resume.",
        ]
    return [
        "Read the technical detail above - it names the exact failing command.",
        "Full log on the server: /var/log/shopbot-install.log",
        "Fix the reported issue, then click Resume to continue from this step.",
    ]


def _cmd(command, label, timeout=300, solutions=None):
    _log("$ " + command[:200])
    try:
        result = _run(command, timeout)
    except subprocess.TimeoutExpired:
        raise InstallError(
            label + " timed out after " + str(timeout) + "s",
            "Command: " + command[:200],
            (solutions or []) + [
                "The server or its internet connection is very slow.",
                "Check it: ping -c 3 8.8.8.8 and ping -c 3 google.com",
                "Click Resume - the installer continues from this step, it does not start over.",
            ],
        )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "").strip()
        for ln in err.splitlines()[-12:]:
            _log("  | " + ln)
        raise InstallError(label, err[-500:], solutions or _guess_solutions(err))
    return result.stdout


def _apt_locked():
    locks = [
        "/var/lib/dpkg/lock-frontend",
        "/var/lib/dpkg/lock",
        "/var/lib/apt/lists/lock",
        "/var/cache/apt/archives/lock",
    ]
    for f in locks:
        if os.path.exists(f) and _run("fuser " + f, timeout=15).returncode == 0:
            return True
    return _run("pgrep -x unattended-upgr", timeout=15).returncode == 0


def _wait_for_apt(max_wait=420):
    waited = 0
    announced = False
    while _apt_locked():
        if not announced:
            _log("Another package manager is running. Waiting for the apt lock to be released...")
            announced = True
        if waited >= max_wait:
            raise InstallError(
                "Could not acquire the apt/dpkg lock",
                "Waited " + str(max_wait) + "s but /var/lib/dpkg/lock-frontend is still held.",
                [
                    "Find the holder: ps -eo pid,etime,cmd | grep -E 'apt|dpkg' | grep -v grep",
                    "If it is unattended-upgrades: sudo systemctl stop unattended-upgrades",
                    "Kill a stuck process: sudo kill <PID> then sudo kill -9 <PID>",
                    "Repair dpkg: sudo dpkg --configure -a && sudo apt-get update",
                    "Only if no apt process is alive: sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock",
                    "Then click Resume here.",
                ],
            )
        if waited % 20 == 0:
            _log("  ... still waiting for apt (" + str(waited) + "s / " + str(max_wait) + "s)")
        time.sleep(5)
        waited += 5
    return True


def _apt(command, label, timeout=600):
    _wait_for_apt()
    return _cmd("DEBIAN_FRONTEND=noninteractive " + command, label, timeout)


# =============================================================================
#  Installation steps - every step is idempotent and independently re-runnable
# =============================================================================
def step_packages(cfg):
    _log("Updating package lists...")
    _wait_for_apt()
    r = _run("DEBIAN_FRONTEND=noninteractive apt-get update -qq", timeout=300)
    if r.returncode != 0:
        _warn("apt-get update reported problems; continuing with cached lists.")
    _log("Installing system packages (this can take a few minutes)...")
    _apt(
        "apt-get install -y -qq python3 python3-pip python3-venv nginx curl wget git "
        "build-essential libssl-dev certbot python3-certbot-nginx "
        "ufw sqlite3 openssl rsync dnsutils psmisc",
        "Installing system packages",
        900,
    )
    _log("System packages are ready.")


def step_nodejs(cfg):
    r = _run("node -v 2>/dev/null", timeout=30)
    raw = (r.stdout or "").strip().lstrip("v").split(".")[0]
    try:
        major = int(raw)
    except ValueError:
        major = 0
    if major >= 18:
        _log("Node.js v" + raw + " is already installed - skipping.")
        return
    _log("Installing Node.js 20 from NodeSource...")
    _wait_for_apt()
    _cmd(
        "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
        "Adding the NodeSource repository",
        240,
        [
            "The server could not reach deb.nodesource.com.",
            "Test it: curl -I https://deb.nodesource.com",
            "Check DNS: echo 'nameserver 8.8.8.8' | sudo tee /etc/resolv.conf",
            "Or install Node manually: sudo apt-get install -y nodejs npm",
            "Then click Resume.",
        ],
    )
    _apt("apt-get install -y -qq nodejs", "Installing Node.js", 600)
    check = _run("node -v", timeout=30)
    if check.returncode != 0:
        raise InstallError(
            "Node.js installation could not be verified",
            (check.stderr or "").strip(),
            [
                "Install it manually: sudo apt-get install -y nodejs npm",
                "Verify: node -v && npm -v",
                "Then click Resume.",
            ],
        )
    _log("Node.js " + check.stdout.strip() + " installed.")


def step_user(cfg):
    _run("id shopbot >/dev/null 2>&1 || useradd -r -m -d /home/shopbot -s /bin/bash shopbot", timeout=60)
    if _run("id shopbot", timeout=30).returncode != 0:
        raise InstallError(
            "Could not create the shopbot system user",
            "useradd failed.",
            [
                "Create it manually: sudo useradd -r -m -d /home/shopbot -s /bin/bash shopbot",
                "Then click Resume.",
            ],
        )
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    _log("User shopbot and " + str(INSTALL_DIR) + " are ready.")


def step_files(cfg):
    _log("Copying project files to " + str(INSTALL_DIR) + " ...")
    _cmd(
        "rsync -a "
        "--exclude='.env' --exclude='__pycache__' --exclude='*.pyc' "
        "--exclude='*.db' --exclude='.git' --exclude='node_modules' "
        "--exclude='panel/dist' --exclude='venv' --exclude='setup' "
        "'" + str(PROJECT_DIR) + "/' '" + str(INSTALL_DIR) + "/'",
        "Copying project files",
        300,
    )
    if not (INSTALL_DIR / "main.py").exists():
        raise InstallError(
            "Project files were not copied correctly",
            "main.py is missing in " + str(INSTALL_DIR),
            [
                "The source folder looks incomplete. Source used: " + str(PROJECT_DIR),
                "Re-download the project and run install.sh from its root folder.",
                "Then click Resume.",
            ],
        )
    _log("Project files copied.")


def _env_line(key, value):
    """Write a .env entry with a quoted value.
    Unquoted values break on spaces and on ' #', which silently truncates
    passwords and tokens and then looks like a wrong password at login."""
    v = str(value if value is not None else "")
    v = v.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))
    return key + "=" + chr(34) + v + chr(34)


def step_env(cfg):
    domain = cfg.get("domain", "localhost")
    env_file = INSTALL_DIR / ".env"
    jwt = secrets.token_hex(32)
    if env_file.exists():
        m = re.search(r'^JWT_SECRET="?([^"]+)"?$', env_file.read_text(), re.M)
        if m and len(m.group(1).strip()) >= 32:
            jwt = m.group(1).strip()
            _log("Reusing the existing JWT secret so logged-in sessions survive.")
    lines = [
        "# Telegram Bot",
        _env_line("BOT_TOKEN", cfg.get("bot_token", "")),
        "",
        "# Admin Panel",
        _env_line("PANEL_PASSWORD", cfg.get("panel_password", "")),
        _env_line("JWT_SECRET", jwt),
        "PANEL_PORT=8000",
        "PANEL_CORS_ORIGINS=https://" + domain + ",http://" + domain,
        "",
        "# Payment APIs (optional)",
        _env_line("BSCSCAN_API_KEY", cfg.get("bscscan_key", "")),
        _env_line("USD_RATE_API_KEY", cfg.get("navasan_key", "")),
        _env_line("ZARINPAL_MERCHANT_ID", cfg.get("zarinpal_id", "")),
    ]
    env_file.write_text("\n".join(lines) + "\n")
    os.chmod(env_file, 0o600)

    cfg_py = INSTALL_DIR / "config.py"
    if cfg_py.exists():
        txt = cfg_py.read_text()
        txt = re.sub(r"ADMIN_IDS\s*=\s*\[.*?\]", "ADMIN_IDS = [" + str(cfg.get("admin_id", "")) + "]", txt)
        cfg_py.write_text(txt)
    _log(".env written and secured (chmod 600).")


def step_venv(cfg):
    venv = INSTALL_DIR / "venv"
    if not (venv / "bin" / "python").exists():
        _cmd(
            "python3 -m venv " + str(venv),
            "Creating the Python virtual environment",
            180,
            [
                "python3-venv is missing: sudo apt-get install -y python3-venv",
                "Remove a broken venv: sudo rm -rf /opt/shopbot/venv",
                "Then click Resume.",
            ],
        )
    else:
        _log("Virtual environment already exists - reusing it.")
    pip = str(venv / "bin" / "pip")
    _cmd(pip + " install --upgrade pip -q", "Upgrading pip", 300)
    pkgs = (
        "'python-telegram-bot>=20.0' 'fastapi>=0.100.0' "
        "'uvicorn[standard]>=0.23.0' 'python-jose[cryptography]>=3.3.0' "
        "'bcrypt>=4.0.0' 'pydantic>=2.0.0' python-dotenv requests 'passlib[bcrypt]'"
    )
    _log("Installing Python dependencies (2-4 minutes)...")
    _cmd(
        pip + " install -q " + pkgs,
        "Installing Python dependencies",
        900,
        [
            "Usually a slow or blocked connection to pypi.org.",
            "Test it: curl -I https://pypi.org/simple/",
            "If your server is filtered, configure a pip mirror in /etc/pip.conf",
            "Then click Resume.",
        ],
    )
    _log("Python dependencies installed.")


def step_panel(cfg):
    panel = INSTALL_DIR / "panel"
    if not panel.exists():
        _log("No panel/ folder found - skipping the frontend build.")
        return
    if (panel / "dist" / "index.html").exists():
        _log("Panel build already present - skipping.")
        return

    mem_kb = 0
    try:
        for ln in Path("/proc/meminfo").read_text().splitlines():
            if ln.startswith("MemTotal:"):
                mem_kb = int(ln.split()[1])
                break
    except Exception:
        pass
    swap_on = "/swapfile" in _run("swapon --show 2>/dev/null", timeout=30).stdout
    if 0 < mem_kb < 1400000 and not swap_on:
        _log("Low RAM detected (" + str(mem_kb // 1024) + " MB). Creating a 2GB swap file to prevent an OOM kill...")
        _run("fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile", timeout=180)

    _log("Running npm install (2-4 minutes)...")
    _cmd(
        "cd " + str(panel) + " && npm install --silent --no-progress --no-audit --no-fund",
        "npm install",
        1200,
        [
            "Clear the npm cache: sudo npm cache clean --force",
            "Delete partial modules: sudo rm -rf /opt/shopbot/panel/node_modules",
            "If the server has under 1GB RAM, add swap (see the note above).",
            "Then click Resume.",
        ],
    )
    _log("Building the admin panel...")
    _cmd(
        "cd " + str(panel) + " && NODE_OPTIONS=--max-old-space-size=1024 npm run build --silent",
        "npm run build",
        900,
        [
            "The build usually fails from low memory. Add swap:",
            "sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile",
            "Then click Resume.",
        ],
    )
    if not (panel / "dist" / "index.html").exists():
        raise InstallError(
            "The panel build produced no output",
            "panel/dist/index.html is missing.",
            [
                "Run the build manually to see the real error: cd /opt/shopbot/panel && npm run build",
                "Then click Resume.",
            ],
        )
    _log("Admin panel built successfully.")


def _nginx_conf(domain):
    return (
        "server {\n"
        "    listen 80;\n"
        "    server_name " + domain + ";\n"
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
        "    location /.well-known/acme-challenge/ {\n"
        "        root /var/www/html;\n"
        "    }\n\n"
        "    location /assets/ {\n"
        "        root " + str(INSTALL_DIR) + "/panel/dist;\n"
        "        expires 30d;\n"
        '        add_header Cache-Control "public, immutable";\n'
        "    }\n\n"
        "    location / {\n"
        "        root " + str(INSTALL_DIR) + "/panel/dist;\n"
        "        try_files $uri $uri/ /index.html;\n"
        "    }\n"
        "}\n"
    )


def step_nginx(cfg):
    domain = cfg.get("domain", "localhost")
    Path("/etc/nginx/sites-available").mkdir(parents=True, exist_ok=True)
    Path("/etc/nginx/sites-enabled").mkdir(parents=True, exist_ok=True)
    Path("/var/www/html").mkdir(parents=True, exist_ok=True)

    if NGINX_SITE.exists() and "managed by Certbot" in NGINX_SITE.read_text():
        _log("Existing Certbot-managed nginx config detected - keeping it intact.")
    else:
        NGINX_SITE.write_text(_nginx_conf(domain))

    _run("ln -sf /etc/nginx/sites-available/shopbot /etc/nginx/sites-enabled/shopbot", timeout=30)
    _run("rm -f /etc/nginx/sites-enabled/default", timeout=30)
    _cmd(
        "nginx -t",
        "Validating the nginx configuration",
        60,
        [
            "Show the exact problem: sudo nginx -t",
            "Another site may already use this server_name: ls /etc/nginx/sites-enabled/",
            "Then click Resume.",
        ],
    )
    _run("systemctl enable nginx", timeout=60)
    _cmd(
        "systemctl reload nginx || systemctl restart nginx",
        "Reloading nginx",
        90,
        [
            "Inspect the service: sudo systemctl status nginx --no-pager",
            "Something else may hold port 80: sudo ss -ltnp | grep ':80 '",
            "Stop Apache if installed: sudo systemctl disable --now apache2",
            "Then click Resume.",
        ],
    )

    svc_bot = (
        "[Unit]\nDescription=ShopBot Bot\nAfter=network-online.target\n\n"
        "[Service]\nType=simple\nUser=shopbot\n"
        "WorkingDirectory=" + str(INSTALL_DIR) + "\nEnvironmentFile=" + str(INSTALL_DIR) + "/.env\n"
        "ExecStart=" + str(INSTALL_DIR) + "/venv/bin/python main.py\n"
        "Restart=always\nRestartSec=10\nNoNewPrivileges=true\n\n"
        "[Install]\nWantedBy=multi-user.target\n"
    )
    svc_panel = (
        "[Unit]\nDescription=ShopBot Panel\nAfter=network-online.target\n\n"
        "[Service]\nType=simple\nUser=shopbot\n"
        "WorkingDirectory=" + str(INSTALL_DIR) + "\nEnvironmentFile=" + str(INSTALL_DIR) + "/.env\n"
        "ExecStart=" + str(INSTALL_DIR) + "/venv/bin/uvicorn api.main:app "
        "--host 127.0.0.1 --port 8000 --workers 2 --proxy-headers\n"
        "Restart=always\nRestartSec=5\nNoNewPrivileges=true\n\n"
        "[Install]\nWantedBy=multi-user.target\n"
    )
    Path("/etc/systemd/system/shopbot.service").write_text(svc_bot)
    Path("/etc/systemd/system/shopbot-panel.service").write_text(svc_panel)
    _cmd("systemctl daemon-reload", "systemctl daemon-reload", 90)
    _log("Nginx and systemd units configured.")


def step_firewall(cfg):
    if shutil.which("ufw") is None:
        _log("ufw is not installed - skipping firewall rules.")
        return
    for rule in ["22/tcp", "80/tcp", "443/tcp", str(WIZARD_PORT) + "/tcp"]:
        _run("ufw allow " + rule, timeout=60)
    _run("ufw deny 8000/tcp", timeout=60)
    _run("yes | ufw enable", timeout=60)
    _log("Firewall configured: 22, 80, 443 open; 8000 blocked from outside.")


def _domain_points_here(domain):
    server_ip = get_public_ip()
    try:
        resolved = socket.gethostbyname(domain)
    except Exception:
        return False, None, server_ip
    return (resolved == server_ip), resolved, server_ip


def _ssl_solutions(domain, err):
    e = (err or "").lower()
    if "dns problem" in e or "nxdomain" in e or "no valid ip" in e:
        base = [
            "Let's Encrypt could not resolve " + domain + ".",
            "Add an A record for " + domain + " pointing to " + get_public_ip() + " in your DNS panel.",
            "Wait 5-30 minutes for propagation, then verify: dig +short " + domain,
        ]
    elif "timeout" in e or "connection refused" in e or "fetching" in e:
        base = [
            "Let's Encrypt could not reach http://" + domain + "/.well-known/acme-challenge/",
            "Open port 80 in your VPS provider firewall AND in ufw: sudo ufw allow 80/tcp",
            "If Cloudflare proxy (orange cloud) is on, switch it to DNS-only during issuance.",
            "Verify from outside: curl -I http://" + domain,
        ]
    elif "too many" in e or "rate limit" in e:
        base = [
            "You hit the Let's Encrypt rate limit for " + domain + " (5 failures/hour, 5 certs/week).",
            "Wait about one hour, then click Retry SSL only.",
            "Meanwhile the panel works fine over http://" + domain,
        ]
    elif "unauthorized" in e or "403" in e:
        base = [
            "The ACME challenge file was served by the wrong site.",
            "Check enabled sites: ls /etc/nginx/sites-enabled/",
            "Remove conflicting configs, then click Retry SSL only.",
        ]
    else:
        base = [
            "Run certbot manually to see the full reason: sudo certbot --nginx -d " + domain,
            "Check the certbot log: sudo tail -n 40 /var/log/letsencrypt/letsencrypt.log",
        ]
    base.append("Your site keeps working over HTTP - click Retry SSL only any time after fixing this.")
    return base


def step_ssl(cfg):
    domain = cfg.get("domain", "localhost")
    if not cfg.get("ssl"):
        _log("SSL was not requested - skipping.")
        return
    if domain in ("localhost", "127.0.0.1") or re.match(r"^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$", domain):
        _warn("SSL needs a real domain name; '" + domain + "' is an IP or localhost. Skipping SSL.")
        return

    if shutil.which("certbot") is None:
        _log("certbot is missing - installing it...")
        _apt("apt-get install -y -qq certbot python3-certbot-nginx", "Installing certbot", 600)

    existing = Path("/etc/letsencrypt/live/" + domain + "/fullchain.pem")
    if existing.exists():
        _log("A certificate for " + domain + " already exists - reusing it.")
        _run("certbot install --nginx -d " + domain + " --non-interactive --redirect", timeout=180)
        _run("systemctl reload nginx", timeout=60)
        cfg["_ssl_ok"] = True
        return

    _log("Checking that " + domain + " points to this server...")
    ok, resolved, server_ip = _domain_points_here(domain)
    if resolved is None:
        _warn("DNS lookup for " + domain + " failed - certbot will most likely fail too.")
    elif not ok:
        _warn(domain + " resolves to " + str(resolved) + " but this server is " + server_ip +
              ". With Cloudflare proxy this is expected; otherwise fix the A record.")
    else:
        _log("DNS is correct: " + domain + " -> " + server_ip)

    backup = NGINX_SITE.read_text() if NGINX_SITE.exists() else None

    _log("Requesting a certificate from Let's Encrypt...")
    email = cfg.get("ssl_email") or ("admin@" + domain)
    r = _run(
        "certbot --nginx -d " + domain + " --non-interactive --agree-tos --email " + email +
        " --redirect --keep-until-expiring",
        timeout=240,
    )

    if r.returncode != 0:
        err = ((r.stderr or "") + "\n" + (r.stdout or "")).strip()
        for ln in err.splitlines()[-10:]:
            _log("  | " + ln)
        _log("The nginx plugin failed - falling back to the webroot method...")
        Path("/var/www/html/.well-known/acme-challenge").mkdir(parents=True, exist_ok=True)
        r2 = _run(
            "certbot certonly --webroot -w /var/www/html -d " + domain +
            " --non-interactive --agree-tos --email " + email + " --keep-until-expiring",
            timeout=240,
        )
        if r2.returncode == 0:
            _log("Certificate obtained via webroot. Installing it into nginx...")
            r3 = _run("certbot install --nginx -d " + domain + " --non-interactive --redirect", timeout=180)
            if r3.returncode == 0:
                _run("systemctl reload nginx", timeout=60)
                _run("systemctl enable certbot.timer", timeout=60)
                cfg["_ssl_ok"] = True
                _log("SSL is active for " + domain)
                return
            err = (r3.stderr or r3.stdout or err)
        else:
            err = ((r2.stderr or "") + "\n" + (r2.stdout or "")).strip() or err

        _log("SSL failed. Rolling back to the working HTTP configuration...")
        if backup is not None:
            NGINX_SITE.write_text(backup)
        if _run("nginx -t", timeout=60).returncode != 0:
            NGINX_SITE.write_text(_nginx_conf(domain))
        _run("systemctl reload nginx || systemctl restart nginx", timeout=90)
        _log("HTTP configuration restored - your panel is still reachable.")

        raise InstallError(
            "Could not obtain the SSL certificate for " + domain,
            err[-500:],
            _ssl_solutions(domain, err),
            fatal=False,
        )

    _run("systemctl enable certbot.timer", timeout=60)
    _run("systemctl start certbot.timer", timeout=60)
    cfg["_ssl_ok"] = True
    _log("SSL is active for " + domain + " and automatic renewal is enabled.")


def step_launch(cfg):
    _cmd("chown -R shopbot:shopbot " + str(INSTALL_DIR), "Fixing file ownership", 180)
    _run("chmod 600 " + str(INSTALL_DIR) + "/.env", timeout=30)
    _cmd("systemctl daemon-reload", "systemctl daemon-reload", 90)
    _cmd("systemctl enable shopbot shopbot-panel", "Enabling services", 90)
    _run("systemctl restart shopbot shopbot-panel", timeout=120)

    _log("Waiting for the services to come up...")
    time.sleep(6)
    problems = []
    for svc in ("shopbot", "shopbot-panel"):
        active = _run("systemctl is-active " + svc, timeout=30).stdout.strip()
        if active != "active":
            logs = _run("journalctl -u " + svc + " -n 15 --no-pager", timeout=60).stdout
            for ln in logs.splitlines()[-12:]:
                _log("  | " + ln)
            problems.append(svc)

    if problems:
        raise InstallError(
            "Service failed to start: " + ", ".join(problems),
            "systemctl reports it as not active.",
            [
                "See the real error: sudo journalctl -u " + problems[0] + " -n 50 --no-pager",
                "A wrong BOT_TOKEN is the most common cause - check /opt/shopbot/.env",
                "Telegram allows only one polling client - stop any other copy of the bot.",
                "After fixing: sudo systemctl restart shopbot shopbot-panel, then click Resume.",
            ],
        )
    _log("All services are running.")


STEP_FUNCS = {
    "packages": step_packages,
    "nodejs": step_nodejs,
    "user": step_user,
    "files": step_files,
    "env": step_env,
    "venv": step_venv,
    "panel": step_panel,
    "nginx": step_nginx,
    "firewall": step_firewall,
    "ssl": step_ssl,
    "launch": step_launch,
}


# =============================================================================
#  Orchestrator - resumes from the first unfinished step, never starts over
# =============================================================================
def _running_step_key():
    with _lock:
        for s in _state["steps"]:
            if s["status"] == "running":
                return s["key"]
    return None


def run_install(only=None, force=None):
    with _lock:
        _state["running"] = True
        _state["error"] = None
        _state["done"] = False
        cfg = _state["config"]

    if force:
        with _lock:
            _state["completed"] = [c for c in _state["completed"] if c != force]

    with _lock:
        completed = set(_state["completed"])

    domain = cfg.get("domain", "localhost")

    try:
        total = len(STEPS)
        for idx, (key, title, _w) in enumerate(STEPS, start=1):
            if only and key != only:
                continue
            if key in completed and not only:
                _set_step_status(key, "done")
                _log("[" + str(idx) + "/" + str(total) + "] " + title + " - already completed, skipping.")
                continue

            _set_step_status(key, "running")
            _log("")
            _log("==== Step " + str(idx) + "/" + str(total) + ": " + title + " ====")
            try:
                STEP_FUNCS[key](cfg)
            except InstallError:
                raise
            except subprocess.TimeoutExpired:
                raise InstallError(
                    title + " timed out",
                    "The step took too long to finish.",
                    ["Check the network speed of the server, then click Resume."],
                )
            except Exception as exc:
                raise InstallError(title, repr(exc), _guess_solutions(str(exc)))

            _set_step_status(key, "done")
            with _lock:
                if key not in _state["completed"]:
                    _state["completed"].append(key)
            _recalc_progress()
            _save_state()
            _log("[OK] " + title)

        proto = "https" if cfg.get("_ssl_ok") else "http"
        with _lock:
            _state["progress"] = 100
            _state["done"] = True
            _state["running"] = False
            _state["panel_url"] = proto + "://" + domain
            _state["panel_password"] = cfg.get("panel_password", "")
        _log("")
        _log("Installation finished successfully. Panel: " + proto + "://" + domain)

    except InstallError as err:
        failed_key = _running_step_key()
        if failed_key:
            _set_step_status(failed_key, "failed")
        payload = err.as_dict()
        payload["step"] = failed_key
        with _lock:
            _state["error"] = payload
            _state["running"] = False
        _log("")
        _log("[FAILED] " + err.title)
        if err.detail:
            _log("Detail: " + err.detail)
        for i, s in enumerate(err.solutions, 1):
            _log("  Fix " + str(i) + ": " + s)
        _log("Nothing else was undone. Fix the issue and click Resume to continue from this step.")
        _save_state()


def _start(only=None, force=None):
    with _lock:
        if _state["running"]:
            return False
    threading.Thread(target=run_install, kwargs={"only": only, "force": force}, daemon=True).start()
    return True


class WizardHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def _read_body(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, rel):
        """Serve a file from the built React bundle. Returns True if handled."""
        if not react_ui_available():
            return False
        rel = rel.lstrip("/")
        if not rel:
            rel = "index.html"
        try:
            target = (UI_DIST / rel).resolve()
            root = UI_DIST.resolve()
        except OSError:
            return False
        # Block path traversal: never serve outside the dist folder.
        if root != target and root not in target.parents:
            return False
        if not target.is_file():
            return False
        try:
            body = target.read_bytes()
        except OSError:
            return False
        ctype = _MIME.get(target.suffix.lower(), "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        if "/assets/" in "/" + rel:
            self.send_header("Cache-Control", "public, max-age=86400")
        else:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
        return True

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/" or path == "/index.html":
            # Prefer the React build; fall back to the embedded HTML wizard.
            if not self._serve_static("index.html"):
                self._html(WIZARD_HTML)

        elif path == "/api/state":
            with _lock:
                snap = {k: v for k, v in _state.items() if k != "config"}
            self._json(snap)

        elif path == "/api/server-info":
            with _lock:
                resumable = bool(_state["completed"])
            self._json({"ip": get_server_ip(), "resume_available": resumable})

        elif path == "/api/logs/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            sent = 0
            try:
                while True:
                    with _lock:
                        logs = list(_state["logs"])
                        prog = _state["progress"]
                        done = _state["done"]
                        err = _state["error"]
                        steps = [dict(s) for s in _state["steps"]]
                    while sent < len(logs):
                        payload = json.dumps(
                            {"msg": logs[sent], "progress": prog, "steps": steps},
                            ensure_ascii=False,
                        )
                        self.wfile.write(("data: " + payload + "\n\n").encode())
                        self.wfile.flush()
                        sent += 1
                    if done or err:
                        fin = json.dumps(
                            {"msg": "__DONE__", "error": err, "progress": prog, "steps": steps},
                            ensure_ascii=False,
                        )
                        self.wfile.write(("data: " + fin + "\n\n").encode())
                        self.wfile.flush()
                        break
                    time.sleep(0.4)
            except (BrokenPipeError, ConnectionResetError):
                pass

        elif not path.startswith("/api/") and self._serve_static(path):
            pass

        else:
            self.send_error(404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path == "/api/validate-token":
            ok, info = validate_bot_token(body.get("token", ""))
            self._json({"ok": ok, "info": info})

        elif path == "/api/check-domain":
            domain = (body.get("domain") or "").strip()
            if not domain or domain in ("localhost", "127.0.0.1"):
                self._json({"ok": False, "reason": "no-domain"})
                return
            ok, resolved, server_ip = _domain_points_here(domain)
            self._json({"ok": ok, "resolved": resolved, "server_ip": server_ip})

        elif path == "/api/save":
            with _lock:
                _state["config"].update(body)
            self._json({"ok": True})

        elif path == "/api/install":
            with _lock:
                _state["config"].update(body)
                _state["logs"] = []
                _state["warnings"] = []
            self._json({"ok": _start()})

        elif path == "/api/resume":
            self._json({"ok": _start()})

        elif path == "/api/retry-step":
            self._json({"ok": _start(force=body.get("step"))})

        elif path == "/api/retry-ssl":
            with _lock:
                _state["completed"] = [c for c in _state["completed"] if c != "ssl"]
                for s in _state["steps"]:
                    if s["key"] == "ssl":
                        s["status"] = "pending"
            self._json({"ok": _start(only="ssl")})

        elif path == "/api/restart-clean":
            with _lock:
                _state["completed"] = []
                _state["logs"] = []
                _state["progress"] = 0
                _state["error"] = None
                _state["done"] = False
                for s in _state["steps"]:
                    s["status"] = "pending"
            try:
                STATE_FILE.unlink()
            except Exception:
                pass
            self._json({"ok": _start()})

        else:
            self.send_error(404)


# --- Embedded UI (animated, bilingual) ---------------------------------------
WIZARD_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ShopBot Setup</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --p:#6366f1; --p2:#8b5cf6; --p3:#22d3ee;
  --ok:#10b981; --warn:#f59e0b; --err:#ef4444;
  --bg:#070810; --card:rgba(18,20,32,.72); --line:rgba(255,255,255,.09);
  --tx:#e9eaf3; --mut:#8b90a8;
}
html,body{height:100%}
body{
  font-family:'Vazirmatn',system-ui,sans-serif;background:var(--bg);color:var(--tx);
  min-height:100vh;overflow-x:hidden;position:relative;
}

/* ---------- animated background ---------- */
#bgfx{position:fixed;inset:0;z-index:0;overflow:hidden;pointer-events:none}
.orb{position:absolute;border-radius:50%;filter:blur(90px);opacity:.5;animation:float 18s ease-in-out infinite}
.orb.a{width:520px;height:520px;background:radial-gradient(circle,#6366f1,transparent 70%);top:-140px;right:-120px}
.orb.b{width:460px;height:460px;background:radial-gradient(circle,#8b5cf6,transparent 70%);bottom:-160px;left:-120px;animation-delay:-6s}
.orb.c{width:380px;height:380px;background:radial-gradient(circle,#22d3ee,transparent 70%);top:38%;left:44%;animation-delay:-12s;opacity:.28}
@keyframes float{0%,100%{transform:translate(0,0) scale(1)}33%{transform:translate(40px,-45px) scale(1.12)}66%{transform:translate(-35px,35px) scale(.92)}}
#grid{position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.35;
  background-image:linear-gradient(rgba(255,255,255,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.035) 1px,transparent 1px);
  background-size:52px 52px;mask-image:radial-gradient(ellipse 80% 60% at 50% 40%,#000 30%,transparent 100%)}
canvas#stars{position:fixed;inset:0;z-index:0;pointer-events:none}

/* ---------- shell ---------- */
.wrap{position:relative;z-index:2;max-width:920px;margin:0 auto;padding:2.2rem 1.1rem 3.5rem}
.logo{display:flex;align-items:center;justify-content:center;gap:.75rem;margin-bottom:.4rem;animation:dropIn .7s cubic-bezier(.2,.9,.25,1.2) both}
.logo .mark{width:46px;height:46px;border-radius:14px;background:linear-gradient(135deg,var(--p),var(--p2));
  display:grid;place-items:center;font-size:1.4rem;box-shadow:0 8px 28px rgba(99,102,241,.45);animation:pulseGlow 3s ease-in-out infinite}
@keyframes pulseGlow{0%,100%{box-shadow:0 8px 28px rgba(99,102,241,.4)}50%{box-shadow:0 8px 44px rgba(139,92,246,.75)}}
.logo h1{font-size:1.6rem;font-weight:800;background:linear-gradient(90deg,#fff,#a5b4fc,#22d3ee,#fff);
  background-size:280% 100%;-webkit-background-clip:text;background-clip:text;color:transparent;animation:shine 6s linear infinite}
@keyframes shine{to{background-position:280% 0}}
.sub{text-align:center;color:var(--mut);font-size:.86rem;margin-bottom:1.4rem;animation:dropIn .7s .1s both}
@keyframes dropIn{from{opacity:0;transform:translateY(-16px)}to{opacity:1;transform:none}}

/* ---------- top bar ---------- */
.topbar{position:fixed;top:14px;inset-inline-end:16px;z-index:20;display:flex;gap:.5rem}
.chip{background:rgba(255,255,255,.07);border:1px solid var(--line);color:var(--tx);
  padding:.4rem .8rem;border-radius:999px;font-size:.78rem;cursor:pointer;
  backdrop-filter:blur(12px);transition:.25s;font-family:inherit}
.chip:hover{background:rgba(99,102,241,.24);border-color:rgba(99,102,241,.5);transform:translateY(-2px)}

/* ---------- stepper ---------- */
.stepper{display:flex;align-items:center;justify-content:center;gap:0;margin-bottom:1.6rem;flex-wrap:nowrap}
.dot{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;font-size:.76rem;font-weight:700;
  background:rgba(255,255,255,.06);border:1px solid var(--line);color:var(--mut);
  transition:.4s cubic-bezier(.2,.9,.25,1.2);flex-shrink:0}
.dot.on{background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;border-color:transparent;
  transform:scale(1.22);box-shadow:0 0 0 5px rgba(99,102,241,.16),0 6px 18px rgba(99,102,241,.4)}
.dot.ok{background:var(--ok);color:#fff;border-color:transparent}
.bar{height:2px;width:34px;background:rgba(255,255,255,.09);position:relative;overflow:hidden;flex-shrink:0}
.bar i{position:absolute;inset:0;width:0;background:linear-gradient(90deg,var(--p),var(--ok));transition:width .5s ease}
.bar.done i{width:100%}

/* ---------- card ---------- */
.card{background:var(--card);border:1px solid var(--line);border-radius:22px;padding:2rem 1.7rem;
  backdrop-filter:blur(22px);box-shadow:0 24px 70px rgba(0,0,0,.6);position:relative;overflow:hidden}
.card::before{content:"";position:absolute;top:0;inset-inline:0;height:1px;
  background:linear-gradient(90deg,transparent,rgba(139,92,246,.85),transparent);animation:scan 3.4s linear infinite}
@keyframes scan{0%{transform:translateX(-100%)}100%{transform:translateX(100%)}}
.pane{display:none}
.pane.on{display:block;animation:slideUp .5s cubic-bezier(.2,.9,.25,1.1)}
@keyframes slideUp{from{opacity:0;transform:translateY(22px) scale(.985)}to{opacity:1;transform:none}}
h2{font-size:1.28rem;font-weight:700;margin-bottom:.4rem}
.desc{color:var(--mut);font-size:.87rem;line-height:1.85;margin-bottom:1.4rem}

/* ---------- fields ---------- */
.field{margin-bottom:1.1rem;animation:fadeUp .45s both}
.field:nth-child(2){animation-delay:.05s}.field:nth-child(3){animation-delay:.1s}
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
label{display:block;font-size:.83rem;font-weight:600;margin-bottom:.45rem}
.hint{font-size:.75rem;color:var(--mut);margin-top:.35rem;line-height:1.7}
input[type=text],input[type=password],input[type=number]{
  width:100%;padding:.8rem .95rem;background:rgba(8,9,17,.85);border:1px solid var(--line);
  border-radius:12px;color:var(--tx);font-family:inherit;font-size:.9rem;transition:.25s;direction:ltr;text-align:left}
input:focus{outline:none;border-color:var(--p);box-shadow:0 0 0 3px rgba(99,102,241,.16);background:rgba(12,14,26,.95)}
input.bad{border-color:var(--err);animation:shake .35s}
input.good{border-color:var(--ok)}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-7px)}75%{transform:translateX(7px)}}
.err{color:var(--err);font-size:.78rem;margin-top:.35rem;display:none}
.err.show{display:block;animation:fadeUp .3s}

.check{display:flex;align-items:center;gap:.6rem;padding:.85rem 1rem;background:rgba(8,9,17,.7);
  border:1px solid var(--line);border-radius:12px;cursor:pointer;transition:.25s;margin-bottom:.7rem}
.check:hover{border-color:rgba(99,102,241,.45);transform:translateX(-3px)}
.check.sel{border-color:rgba(99,102,241,.6);background:rgba(99,102,241,.09)}
.check input{width:1.05rem;height:1.05rem;accent-color:var(--p);flex-shrink:0}
.check .ico{font-size:1.1rem}

/* ---------- buttons ---------- */
.row{display:flex;gap:.7rem;margin-top:1.6rem}
button.btn{flex:1;padding:.85rem 1.2rem;border:none;border-radius:12px;font-family:inherit;
  font-size:.9rem;font-weight:700;cursor:pointer;transition:.25s;position:relative;overflow:hidden}
.pri{background:linear-gradient(135deg,var(--p),var(--p2));color:#fff;box-shadow:0 6px 22px rgba(99,102,241,.35)}
.pri:hover{transform:translateY(-2px);box-shadow:0 10px 30px rgba(99,102,241,.55)}
.pri:disabled{opacity:.5;cursor:not-allowed;transform:none}
.sec{background:rgba(255,255,255,.07);color:var(--tx);border:1px solid var(--line)}
.sec:hover{background:rgba(255,255,255,.13)}
.ghost{background:transparent;color:var(--mut);border:1px solid var(--line)}
.ghost:hover{color:var(--tx);border-color:var(--p)}
.pri::after{content:"";position:absolute;top:0;inset-inline-start:-100%;width:100%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.28),transparent)}
.pri:hover::after{animation:sweep .7s}
@keyframes sweep{to{inset-inline-start:100%}}

.badge{display:inline-block;padding:.16rem .55rem;border-radius:6px;font-size:.74rem;font-weight:600}
.b-g{background:rgba(16,185,129,.18);color:#34d399}
.b-r{background:rgba(239,68,68,.18);color:#f87171}
.b-y{background:rgba(245,158,11,.18);color:#fbbf24}

.spin{display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.28);
  border-top-color:#fff;border-radius:50%;animation:sp .7s linear infinite;vertical-align:-2px}
@keyframes sp{to{transform:rotate(360deg)}}

table.rev{width:100%;border-collapse:collapse;font-size:.86rem}
table.rev td{padding:.65rem .5rem;border-bottom:1px solid rgba(255,255,255,.06)}
table.rev td:first-child{color:var(--mut);width:42%}
</style>
</head>
<body>
<div id="bgfx"><div class="orb a"></div><div class="orb b"></div><div class="orb c"></div></div>
<div id="grid"></div>
<canvas id="stars"></canvas>

<div class="topbar">
  <button class="chip" onclick="setLang(lang==='fa'?'en':'fa')" id="lang-btn">EN</button>
</div>

<div class="wrap">
  <div class="logo"><div class="mark">&#128722;</div><h1>ShopBot</h1></div>
  <div class="sub" id="tagline">Automated installer &amp; setup wizard</div>

  <div class="stepper" id="stepper"></div>

  <div class="card">
    <!-- 0 WELCOME -->
    <div class="pane on" id="p0">
      <h2 id="w-h">Welcome</h2>
      <div class="desc" id="w-p">This wizard installs ShopBot end to end.</div>
      <div id="resume-box"></div>
      <div class="check sel"><span class="ico">&#129302;</span><span id="f1">Telegram shop bot</span></div>
      <div class="check sel"><span class="ico">&#128202;</span><span id="f2">React admin panel</span></div>
      <div class="check sel"><span class="ico">&#128179;</span><span id="f3">Card, USDT, TON, Zarinpal payments</span></div>
      <div class="check sel"><span class="ico">&#128274;</span><span id="f4">Nginx, systemd, UFW and free SSL</span></div>
      <div class="row"><button class="btn pri" onclick="go(1)" id="w-b">Start</button></div>
    </div>

    <!-- 1 BOT TOKEN -->
    <div class="pane" id="p1">
      <h2 id="s1-h">Bot token</h2>
      <div class="desc" id="s1-p">Create a bot with @BotFather and paste the token here.</div>
      <div class="field">
        <label id="s1-l">Bot Token</label>
        <input type="text" id="bot-token" placeholder="123456789:AAE..." autocomplete="off">
        <div class="err" id="e-token"></div>
        <div class="hint" id="s1-hint">Send /newbot to @BotFather in Telegram.</div>
      </div>
      <div class="row">
        <button class="btn sec" onclick="go(0)" id="b-back1">Back</button>
        <button class="btn pri" onclick="checkToken()" id="b-next1">Verify &amp; continue</button>
      </div>
    </div>

    <!-- 2 ADMIN ID -->
    <div class="pane" id="p2">
      <h2 id="s2-h">Admin account</h2>
      <div class="desc" id="s2-p">Your numeric Telegram ID becomes the bot owner.</div>
      <div class="field">
        <label id="s2-l">Telegram numeric ID</label>
        <input type="text" id="admin-id" placeholder="123456789" inputmode="numeric">
        <div class="err" id="e-admin"></div>
        <div class="hint" id="s2-hint">Get it from @userinfobot.</div>
      </div>
      <div class="row">
        <button class="btn sec" onclick="go(1)" id="b-back2">Back</button>
        <button class="btn pri" onclick="saveAdmin()" id="b-next2">Next</button>
      </div>
    </div>

    <!-- 3 DOMAIN + SSL -->
    <div class="pane" id="p3">
      <h2 id="s3-h">Domain &amp; panel</h2>
      <div class="desc" id="s3-p">Point your domain A record to this server first.</div>
      <div class="field">
        <label id="s3-l1">Domain or server IP</label>
        <input type="text" id="domain" placeholder="shop.example.com">
        <div class="err" id="e-domain"></div>
        <div class="hint" id="dns-status"></div>
      </div>
      <div class="field">
        <label id="s3-l2">Admin panel password</label>
        <input type="password" id="panel-pass" placeholder="At least 8 characters">
        <div class="err" id="e-pass"></div>
      </div>
      <div class="check sel" id="ssl-wrap" onclick="toggleSsl()">
        <input type="checkbox" id="ssl-check" checked onclick="event.stopPropagation();toggleSsl(1)">
        <span class="ico">&#128274;</span><span id="s3-ssl">Install free SSL (Let's Encrypt)</span>
      </div>
      <div class="hint" id="ssl-note">If SSL fails, the installer automatically restores a working HTTP site and lets you retry SSL alone.</div>
      <div class="row">
        <button class="btn sec" onclick="go(2)" id="b-back3">Back</button>
        <button class="btn pri" onclick="saveDomain()" id="b-next3">Next</button>
      </div>
    </div>

    <!-- 4 PAYMENTS -->
    <div class="pane" id="p4">
      <h2 id="s4-h">Payment methods</h2>
      <div class="desc" id="s4-p">Enable the methods you want. You can change these later.</div>
      <div class="check sel" onclick="togglePay('card',this)"><input type="checkbox" id="pay-card" checked><span class="ico">&#128179;</span><span>Card to card</span></div>
      <div class="check" onclick="togglePay('bep20',this)"><input type="checkbox" id="pay-bep20"><span class="ico">&#127974;</span><span>USDT BEP20</span></div>
      <div class="check" onclick="togglePay('trc20',this)"><input type="checkbox" id="pay-trc20"><span class="ico">&#127974;</span><span>USDT TRC20</span></div>
      <div class="check" onclick="togglePay('ton',this)"><input type="checkbox" id="pay-ton"><span class="ico">&#128142;</span><span>TON</span></div>
      <div class="check" onclick="togglePay('zarinpal',this)"><input type="checkbox" id="pay-zarinpal"><span class="ico">&#127974;</span><span>Zarinpal</span></div>
      <div class="row">
        <button class="btn sec" onclick="go(3)" id="b-back4">Back</button>
        <button class="btn pri" onclick="savePays()" id="b-next4">Next</button>
      </div>
    </div>

    <!-- 5 API KEYS -->
    <div class="pane" id="p5">
      <h2 id="s5-h">API keys</h2>
      <div class="desc" id="s5-p">Optional. You can leave them empty and add them later in the panel.</div>
      <div id="api-fields"></div>
      <div class="row">
        <button class="btn sec" onclick="go(4)" id="b-back5">Back</button>
        <button class="btn pri" onclick="saveKeys()" id="b-next5">Next</button>
      </div>
    </div>

    <!-- 6 REVIEW -->
    <div class="pane" id="p6">
      <h2 id="s6-h">Review</h2>
      <div class="desc" id="s6-p">Check everything, then start the installation.</div>
      <table class="rev" id="review"></table>
      <div class="row">
        <button class="btn sec" onclick="go(5)" id="b-back6">Back</button>
        <button class="btn pri" onclick="startInstall()" id="b-install">Install now</button>
      </div>
    </div>

    <!-- 7 PROGRESS -->
    <div class="pane" id="p7">
      <h2 id="s7-h">Installing</h2>
      <div class="desc" id="s7-p">Keep this page open. Each step is saved, so a failure never restarts the whole install.</div>

      <div style="margin-bottom:1rem">
        <div style="display:flex;justify-content:space-between;font-size:.8rem;margin-bottom:.4rem">
          <span id="cur-step">Preparing...</span><span id="pct">0%</span>
        </div>
        <div style="height:9px;background:rgba(255,255,255,.07);border-radius:99px;overflow:hidden">
          <div id="pbar" style="height:100%;width:0;border-radius:99px;transition:width .55s cubic-bezier(.2,.9,.25,1);
            background:linear-gradient(90deg,#6366f1,#8b5cf6,#22d3ee);background-size:200% 100%;animation:shine 2.2s linear infinite"></div>
        </div>
      </div>

      <div id="steplist" style="margin-bottom:1rem"></div>

      <div id="console" style="background:#05060c;border:1px solid var(--line);border-radius:12px;
        padding:.9rem;height:240px;overflow-y:auto;font-family:'JetBrains Mono',monospace;
        font-size:.74rem;line-height:1.75;direction:ltr;text-align:left;white-space:pre-wrap"></div>

      <div id="errbox"></div>
    </div>

    <!-- 8 DONE -->
    <div class="pane" id="p8">
      <div style="text-align:center;padding:1rem 0 1.4rem">
        <div style="font-size:3.6rem;animation:pop .7s cubic-bezier(.2,1.6,.4,1)">&#127881;</div>
        <h2 style="margin-top:.6rem" id="s8-h">Installation complete</h2>
      </div>
      <table class="rev" id="final"></table>
      <div class="row"><button class="btn pri" onclick="openPanel()" id="b-open">Open admin panel</button></div>
    </div>

  </div>
</div>
<style>@keyframes pop{0%{transform:scale(0) rotate(-25deg)}70%{transform:scale(1.25) rotate(8deg)}100%{transform:scale(1) rotate(0)}}</style>
<script>
// ---------- animated starfield ----------
(function(){
  var c=document.getElementById('stars'),x=c.getContext('2d'),ps=[],n=70;
  function size(){c.width=innerWidth;c.height=innerHeight}
  size();addEventListener('resize',size);
  for(var i=0;i<n;i++)ps.push({x:Math.random()*c.width,y:Math.random()*c.height,
    r:Math.random()*1.6+.3,vx:(Math.random()-.5)*.22,vy:(Math.random()-.5)*.22,a:Math.random()*.5+.15});
  (function loop(){
    x.clearRect(0,0,c.width,c.height);
    for(var i=0;i<n;i++){var p=ps[i];p.x+=p.vx;p.y+=p.vy;
      if(p.x<0)p.x=c.width;if(p.x>c.width)p.x=0;if(p.y<0)p.y=c.height;if(p.y>c.height)p.y=0;
      x.beginPath();x.arc(p.x,p.y,p.r,0,6.284);x.fillStyle='rgba(165,180,252,'+p.a+')';x.fill();}
    for(var i=0;i<n;i++)for(var j=i+1;j<n;j++){
      var dx=ps[i].x-ps[j].x,dy=ps[i].y-ps[j].y,d=dx*dx+dy*dy;
      if(d<14000){x.beginPath();x.moveTo(ps[i].x,ps[i].y);x.lineTo(ps[j].x,ps[j].y);
        x.strokeStyle='rgba(99,102,241,'+(1-d/14000)*.13+')';x.lineWidth=.6;x.stroke();}}
    requestAnimationFrame(loop);
  })();
})();

// ---------- i18n ----------
var lang='fa', step=0, cfg={}, installing=false;
var STEP_LABELS_FA={packages:'بسته‌های سیستمی',nodejs:'Node.js',user:'کاربر سیستمی',files:'کپی فایل‌ها',env:'تنظیمات محیطی',venv:'محیط پایتون',panel:'ساخت پنل',nginx:'Nginx و سرویس‌ها',firewall:'فایروال',ssl:'گواهی SSL',launch:'اجرای سرویس‌ها'};

var T={fa:{
 'tagline':'نصب‌کننده خودکار و ویزارد راه‌اندازی',
 'w-h':'خوش آمدید','w-p':'این ویزارد ShopBot را به‌صورت کامل روی سرور شما نصب می‌کند. هر مرحله ذخیره می‌شود؛ اگر خطایی رخ دهد، نصب از همان‌جا ادامه پیدا می‌کند و از اول شروع نمی‌شود.',
 'f1':'ربات فروشگاهی تلگرام','f2':'پنل مدیریت React','f3':'پرداخت کارت، USDT، TON، زرین‌پال','f4':'Nginx، systemd، فایروال و SSL رایگان','w-b':'شروع نصب',
 's1-h':'توکن ربات','s1-p':'در تلگرام به @BotFather پیام دهید، ربات بسازید و توکن را اینجا بگذارید.','s1-l':'توکن ربات','s1-hint':'دستور /newbot را برای @BotFather بفرستید.',
 'b-back1':'بازگشت','b-next1':'بررسی و ادامه',
 's2-h':'حساب مدیر','s2-p':'شناسه عددی تلگرام شما مالک ربات می‌شود.','s2-l':'شناسه عددی تلگرام','s2-hint':'از @userinfobot بگیرید.','b-back2':'بازگشت','b-next2':'بعدی',
 's3-h':'دامنه و پنل','s3-p':'قبل از ادامه، رکورد A دامنه را به IP همین سرور وصل کنید.','s3-l1':'دامنه یا IP سرور','s3-l2':'رمز عبور پنل مدیریت','s3-ssl':'دریافت SSL رایگان (Let\u0027s Encrypt)',
 'ssl-note':'اگر گرفتن SSL شکست بخورد، نصب‌کننده خودش تنظیمات سالم HTTP را برمی‌گرداند و می‌توانید فقط SSL را دوباره تلاش کنید.',
 'b-back3':'بازگشت','b-next3':'بعدی',
 's4-h':'روش‌های پرداخت','s4-p':'روش‌های دلخواه را فعال کنید. بعداً هم قابل تغییر است.','b-back4':'بازگشت','b-next4':'بعدی',
 's5-h':'کلیدهای API','s5-p':'اختیاری است. می‌توانید خالی بگذارید و بعداً از پنل وارد کنید.','b-back5':'بازگشت','b-next5':'بعدی',
 's6-h':'مرور نهایی','s6-p':'همه‌چیز را بررسی کنید و نصب را شروع کنید.','b-back6':'بازگشت','b-install':'شروع نصب',
 's7-h':'در حال نصب','s7-p':'این صفحه را باز نگه دارید. هر مرحله ذخیره می‌شود؛ خطا باعث شروع مجدد کل نصب نمی‌شود.',
 's8-h':'نصب با موفقیت کامل شد','b-open':'باز کردن پنل مدیریت',
 'e-token':'توکن نامعتبر است','e-admin':'شناسه عددی معتبر وارد کنید','e-domain':'دامنه یا IP را وارد کنید','e-pass':'رمز باید حداقل ۸ کاراکتر باشد',
 'rv-bot':'ربات','rv-admin':'شناسه مدیر','rv-domain':'دامنه','rv-pass':'رمز پنل','rv-ssl':'SSL','rv-pay':'روش‌های پرداخت','yes':'بله','no':'خیر',
 'fix-title':'چطور این مشکل را حل کنم؟','detail':'جزئیات فنی','resume':'ادامه از همین مرحله','retry-step':'تلاش دوباره این مرحله','retry-ssl':'فقط SSL را دوباره بگیر','clean':'نصب کامل از اول','skip-note':'مراحل انجام‌شده دوباره اجرا نمی‌شوند.',
 'resume-found':'یک نصب ناتمام پیدا شد. می‌توانید از همان‌جا ادامه دهید.','resume-btn':'ادامه نصب قبلی',
 'dns-ok':'✅ دامنه به این سرور اشاره می‌کند','dns-bad':'⚠️ دامنه به این سرور اشاره نمی‌کند','dns-none':'⚠️ دامنه قابل resolve نیست — رکورد A را بسازید','checking':'در حال بررسی...',
 'panel-url':'آدرس پنل','panel-pass2':'رمز پنل','ssl-state':'وضعیت SSL','ssl-on':'فعال','ssl-off':'غیرفعال (HTTP)'
},en:{
 'tagline':'Automated installer and setup wizard',
 'w-h':'Welcome','w-p':'This wizard installs ShopBot end to end. Every step is checkpointed, so if something fails the installer resumes from that step instead of starting over.',
 'f1':'Telegram shop bot','f2':'React admin panel','f3':'Card, USDT, TON, Zarinpal payments','f4':'Nginx, systemd, firewall and free SSL','w-b':'Start',
 's1-h':'Bot token','s1-p':'Create a bot with @BotFather on Telegram and paste its token here.','s1-l':'Bot Token','s1-hint':'Send /newbot to @BotFather.',
 'b-back1':'Back','b-next1':'Verify and continue',
 's2-h':'Admin account','s2-p':'Your numeric Telegram ID becomes the bot owner.','s2-l':'Telegram numeric ID','s2-hint':'Get it from @userinfobot.','b-back2':'Back','b-next2':'Next',
 's3-h':'Domain and panel','s3-p':'Point the A record of your domain to this server first.','s3-l1':'Domain or server IP','s3-l2':'Admin panel password','s3-ssl':'Install free SSL (Let\u0027s Encrypt)',
 'ssl-note':'If SSL fails, the installer restores a working HTTP site automatically and lets you retry SSL on its own.',
 'b-back3':'Back','b-next3':'Next',
 's4-h':'Payment methods','s4-p':'Enable the methods you want. You can change them later.','b-back4':'Back','b-next4':'Next',
 's5-h':'API keys','s5-p':'Optional. Leave empty and add them later from the panel.','b-back5':'Back','b-next5':'Next',
 's6-h':'Review','s6-p':'Check everything, then start the installation.','b-back6':'Back','b-install':'Install now',
 's7-h':'Installing','s7-p':'Keep this page open. Each step is saved, so a failure never restarts the whole install.',
 's8-h':'Installation complete','b-open':'Open admin panel',
 'e-token':'Invalid token','e-admin':'Enter a valid numeric ID','e-domain':'Enter a domain or IP','e-pass':'Password must be at least 8 characters',
 'rv-bot':'Bot','rv-admin':'Admin ID','rv-domain':'Domain','rv-pass':'Panel password','rv-ssl':'SSL','rv-pay':'Payment methods','yes':'Yes','no':'No',
 'fix-title':'How to fix this','detail':'Technical detail','resume':'Resume from this step','retry-step':'Retry this step','retry-ssl':'Retry SSL only','clean':'Full clean reinstall','skip-note':'Completed steps are not re-run.',
 'resume-found':'An unfinished installation was found. You can continue from where it stopped.','resume-btn':'Resume previous install',
 'dns-ok':'DNS OK - the domain points to this server','dns-bad':'The domain does not point to this server','dns-none':'Domain cannot be resolved - create an A record','checking':'Checking...',
 'panel-url':'Panel URL','panel-pass2':'Panel password','ssl-state':'SSL status','ssl-on':'Active','ssl-off':'Disabled (HTTP)'
}};

function t(k){return (T[lang]&&T[lang][k])||(T.en[k])||k}
function setLang(L){
  lang=L;
  document.documentElement.lang=L;
  document.documentElement.dir=(L==='fa')?'rtl':'ltr';
  document.getElementById('lang-btn').textContent=(L==='fa')?'EN':'FA';
  var keys=Object.keys(T[L]);
  for(var i=0;i<keys.length;i++){var el=document.getElementById(keys[i]);if(el)el.textContent=T[L][keys[i]]}
  renderSteps();
  if(step===6)renderReview();
}

// ---------- stepper ----------
var TOTAL=7;
function renderStepper(){
  var h='';
  for(var i=0;i<TOTAL;i++){
    var cl=(i<step)?'dot ok':(i===step?'dot on':'dot');
    h+='<div class="'+cl+'">'+(i<step?'&#10003;':(i+1))+'</div>';
    if(i<TOTAL-1)h+='<div class="bar'+(i<step?' done':'')+'"><i></i></div>';
  }
  document.getElementById('stepper').innerHTML=h;
}
function go(n){
  var cur=document.querySelector('.pane.on'); if(cur)cur.classList.remove('on');
  step=n;
  document.getElementById('p'+n).classList.add('on');
  document.getElementById('stepper').style.display=(n>=7)?'none':'flex';
  renderStepper();
  window.scrollTo({top:0,behavior:'smooth'});
}
function showErr(id,msg){var e=document.getElementById(id);e.textContent=msg;e.classList.add('show')}
function clrErr(id){document.getElementById(id).classList.remove('show')}

// ---------- api ----------
function api(url,data){
  return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data||{})}).then(function(r){return r.json()});
}

// ---------- step 1 ----------
function checkToken(){
  var el=document.getElementById('bot-token'), v=el.value.trim(), b=document.getElementById('b-next1');
  clrErr('e-token'); el.classList.remove('bad','good');
  if(!v){el.classList.add('bad');showErr('e-token',t('e-token'));return}
  b.disabled=true; b.innerHTML='<span class="spin"></span>';
  api('/api/validate-token',{token:v}).then(function(r){
    b.disabled=false; b.textContent=t('b-next1');
    if(r.ok){
      el.classList.add('good'); cfg.bot_token=v; cfg.bot_username=r.info.username;
      api('/api/save',{bot_token:v}); go(2);
    }else{ el.classList.add('bad'); showErr('e-token',(typeof r.info==='string')?r.info:t('e-token')); }
  }).catch(function(){b.disabled=false;b.textContent=t('b-next1');showErr('e-token','Network error')});
}

// ---------- step 2 ----------
function saveAdmin(){
  var el=document.getElementById('admin-id'), v=el.value.trim();
  clrErr('e-admin'); el.classList.remove('bad','good');
  if(!/^[0-9]{5,}$/.test(v)){el.classList.add('bad');showErr('e-admin',t('e-admin'));return}
  el.classList.add('good'); cfg.admin_id=v; api('/api/save',{admin_id:v}); go(3);
}

// ---------- step 3 ----------
var dnsTimer=null;
function toggleSsl(fromInput){
  var c=document.getElementById('ssl-check');
  if(!fromInput)c.checked=!c.checked;
  document.getElementById('ssl-wrap').classList.toggle('sel',c.checked);
}
document.addEventListener('input',function(e){
  if(e.target.id!=='domain')return;
  clearTimeout(dnsTimer);
  var v=e.target.value.trim();
  var s=document.getElementById('dns-status');
  if(!v||/^[0-9.]+$/.test(v)){s.textContent='';return}
  s.textContent=t('checking');
  dnsTimer=setTimeout(function(){
    api('/api/check-domain',{domain:v}).then(function(r){
      if(r.ok)s.innerHTML='<span style="color:#34d399">'+t('dns-ok')+'</span>';
      else if(!r.resolved)s.innerHTML='<span style="color:#fbbf24">'+t('dns-none')+'</span>';
      else s.innerHTML='<span style="color:#fbbf24">'+t('dns-bad')+' ('+r.resolved+' &ne; '+r.server_ip+')</span>';
    }).catch(function(){s.textContent=''});
  },700);
});
function saveDomain(){
  var d=document.getElementById('domain'), p=document.getElementById('panel-pass');
  var dv=d.value.trim(), pv=p.value;
  clrErr('e-domain'); clrErr('e-pass'); d.classList.remove('bad'); p.classList.remove('bad');
  var bad=false;
  if(!dv){d.classList.add('bad');showErr('e-domain',t('e-domain'));bad=true}
  if(pv.length<8){p.classList.add('bad');showErr('e-pass',t('e-pass'));bad=true}
  if(bad)return;
  cfg.domain=dv; cfg.panel_password=pv; cfg.ssl=document.getElementById('ssl-check').checked;
  api('/api/save',{domain:dv,panel_password:pv,ssl:cfg.ssl}); go(4);
}

// ---------- step 4 ----------
function togglePay(k,row){
  var c=document.getElementById('pay-'+k);
  c.checked=!c.checked;
  row.classList.toggle('sel',c.checked);
}
function savePays(){
  var ks=['card','bep20','trc20','ton','zarinpal'];
  for(var i=0;i<ks.length;i++)cfg['pay_'+ks[i]]=document.getElementById('pay-'+ks[i]).checked;
  buildKeys(); go(5);
}
function keyField(id,label,hint){
  return '<div class="field"><label>'+label+'</label><input type="text" id="'+id+'" autocomplete="off">'+
         '<div class="hint">'+hint+'</div></div>';
}
function buildKeys(){
  var h='';
  if(cfg.pay_bep20)h+=keyField('bscscan-key','BscScan API Key',lang==='fa'?'برای بررسی تراکنش‌های USDT BEP20':'For USDT BEP20 transaction checks');
  if(cfg.pay_zarinpal)h+=keyField('zarinpal-id','Zarinpal Merchant ID',lang==='fa'?'از داشبورد زرین‌پال':'From the Zarinpal dashboard');
  h+=keyField('navasan-key',lang==='fa'?'کلید API نرخ دلار (navasan.tech)':'USD rate API key (navasan.tech)',lang==='fa'?'اختیاری — برای تبدیل نرخ ارز':'Optional - used for currency conversion');
  document.getElementById('api-fields').innerHTML=h;
}
function saveKeys(){
  var map={'bscscan-key':'bscscan_key','zarinpal-id':'zarinpal_id','navasan-key':'navasan_key'};
  for(var id in map){var el=document.getElementById(id);if(el)cfg[map[id]]=el.value.trim()}
  api('/api/save',cfg); renderReview(); go(6);
}

// ---------- step 6 ----------
function renderReview(){
  var pays=['card','bep20','trc20','ton','zarinpal'].filter(function(k){return cfg['pay_'+k]});
  var rows=[
    [t('rv-bot'), cfg.bot_username?('@'+cfg.bot_username):'-'],
    [t('rv-admin'), cfg.admin_id||'-'],
    [t('rv-domain'), cfg.domain||'-'],
    [t('rv-pass'), '••••••••'],
    [t('rv-ssl'), cfg.ssl?'<span class="badge b-g">'+t('yes')+'</span>':'<span class="badge b-r">'+t('no')+'</span>'],
    [t('rv-pay'), pays.join(', ')||'-']
  ];
  var h='';
  for(var i=0;i<rows.length;i++)h+='<tr><td>'+rows[i][0]+'</td><td>'+rows[i][1]+'</td></tr>';
  document.getElementById('review').innerHTML=h;
}

// ---------- install ----------
function startInstall(){ api('/api/install',cfg).then(function(){beginStream()}); go(7); }
function resumeInstall(){ document.getElementById('errbox').innerHTML=''; api('/api/resume',{}).then(function(){beginStream()}); go(7); }
function retryStep(k){ document.getElementById('errbox').innerHTML=''; api('/api/retry-step',{step:k}).then(function(){beginStream()}); }
function retrySsl(){ document.getElementById('errbox').innerHTML=''; api('/api/retry-ssl',{}).then(function(){beginStream()}); }
function cleanInstall(){ document.getElementById('errbox').innerHTML=''; document.getElementById('console').innerHTML=''; api('/api/restart-clean',{}).then(function(){beginStream()}); }

function renderSteps(list){
  if(list)window._steps=list;
  var arr=window._steps||[]; var h='';
  for(var i=0;i<arr.length;i++){
    var s=arr[i];
    var icon='<span style="opacity:.35">&#9675;</span>', col='var(--mut)';
    if(s.status==='done'){icon='<span style="color:#34d399">&#10003;</span>';col='#9aa0b8'}
    else if(s.status==='running'){icon='<span class="spin" style="border-top-color:#818cf8"></span>';col='#c7d2fe'}
    else if(s.status==='failed'){icon='<span style="color:#f87171">&#10007;</span>';col='#fca5a5'}
    var label=(lang==='fa'&&STEP_LABELS_FA[s.key])?STEP_LABELS_FA[s.key]:s.title;
    h+='<div style="display:flex;align-items:center;gap:.55rem;font-size:.79rem;color:'+col+';padding:.16rem 0">'+icon+'<span>'+label+'</span></div>';
  }
  document.getElementById('steplist').innerHTML=h;
}

function addLine(msg){
  var c=document.getElementById('console');
  var col='#9aa4bf';
  if(msg.indexOf('[OK]')===0||msg.indexOf('successfully')>-1)col='#34d399';
  else if(msg.indexOf('[FAILED]')===0)col='#f87171';
  else if(msg.indexOf('[WARN]')===0)col='#fbbf24';
  else if(msg.indexOf('====')===0)col='#818cf8';
  else if(msg.indexOf('$ ')===0)col='#64748b';
  else if(msg.indexOf('  Fix ')===0)col='#fbbf24';
  var d=document.createElement('div');
  d.style.color=col; d.style.animation='fadeUp .2s';
  d.textContent=msg;
  c.appendChild(d); c.scrollTop=c.scrollHeight;
}

function showError(err){
  var sols='';
  for(var i=0;i<(err.solutions||[]).length;i++){
    sols+='<div style="display:flex;gap:.5rem;padding:.3rem 0;font-size:.8rem;line-height:1.8">'+
      '<span style="color:#fbbf24;font-weight:700;flex-shrink:0">'+(i+1)+'.</span>'+
      '<span style="direction:ltr;text-align:left;font-family:\'JetBrains Mono\',monospace;font-size:.74rem;color:#e5e7eb">'+
      String(err.solutions[i]).replace(/&/g,'&amp;').replace(/</g,'&lt;')+'</span></div>';
  }
  var extra='';
  if(err.step==='ssl')extra='<button class="btn sec" onclick="retrySsl()">'+t('retry-ssl')+'</button>';
  document.getElementById('errbox').innerHTML=
    '<div style="margin-top:1rem;background:rgba(239,68,68,.07);border:1px solid rgba(239,68,68,.32);'+
    'border-radius:14px;padding:1.1rem;animation:slideUp .45s">'+
    '<div style="font-weight:700;color:#f87171;margin-bottom:.5rem;font-size:.92rem">&#10007; '+
      String(err.title).replace(/</g,'&lt;')+'</div>'+
    (err.detail?('<div style="font-size:.71rem;color:#94a3b8;direction:ltr;text-align:left;background:#05060c;'+
      'border-radius:8px;padding:.6rem;margin-bottom:.8rem;max-height:110px;overflow:auto;'+
      'font-family:\'JetBrains Mono\',monospace;white-space:pre-wrap">'+String(err.detail).replace(/</g,'&lt;')+'</div>'):'')+
    '<div style="font-weight:700;color:#fbbf24;margin:.5rem 0 .2rem;font-size:.85rem">&#128161; '+t('fix-title')+'</div>'+
    sols+
    '<div style="font-size:.73rem;color:var(--mut);margin-top:.7rem">'+t('skip-note')+'</div>'+
    '<div class="row" style="margin-top:.9rem">'+
      '<button class="btn pri" onclick="resumeInstall()">'+t('resume')+'</button>'+
      extra+
      '<button class="btn ghost" onclick="cleanInstall()">'+t('clean')+'</button>'+
    '</div></div>';
}

var es=null;
function beginStream(){
  if(es){es.close();es=null}
  es=new EventSource('/api/logs/stream');
  es.onmessage=function(ev){
    var d=JSON.parse(ev.data);
    if(d.steps)renderSteps(d.steps);
    if(typeof d.progress==='number'){
      document.getElementById('pbar').style.width=d.progress+'%';
      document.getElementById('pct').textContent=d.progress+'%';
    }
    if(d.steps){
      var run=d.steps.filter(function(s){return s.status==='running'})[0];
      if(run)document.getElementById('cur-step').textContent=(lang==='fa'&&STEP_LABELS_FA[run.key])?STEP_LABELS_FA[run.key]:run.title;
    }
    if(d.msg==='__DONE__'){
      es.close(); es=null;
      if(d.error){ showError(d.error); }
      else{ finish(); }
      return;
    }
    if(d.msg!=='')addLine(d.msg);
  };
  es.onerror=function(){ if(es){es.close();es=null;setTimeout(beginStream,1500)} };
}

function finish(){
  fetch('/api/state').then(function(r){return r.json()}).then(function(s){
    var url=s.panel_url||('http://'+(cfg.domain||'localhost'));
    var secure=url.indexOf('https')===0;
    window._panel=url;
    document.getElementById('final').innerHTML=
      '<tr><td>'+t('panel-url')+'</td><td><a href="'+url+'" target="_blank" style="color:#818cf8">'+url+'</a></td></tr>'+
      '<tr><td>'+t('panel-pass2')+'</td><td style="font-family:monospace">'+(s.panel_password||'')+'</td></tr>'+
      '<tr><td>'+t('rv-bot')+'</td><td>'+(cfg.bot_username?('@'+cfg.bot_username):'-')+'</td></tr>'+
      '<tr><td>'+t('ssl-state')+'</td><td>'+(secure?'<span class="badge b-g">'+t('ssl-on')+'</span>':'<span class="badge b-y">'+t('ssl-off')+'</span>')+'</td></tr>';
    go(8);
  });
}
function openPanel(){ window.open(window._panel||'/','_blank') }

// ---------- boot ----------
fetch('/api/server-info').then(function(r){return r.json()}).then(function(d){
  if(d.resume_available){
    document.getElementById('resume-box').innerHTML=
      '<div style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.32);border-radius:12px;'+
      'padding:.9rem;margin-bottom:1rem;font-size:.82rem;animation:slideUp .5s">'+
      '<div style="color:#fbbf24;font-weight:600;margin-bottom:.6rem">&#9888; '+t('resume-found')+'</div>'+
      '<button class="btn sec" style="width:100%" onclick="resumeInstall()">'+t('resume-btn')+'</button></div>';
  }
}).catch(function(){});
setLang('fa');
renderStepper();
</script>
</body>
</html>
"""


def main():
    if os.geteuid() != 0:
        print("[error] The wizard must run as root. Start it with: sudo bash install.sh")
        sys.exit(1)
    _load_state()
    if _state["completed"]:
        print("[install] Previous run detected. Completed steps: " + ", ".join(_state["completed"]))
        print("[install] The wizard will resume from the first unfinished step.")
    srv = http.server.ThreadingHTTPServer(("0.0.0.0", WIZARD_PORT), WizardHandler)
    print("[install] Wizard listening on http://" + get_server_ip() + ":" + str(WIZARD_PORT))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[install] Wizard stopped by user.")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
