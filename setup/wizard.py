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
    ("admin", "Create admin account", 3),
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
    admin_id = str(cfg.get("admin_id", "")).strip()
    lines = [
        "# Telegram Bot",
        _env_line("BOT_TOKEN", cfg.get("bot_token", "")),
        "",
        "# Admin",
        # config.py reads ADMIN_IDS from the environment. Writing it here is the
        # only thing that actually takes effect; patching config.py does not.
        _env_line("ADMIN_IDS", admin_id),
        "",
        "# Admin Panel",
        _env_line("PANEL_PASSWORD", cfg.get("panel_password", "")),
        _env_line("JWT_SECRET", jwt),
        "PANEL_PORT=8000",
        "PANEL_TRUST_PROXY=1",
        "PANEL_CORS_ORIGINS=https://" + domain + ",http://" + domain,
        "",
        "# Payment APIs (optional)",
        _env_line("BSCSCAN_API_KEY", cfg.get("bscscan_key", "")),
        _env_line("USD_RATE_API_KEY", cfg.get("navasan_key", "")),
        _env_line("ZARINPAL_MERCHANT_ID", cfg.get("zarinpal_id", "")),
    ]
    env_file.write_text("\n".join(lines) + "\n")
    os.chmod(env_file, 0o600)
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


SEED_ADMIN_SCRIPT = """
import os, sys
sys.path.insert(0, {install!r})
os.chdir({install!r})

for line in open({envfile!r}, encoding="utf-8"):
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    os.environ.setdefault(k.strip(), v.strip().strip('\"'))

import bcrypt
import database as db

uid = int(sys.argv[1])
raw = sys.argv[2].encode("utf-8")[:72]
pw_hash = bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode()

db.init_db()
db.ensure_schema()

with db.get_db() as c:
    c.execute(
        "INSERT OR IGNORE INTO admins (user_id, is_super, permissions) VALUES (?,1,'all')",
        (uid,))
    c.execute(
        "UPDATE admins SET is_super=1, permissions='all',"
        " panel_username=COALESCE(NULLIF(panel_username,''),'admin'),"
        " panel_password_hash=? WHERE user_id=?",
        (pw_hash, uid))

print("admin-ready")
"""


def step_admin(cfg):
    """Write the panel admin row before the services come up.

    Doing this here (rather than lazily on first login) is what makes the
    password chosen in the wizard actually work.
    """
    admin_id = str(cfg.get("admin_id", "")).strip()
    password = cfg.get("panel_password") or ""
    if not admin_id or not password:
        raise InstallError(
            "Admin account details are missing",
            "The wizard did not receive a Telegram ID or a panel password.",
            ["Go back to the Admin Account step and fill both fields."],
        )

    script = INSTALL_DIR / "_seed_admin.py"
    try:
        script.write_text(
            SEED_ADMIN_SCRIPT.format(
                install=str(INSTALL_DIR),
                envfile=str(INSTALL_DIR / ".env"),
            ),
            encoding="utf-8",
        )
        out = _run(
            [str(INSTALL_DIR / "venv" / "bin" / "python"), str(script),
             admin_id, password],
            shell=False, timeout=180,
        )
        if "admin-ready" not in (out or ""):
            raise InstallError(
                "Could not create the admin account",
                (out or "")[-800:],
                ["Check that the database file is writable by the shopbot user.",
                 "Retry this step from the installer."],
            )
        _log("Admin account ready (username: admin)")
    finally:
        try:
            script.unlink()
        except Exception:
            pass


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
    "admin": step_admin,
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
                # /api/state needs no auth, so strip every secret.
                snap = {k: v for k, v in _state.items()
                        if k not in ("config", "panel_password")}
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
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>ShopBot Setup</title>
<style>
:root{
  --bg:#0E1021; --card:#171929; --card-2:#1C1F33;
  --primary:#7C5CFF; --primary-hover:#8D70FF; --accent:#5B8DEF;
  --primary-10:rgba(124,92,255,.10); --primary-15:rgba(124,92,255,.15);
  --primary-25:rgba(124,92,255,.25); --primary-35:rgba(124,92,255,.35);
  --primary-60:rgba(124,92,255,.60);
  --text:#FFFFFF; --text-dim:#A7A8BE;
  --ok:#33D17A; --err:#FF5A70; --warn:#F5A623;
  --border:rgba(255,255,255,.10); --radius:16px;
}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{
  background:var(--bg); color:var(--text);
  font-family:Vazirmatn,IRANSans,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  min-height:100%; display:flex; align-items:center; justify-content:center;
  padding:28px 16px; position:relative; overflow-x:hidden;
}
body::before{
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:linear-gradient(rgba(255,255,255,.045) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px);
  background-size:44px 44px;
  -webkit-mask-image:radial-gradient(ellipse at center,black 30%,transparent 75%);
  mask-image:radial-gradient(ellipse at center,black 30%,transparent 75%);
}
body::after{
  content:''; position:fixed; top:50%; left:50%; width:620px; height:620px;
  transform:translate(-50%,-50%); pointer-events:none; z-index:0;
  background:radial-gradient(circle,rgba(124,92,255,.18) 0%,transparent 70%);
  filter:blur(40px);
}
.wrap{position:relative;z-index:1;width:100%;max-width:520px}
.brand{display:flex;flex-direction:column;align-items:center;gap:14px;margin-bottom:22px;text-align:center}
.logo{
  width:60px;height:60px;border-radius:18px;display:grid;place-items:center;
  background:linear-gradient(135deg,var(--primary),var(--accent));
  box-shadow:0 8px 26px var(--primary-35);
}
.logo svg{width:32px;height:32px;stroke:#fff;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.brand h1{font-size:21px;font-weight:700;letter-spacing:.2px}
.brand p{font-size:13.5px;color:var(--text-dim);line-height:1.7}
.card{
  background:var(--card); border:1px solid var(--border); border-radius:var(--radius);
  padding:28px 26px; box-shadow:0 22px 60px rgba(0,0,0,.45);
}
.stepper{display:flex;align-items:center;gap:8px;margin-bottom:8px}
.dot{height:5px;flex:1;border-radius:99px;background:rgba(255,255,255,.09);transition:background .35s,box-shadow .35s}
.dot.on{background:linear-gradient(90deg,var(--primary),var(--accent));box-shadow:0 0 12px var(--primary-35)}
.dot.done{background:var(--primary-60)}
.smeta{display:flex;justify-content:space-between;font-size:12px;color:var(--text-dim);margin-bottom:22px}
.smeta b{color:var(--text);font-weight:600}
.pane{display:none}
.pane.on{display:block;animation:slideUp .38s cubic-bezier(.22,.9,.3,1) both}
@keyframes slideUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.ptitle{font-size:17px;font-weight:700;margin-bottom:6px}
.psub{font-size:13px;color:var(--text-dim);line-height:1.8;margin-bottom:20px}
.form-label{display:block;font-size:12px;font-weight:600;color:var(--text-dim);margin:0 0 7px 2px;letter-spacing:.3px}
.field{position:relative;margin-bottom:16px}
.input{
  width:100%; padding:13px 15px; font:inherit; font-size:14px; color:var(--text);
  background:rgba(255,255,255,.06); border:1px solid var(--border);
  border-radius:11px; outline:none; transition:border-color .2s,box-shadow .2s;
}
.input::placeholder{color:#6E7089}
.input:focus{border-color:var(--primary-60);box-shadow:0 0 0 3px var(--primary-15)}
.input.pw{padding-inline-end:44px}
.input:disabled{opacity:.55}
.eye{
  position:absolute; inset-inline-end:12px; top:50%; transform:translateY(-50%);
  background:none;border:none;cursor:pointer;color:var(--text-dim);
  display:grid;place-items:center;padding:4px;
}
.eye:hover{color:var(--text)}
.eye svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.8}
.btn{
  width:100%; padding:13px 18px; font:inherit; font-size:14.5px; font-weight:600;
  border:none; border-radius:11px; cursor:pointer; color:#fff;
  display:flex; align-items:center; justify-content:center; gap:9px;
  transition:transform .15s,box-shadow .2s,opacity .2s;
}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn-primary{background:linear-gradient(135deg,var(--primary),var(--accent));box-shadow:0 4px 15px var(--primary-35)}
.btn-primary:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 7px 22px var(--primary-35)}
.btn-secondary{background:rgba(255,255,255,.07);border:1px solid var(--border)}
.btn-secondary:hover:not(:disabled){background:rgba(255,255,255,.11)}
.btn-ghost{background:none;color:var(--text-dim);font-size:13px;font-weight:500;padding:10px}
.btn-ghost:hover{color:var(--primary-hover)}
.row{display:flex;gap:10px;margin-top:6px}
.row .btn{flex:1}
.alert{
  display:flex; gap:10px; align-items:flex-start; padding:12px 14px; border-radius:11px;
  font-size:12.8px; line-height:1.75; margin-bottom:16px; animation:slideUp .25s both;
}
.alert svg{width:17px;height:17px;flex:0 0 17px;margin-top:2px;stroke:currentColor;fill:none;stroke-width:1.9}
.alert.err{background:rgba(255,90,112,.11);border:1px solid rgba(255,90,112,.30);color:#FFB3BD}
.alert.ok{background:rgba(51,209,122,.11);border:1px solid rgba(51,209,122,.30);color:#8FE9B8}
.alert.warn{background:rgba(245,166,35,.11);border:1px solid rgba(245,166,35,.30);color:#F7CE8C}
.alert.info{background:var(--primary-10);border:1px solid var(--primary-25);color:#C3B4FF}
.hint{font-size:11.8px;color:var(--text-dim);line-height:1.8;margin-top:-8px;margin-bottom:16px}
.hint a{color:var(--primary-hover);text-decoration:none}
.hint a:hover{text-decoration:underline}
.spin{width:16px;height:16px;border:2px solid rgba(255,255,255,.28);border-top-color:#fff;border-radius:50%;animation:sp .7s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
.bar{height:7px;border-radius:99px;background:rgba(255,255,255,.08);overflow:hidden;margin-bottom:9px}
.bar i{display:block;height:100%;width:0;border-radius:99px;background:linear-gradient(90deg,var(--primary),var(--accent));box-shadow:0 0 14px var(--primary-35);transition:width .5s cubic-bezier(.3,.9,.4,1)}
.barmeta{display:flex;justify-content:space-between;font-size:12px;color:var(--text-dim);margin-bottom:18px}
.tasks{list-style:none;display:flex;flex-direction:column;gap:2px;margin-bottom:16px}
.tasks li{display:flex;align-items:center;gap:10px;font-size:13px;padding:7px 2px;color:var(--text-dim);transition:color .3s}
.tasks li.run{color:var(--text)}
.tasks li.done{color:#8FE9B8}
.tasks li.fail{color:#FFB3BD}
.tico{width:17px;height:17px;flex:0 0 17px;display:grid;place-items:center}
.tico svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}
.tico .pend{width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,.20)}
.term{
  display:none; background:#0A0C18; border:1px solid var(--border); border-radius:11px;
  padding:12px 14px; max-height:190px; overflow-y:auto; margin-bottom:14px;
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; font-size:11.5px;
  line-height:1.85; direction:ltr; text-align:left; color:#9AA0B4;
}
.term.on{display:block}
.term div{white-space:pre-wrap;word-break:break-word}
.term .l-ok{color:#8FE9B8}
.term .l-err{color:#FFB3BD}
.term .l-warn{color:#F7CE8C}
.term::-webkit-scrollbar{width:6px}
.term::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:99px}
.kv{display:flex;flex-direction:column;gap:9px;margin-bottom:20px}
.kv .r{
  display:flex;align-items:center;gap:10px;background:var(--card-2);
  border:1px solid var(--border);border-radius:11px;padding:11px 13px;
}
.kv .k{font-size:11.5px;color:var(--text-dim);flex:0 0 82px;font-weight:600}
.kv .v{flex:1;font-size:13px;word-break:break-all;direction:ltr;text-align:left;font-family:ui-monospace,Menlo,Consolas,monospace}
.cp{background:none;border:none;cursor:pointer;color:var(--text-dim);padding:4px;display:grid;place-items:center;border-radius:6px}
.cp:hover{color:var(--primary-hover);background:var(--primary-10)}
.cp svg{width:15px;height:15px;stroke:currentColor;fill:none;stroke-width:1.8}
.pop{width:66px;height:66px;border-radius:50%;display:grid;place-items:center;margin:0 auto 18px;
  background:rgba(51,209,122,.13);border:1px solid rgba(51,209,122,.35);animation:pop .5s cubic-bezier(.2,1.5,.4,1) both}
@keyframes pop{from{opacity:0;transform:scale(.5)}to{opacity:1;transform:scale(1)}}
.pop svg{width:32px;height:32px;stroke:var(--ok);fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
.lang{
  position:fixed;top:18px;inset-inline-end:18px;z-index:5;
  background:rgba(255,255,255,.07);border:1px solid var(--border);color:var(--text-dim);
  border-radius:9px;padding:7px 13px;font:inherit;font-size:12px;font-weight:600;cursor:pointer;
  display:flex;align-items:center;gap:6px;
}
.lang:hover{color:var(--text);border-color:var(--primary-60)}
.lang svg{width:14px;height:14px;stroke:currentColor;fill:none;stroke-width:1.8}
.foot{text-align:center;font-size:11.5px;color:#5E6178;margin-top:20px;line-height:1.9}
.foot code{background:rgba(255,255,255,.07);padding:2px 7px;border-radius:5px;font-size:11px;color:var(--text-dim)}
@media(max-width:520px){.card{padding:22px 18px}.brand h1{font-size:19px}}
</style>
</head>
<body>

<button class="lang" id="langBtn">
  <svg viewBox="0 0 24 24"><path d="M5 8h14M9 5v3M11 17l4-9 4 9M12.5 14h5.5"/><path d="M5 8c0 4 3 7 7 8"/></svg>
  <span id="langTxt">EN</span>
</button>

<div class="wrap">

  <div class="brand">
    <div class="logo">
      <svg viewBox="0 0 24 24"><rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V5M9 14h.01M15 14h.01M2 13v3M22 13v3"/><circle cx="12" cy="4" r="1.4"/></svg>
    </div>
    <div>
      <h1 id="bTitle">نصب ShopBot</h1>
      <p id="bSub">ربات فروشگاهی تلگرام و پنل مدیریت</p>
    </div>
  </div>

  <div class="card">
    <div class="stepper" id="stepper"></div>
    <div class="smeta">
      <span id="stepNow"></span>
      <b id="stepName"></b>
    </div>

    <div id="alertBox"></div>

    <!-- 0 welcome -->
    <div class="pane on" data-p="0">
      <div class="ptitle" id="t0"></div>
      <div class="psub" id="s0"></div>
      <div id="resumeBox"></div>
      <button class="btn btn-primary" id="b0"></button>
    </div>

    <!-- 1 domain -->
    <div class="pane" data-p="1">
      <div class="ptitle" id="t1"></div>
      <div class="psub" id="s1"></div>
      <label class="form-label" id="h1"></label>
      <div class="field"><input class="input" id="domain" dir="ltr" placeholder="bot.example.com" autocomplete="off"></div>
      <div id="emailField" style="display:none">
        <label class="form-label" id="h1b"></label>
        <div class="field"><input class="input" id="email" dir="ltr" type="email" placeholder="you@example.com" autocomplete="off"></div>
      </div>
      <div id="domainMsg"></div>
      <button class="btn btn-primary" id="nextDomain"></button>
      <button class="btn btn-ghost" id="skipDomain"></button>
    </div>

    <!-- 2 telegram -->
    <div class="pane" data-p="2">
      <div class="ptitle" id="t2"></div>
      <div class="psub" id="s2"></div>
      <label class="form-label" id="h2"></label>
      <div class="field"><input class="input" id="token" dir="ltr" placeholder="1234567890:AAE..." autocomplete="off"></div>
      <div class="hint" id="i2"></div>
      <div id="tokenMsg"></div>
      <button class="btn btn-primary" id="nextToken"></button>
    </div>

    <!-- 3 admin -->
    <div class="pane" data-p="3">
      <div class="ptitle" id="t3"></div>
      <div class="psub" id="s3"></div>
      <label class="form-label" id="h3"></label>
      <div class="field"><input class="input" id="adminId" dir="ltr" inputmode="numeric" placeholder="123456789" autocomplete="off"></div>
      <div class="hint" id="i3"></div>
      <label class="form-label" id="h3b"></label>
      <div class="field">
        <input class="input pw" id="pass" type="password" autocomplete="new-password">
        <button class="eye" data-for="pass"><svg viewBox="0 0 24 24"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg></button>
      </div>
      <label class="form-label" id="h3c"></label>
      <div class="field">
        <input class="input pw" id="pass2" type="password" autocomplete="new-password">
        <button class="eye" data-for="pass2"><svg viewBox="0 0 24 24"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg></button>
      </div>
      <div id="adminMsg"></div>
      <button class="btn btn-primary" id="startInstall"></button>
    </div>

    <!-- 4 install -->
    <div class="pane" data-p="4">
      <div class="ptitle" id="t4"></div>
      <div class="psub" id="s4"></div>
      <div class="bar"><i id="barFill"></i></div>
      <div class="barmeta"><span id="barLabel"></span><b id="barPct">0%</b></div>
      <ul class="tasks" id="tasks"></ul>
      <button class="btn btn-ghost" id="toggleLog"></button>
      <div class="term" id="term"></div>
      <div id="installMsg"></div>
      <div id="installActions"></div>
    </div>

    <!-- 5 finish -->
    <div class="pane" data-p="5">
      <div class="pop"><svg viewBox="0 0 24 24"><path d="m4 12.5 5.2 5L20 7"/></svg></div>
      <div class="ptitle" style="text-align:center" id="t5"></div>
      <div class="psub" style="text-align:center" id="s5"></div>
      <div id="w5"></div>
      <div class="kv" id="creds"></div>
      <button class="btn btn-primary" id="goPanel"></button>
      <div class="foot" id="f5"></div>
    </div>
  </div>

  <div class="foot" id="pageFoot"></div>
</div>

<script>
/* ------------------------------------------------------------------ i18n */
var T = {
  fa: {
    bTitle:'نصب ShopBot', bSub:'ربات فروشگاهی تلگرام و پنل مدیریت',
    stepOf:'گام %1 از %2',
    n0:'خوش‌آمد', n1:'دامنه', n2:'تلگرام', n3:'حساب مدیر', n4:'نصب', n5:'پایان',
    t0:'به نصب‌کننده خوش آمدید',
    s0:'در چند گام ساده، ربات و پنل مدیریت روی این سرور نصب می‌شود. فقط کافی است توکن ربات و شناسهٔ تلگرام خود را آماده داشته باشید.',
    b0:'شروع نصب',
    t1:'دامنه و گواهی SSL',
    s1:'اگر دامنه دارید، پنل روی HTTPS امن اجرا می‌شود. اگر ندارید، این گام را رد کنید — بعداً هم می‌توانید دامنه اضافه کنید.',
    h1:'دامنه', h1b:'ایمیل (برای یادآوری تمدید گواهی)',
    nextDomain:'بررسی دامنه و ادامه', skipDomain:'دامنه ندارم، با IP ادامه بده',
    dChecking:'در حال بررسی DNS…',
    dBad:'قالب دامنه درست نیست. مثلاً bot.example.com',
    dOk:'دامنه به این سرور اشاره می‌کند.',
    dMiss:'دامنه به %1 اشاره می‌کند ولی IP این سرور %2 است. می‌توانید ادامه دهید، ولی گواهی SSL صادر نمی‌شود.',
    dGo:'به هر حال ادامه بده',
    t2:'اتصال به تلگرام',
    s2:'توکن رباتی که از BotFather گرفته‌اید را اینجا بچسبانید.',
    h2:'توکن ربات',
    i2:'در تلگرام به <a href="https://t.me/BotFather" target="_blank">BotFather@</a> پیام دهید، newbot/ را بزنید و توکن را کپی کنید.',
    nextToken:'بررسی توکن و ادامه',
    tChecking:'در حال بررسی توکن…',
    tEmpty:'توکن ربات را وارد کنید.',
    tOk:'توکن معتبر است — %1',
    tBad:'توکن پذیرفته نشد. دوباره از BotFather کپی کنید.',
    t3:'حساب مدیر',
    s3:'این حساب برای ورود به پنل مدیریت و بازیابی رمز استفاده می‌شود.',
    h3:'شناسهٔ عددی تلگرام',
    i3:'به <a href="https://t.me/userinfobot" target="_blank">userinfobot@</a> پیام دهید — عددی که می‌دهد همین است.',
    h3b:'رمز عبور پنل', h3c:'تکرار رمز عبور',
    startInstall:'شروع نصب',
    aId:'شناسهٔ عددی تلگرام را وارد کنید (فقط عدد).',
    aLen:'رمز عبور باید حداقل ۸ نویسه باشد.',
    aAscii:'برای رمز عبور فقط از حروف انگلیسی، عدد و علائم استفاده کنید.',
    aMatch:'دو رمز عبور یکسان نیستند.',
    t4:'در حال نصب',
    s4:'این کار بین ۳ تا ۸ دقیقه طول می‌کشد. این صفحه را نبندید.',
    showLog:'نمایش جزئیات فنی', hideLog:'پنهان کردن جزئیات',
    failed:'نصب متوقف شد', retry:'تلاش دوباره',
    t5:'نصب کامل شد',
    s5:'اطلاعات زیر را همین حالا ذخیره کنید — پس از بستن این صفحه دیگر نمایش داده نمی‌شوند.',
    kUrl:'آدرس پنل', kUser:'نام کاربری', kPass:'رمز عبور',
    goPanel:'ورود به پنل مدیریت',
    f5:'برای مدیریت بعدی کافی است در سرور دستور <code>shopbot</code> را بزنید.',
    sslWarn:'گواهی SSL صادر نشد، ولی نصب کامل است. بعداً با دستور shopbot گزینهٔ ۱۱ دوباره تلاش کنید.',
    resume:'یک نصب ناتمام پیدا شد. می‌خواهید ادامه دهید یا از اول شروع کنید؟',
    btnResume:'ادامهٔ نصب', btnFresh:'شروع از اول',
    copied:'کپی شد', netErr:'ارتباط با سرور قطع شد. صفحه را تازه کنید.',
    foot:'نصب‌کنندهٔ ShopBot'
  },
  en: {
    bTitle:'Install ShopBot', bSub:'Telegram shop bot and admin panel',
    stepOf:'Step %1 of %2',
    n0:'Welcome', n1:'Domain', n2:'Telegram', n3:'Admin', n4:'Install', n5:'Finish',
    t0:'Welcome to the installer',
    s0:'This will set up the bot and the admin panel on this server in a few short steps. Have your bot token and your Telegram ID ready.',
    b0:'Start installation',
    t1:'Domain and SSL',
    s1:'With a domain the panel runs over secure HTTPS. Without one, skip this step — you can add a domain later.',
    h1:'Domain', h1b:'Email (for certificate renewal notices)',
    nextDomain:'Check domain and continue', skipDomain:'No domain, continue with the IP',
    dChecking:'Checking DNS…',
    dBad:'That does not look like a domain. For example: bot.example.com',
    dOk:'The domain points to this server.',
    dMiss:'The domain points to %1 but this server is %2. You can continue, but no SSL certificate will be issued.',
    dGo:'Continue anyway',
    t2:'Connect Telegram',
    s2:'Paste the bot token you received from BotFather.',
    h2:'Bot token',
    i2:'Message <a href="https://t.me/BotFather" target="_blank">@BotFather</a> on Telegram, send /newbot and copy the token.',
    nextToken:'Verify token and continue',
    tChecking:'Verifying token…',
    tEmpty:'Enter the bot token.',
    tOk:'Token is valid — %1',
    tBad:'Telegram rejected that token. Copy it again from BotFather.',
    t3:'Admin account',
    s3:'This account signs in to the admin panel and recovers the password.',
    h3:'Telegram numeric ID',
    i3:'Message <a href="https://t.me/userinfobot" target="_blank">@userinfobot</a> — the number it replies with is your ID.',
    h3b:'Panel password', h3c:'Repeat password',
    startInstall:'Start installation',
    aId:'Enter your Telegram numeric ID (digits only).',
    aLen:'The password must be at least 8 characters.',
    aAscii:'Use only Latin letters, digits and symbols for the password.',
    aMatch:'The two passwords do not match.',
    t4:'Installing',
    s4:'This usually takes 3 to 8 minutes. Please keep this page open.',
    showLog:'Show technical details', hideLog:'Hide details',
    failed:'Installation stopped', retry:'Try again',
    t5:'Installation complete',
    s5:'Save these details now — they will not be shown again once you close this page.',
    kUrl:'Panel URL', kUser:'Username', kPass:'Password',
    goPanel:'Go to the admin panel',
    f5:'To manage it later, just run <code>shopbot</code> on the server.',
    sslWarn:'The SSL certificate could not be issued, but the install finished. Run shopbot and pick option 11 to retry.',
    resume:'An unfinished installation was found. Resume it or start over?',
    btnResume:'Resume install', btnFresh:'Start over',
    copied:'Copied', netErr:'Lost connection to the server. Please refresh the page.',
    foot:'ShopBot installer'
  }
};

var lang = 'fa';
function L(k){ return T[lang][k] || k; }
function fmt(s){
  var a = arguments;
  return String(s).replace(/%(\d)/g, function(m, i){ return a[+i] == null ? m : a[+i]; });
}
var FA_D = ['۰','۱','۲','۳','۴','۵','۶','۷','۸','۹'];
function num(n){
  if (lang !== 'fa') return String(n);
  return String(n).replace(/\d/g, function(d){ return FA_D[+d]; });
}

/* ------------------------------------------------------------------ utils */
function $(id){ return document.getElementById(id); }
function esc(s){
  return String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}
var ICON = {
  err:  '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01"/></svg>',
  ok:   '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m8.5 12.5 2.5 2.5 4.5-5"/></svg>',
  warn: '<svg viewBox="0 0 24 24"><path d="M10.3 3.9 2.4 17.1A1.9 1.9 0 0 0 4 20h16a1.9 1.9 0 0 0 1.6-2.9L13.7 3.9a1.9 1.9 0 0 0-3.4 0Z"/><path d="M12 9v4M12 16h.01"/></svg>',
  info: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/></svg>'
};
function alertHTML(kind, msg){
  return '<div class="alert ' + kind + '">' + ICON[kind] + '<div>' + msg + '</div></div>';
}
function setMsg(id, kind, msg){
  $(id).innerHTML = msg ? alertHTML(kind, msg) : '';
}
function post(url, data){
  return fetch(url, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(data || {})
  }).then(function(r){ return r.json(); });
}
function get(url){ return fetch(url).then(function(r){ return r.json(); }); }

/* ------------------------------------------------------------------ state */
var TOTAL = 6;
var NAMES = ['n0','n1','n2','n3','n4','n5'];
var cur = 0, serverIp = '', botName = '', installing = false, finished = false;

function buildStepper(){
  var h = '';
  for (var i = 0; i < TOTAL; i++) h += '<div class="dot" data-d="' + i + '"></div>';
  $('stepper').innerHTML = h;
}
function paintStepper(){
  var dots = document.querySelectorAll('.dot');
  for (var i = 0; i < dots.length; i++){
    dots[i].className = 'dot' + (i < cur ? ' done' : (i === cur ? ' on' : ''));
  }
  $('stepNow').textContent = fmt(L('stepOf'), num(cur + 1), num(TOTAL));
  $('stepName').textContent = L(NAMES[cur]);
}
function go(n){
  cur = n;
  var panes = document.querySelectorAll('.pane');
  for (var i = 0; i < panes.length; i++){
    panes[i].classList.toggle('on', +panes[i].dataset.p === n);
  }
  paintStepper();
  $('alertBox').innerHTML = '';
  window.scrollTo(0, 0);
}

function applyLang(){
  document.documentElement.lang = lang;
  document.documentElement.dir = (lang === 'fa') ? 'rtl' : 'ltr';
  $('langTxt').textContent = (lang === 'fa') ? 'EN' : 'FA';
  var keys = ['bTitle','bSub','t0','s0','b0','t1','s1','h1','h1b','nextDomain','skipDomain',
              't2','s2','h2','i2','nextToken','t3','s3','h3','i3','h3b','h3c','startInstall',
              't4','s4','t5','s5','goPanel','f5'];
  for (var i = 0; i < keys.length; i++){
    var el = $(keys[i]);
    if (el) el.innerHTML = L(keys[i]);
  }
  $('toggleLog').textContent = $('term').classList.contains('on') ? L('hideLog') : L('showLog');
  $('pageFoot').textContent = L('foot');
  paintStepper();
  renderResume();
}

$('langBtn').onclick = function(){
  lang = (lang === 'fa') ? 'en' : 'fa';
  applyLang();
};

/* eye toggles */
var eyes = document.querySelectorAll('.eye');
for (var e = 0; e < eyes.length; e++){
  eyes[e].onclick = function(){
    var f = $(this.dataset.for);
    f.type = (f.type === 'password') ? 'text' : 'password';
  };
}

/* ------------------------------------------------------------- 0 welcome */
var resumeAvailable = false;
function renderResume(){
  if (!resumeAvailable){ $('resumeBox').innerHTML = ''; return; }
  $('resumeBox').innerHTML =
    alertHTML('info', L('resume')) +
    '<div class="row" style="margin-bottom:14px">' +
      '<button class="btn btn-primary" id="btnResume">' + L('btnResume') + '</button>' +
      '<button class="btn btn-secondary" id="btnFresh">' + L('btnFresh') + '</button>' +
    '</div>';
  $('btnResume').onclick = function(){ beginInstall('/api/resume', {}); };
  $('btnFresh').onclick = function(){
    resumeAvailable = false;
    renderResume();
  };
}
$('b0').onclick = function(){ go(1); };

/* -------------------------------------------------------------- 1 domain */
function validDomain(d){
  return /^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/i.test(d);
}
$('domain').addEventListener('input', function(){
  $('emailField').style.display = this.value.trim() ? 'block' : 'none';
});
$('skipDomain').onclick = function(){
  $('domain').value = '';
  $('email').value = '';
  setMsg('domainMsg', 'info', '');
  go(2);
};
$('nextDomain').onclick = function(){
  var d = $('domain').value.trim().toLowerCase().replace(/^https?:\/\//, '').replace(/\/.*$/, '');
  if (!d){ go(2); return; }
  if (!validDomain(d)){ setMsg('domainMsg', 'err', L('dBad')); return; }
  $('domain').value = d;
  var btn = this;
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span>' + L('dChecking');
  post('/api/check-domain', { domain: d }).then(function(r){
    btn.disabled = false;
    btn.textContent = L('nextDomain');
    if (r.ok){
      setMsg('domainMsg', 'ok', L('dOk'));
      setTimeout(function(){ go(2); }, 650);
    } else {
      $('domainMsg').innerHTML =
        alertHTML('warn', fmt(L('dMiss'), esc(r.resolved || '?'), esc(r.server_ip || serverIp))) +
        '<button class="btn btn-secondary" id="dGo" style="margin-bottom:14px">' + L('dGo') + '</button>';
      $('dGo').onclick = function(){ go(2); };
    }
  })['catch'](function(){
    btn.disabled = false;
    btn.textContent = L('nextDomain');
    setMsg('domainMsg', 'err', L('netErr'));
  });
};

/* ------------------------------------------------------------ 2 telegram */
$('nextToken').onclick = function(){
  var tok = $('token').value.trim();
  if (!tok){ setMsg('tokenMsg', 'err', L('tEmpty')); return; }
  var btn = this;
  btn.disabled = true;
  btn.innerHTML = '<span class="spin"></span>' + L('tChecking');
  post('/api/validate-token', { token: tok }).then(function(r){
    btn.disabled = false;
    btn.textContent = L('nextToken');
    if (r.ok){
      botName = r.info || '';
      setMsg('tokenMsg', 'ok', fmt(L('tOk'), esc(botName)));
      setTimeout(function(){ go(3); }, 650);
    } else {
      setMsg('tokenMsg', 'err', esc(r.info || L('tBad')));
    }
  })['catch'](function(){
    btn.disabled = false;
    btn.textContent = L('nextToken');
    setMsg('tokenMsg', 'err', L('netErr'));
  });
};

/* --------------------------------------------------------------- 3 admin */
$('startInstall').onclick = function(){
  var id = $('adminId').value.trim();
  var p1 = $('pass').value;
  var p2 = $('pass2').value;

  if (!/^\d{5,}$/.test(id)){ setMsg('adminMsg', 'err', L('aId')); return; }
  if (p1.length < 8){ setMsg('adminMsg', 'err', L('aLen')); return; }
  // The panel compares this password with secrets.compare_digest, which only
  // accepts ASCII. A Persian password would make every login fail with a 500.
  if (!/^[\x21-\x7E]+$/.test(p1)){ setMsg('adminMsg', 'err', L('aAscii')); return; }
  if (p1 !== p2){ setMsg('adminMsg', 'err', L('aMatch')); return; }

  setMsg('adminMsg', 'info', '');
  beginInstall('/api/install', {
    lang: lang,
    domain: $('domain').value.trim(),
    email: $('email').value.trim(),
    bot_token: $('token').value.trim(),
    admin_id: id,
    panel_password: p1
  });
};

/* ------------------------------------------------------------- 4 install */
var TASK_ICON = {
  pending: '<span class="pend"></span>',
  running: '<span class="spin" style="width:14px;height:14px"></span>',
  done:    '<svg viewBox="0 0 24 24"><path d="m5 12.5 4.5 4.5L19 7"/></svg>',
  failed:  '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  skipped: '<svg viewBox="0 0 24 24"><path d="M5 12h14"/></svg>'
};
var CLS = { running:'run', done:'done', failed:'fail', skipped:'done' };

function paintTasks(steps){
  if (!steps || !steps.length) return;
  var h = '';
  for (var i = 0; i < steps.length; i++){
    var s = steps[i];
    var st = s.status || 'pending';
    h += '<li class="' + (CLS[st] || '') + '">' +
           '<span class="tico">' + (TASK_ICON[st] || TASK_ICON.pending) + '</span>' +
           '<span>' + esc(s.title || s.key) + '</span>' +
         '</li>';
    if (st === 'running') $('barLabel').textContent = s.title || s.key;
  }
  $('tasks').innerHTML = h;
}
function setProgress(p){
  p = Math.max(0, Math.min(100, Math.round(p || 0)));
  $('barFill').style.width = p + '%';
  $('barPct').textContent = num(p) + '%';
}
function logLine(msg){
  var cls = '';
  var low = String(msg).toLowerCase();
  if (/error|failed|fatal|traceback/.test(low)) cls = 'l-err';
  else if (/warn/.test(low)) cls = 'l-warn';
  else if (/^ok|done|success|\u2713/.test(low)) cls = 'l-ok';
  var d = document.createElement('div');
  if (cls) d.className = cls;
  d.textContent = msg;
  var t = $('term');
  t.appendChild(d);
  t.scrollTop = t.scrollHeight;
}
$('toggleLog').onclick = function(){
  var on = $('term').classList.toggle('on');
  this.textContent = on ? L('hideLog') : L('showLog');
};

function beginInstall(url, payload){
  installing = true;
  $('installActions').innerHTML = '';
  setMsg('installMsg', 'info', '');
  go(4);
  post(url, payload).then(function(){ streamLogs(); })['catch'](function(){
    setMsg('installMsg', 'err', L('netErr'));
  });
}

function streamLogs(){
  var es = new EventSource('/api/logs/stream');
  es.onmessage = function(ev){
    var d;
    try { d = JSON.parse(ev.data); } catch (x){ return; }
    if (d.msg === '__DONE__'){
      es.close();
      installing = false;
      setProgress(d.progress);
      paintTasks(d.steps);
      if (d.error) onFailed(d.error); else onDone();
      return;
    }
    logLine(d.msg);
    setProgress(d.progress);
    paintTasks(d.steps);
  };
  es.onerror = function(){
    es.close();
    if (installing) setTimeout(streamLogs, 1500);
  };
}

function onFailed(err){
  var detail = (typeof err === 'string') ? err : (err && err.detail) || '';
  var title  = (err && err.title) || L('failed');
  var sols   = (err && err.solutions) || [];
  var h = '<b>' + esc(title) + '</b>';
  if (detail) h += '<br>' + esc(detail);
  if (sols.length){
    h += '<br><br>';
    for (var i = 0; i < sols.length; i++) h += '• ' + esc(sols[i]) + '<br>';
  }
  $('installMsg').innerHTML = alertHTML('err', h);
  $('term').classList.add('on');
  $('toggleLog').textContent = L('hideLog');
  $('installActions').innerHTML =
    '<button class="btn btn-primary" id="btnRetry">' + L('retry') + '</button>';
  $('btnRetry').onclick = function(){
    $('installMsg').innerHTML = '';
    $('installActions').innerHTML = '';
    beginInstall('/api/resume', {});
  };
}

function onDone(){
  finished = true;
  get('/api/state').then(function(st){ showFinish(st); })['catch'](function(){ showFinish({}); });
}

function copyBtn(val){
  return '<button class="cp" data-c="' + esc(val) + '">' +
         '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="11" height="11" rx="2"/>' +
         '<path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg></button>';
}

function showFinish(st){
  var url = st.panel_url || ('http://' + (serverIp || location.hostname));
  var pass = $('pass').value || '';
  var warns = st.warnings || [];
  var sslFailed = false;
  for (var i = 0; i < warns.length; i++){
    if (/ssl|certbot|certificate/i.test(String(warns[i]))) sslFailed = true;
  }
  $('w5').innerHTML = sslFailed ? alertHTML('warn', L('sslWarn')) : '';

  var rows = [['kUrl', url], ['kUser', 'admin'], ['kPass', pass]];
  var h = '';
  for (var j = 0; j < rows.length; j++){
    if (!rows[j][1]) continue;
    h += '<div class="r"><span class="k">' + L(rows[j][0]) + '</span>' +
         '<span class="v">' + esc(rows[j][1]) + '</span>' + copyBtn(rows[j][1]) + '</div>';
  }
  $('creds').innerHTML = h;

  var cps = document.querySelectorAll('.cp');
  for (var k = 0; k < cps.length; k++){
    cps[k].onclick = function(){
      var self = this;
      var txt = self.dataset.c;
      var done = function(){
        self.style.color = 'var(--ok)';
        setTimeout(function(){ self.style.color = ''; }, 1200);
      };
      if (navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(txt).then(done, function(){});
      } else {
        var ta = document.createElement('textarea');
        ta.value = txt; document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); done(); } catch (x){}
        document.body.removeChild(ta);
      }
    };
  }

  $('goPanel').onclick = function(){
    window.open(url.replace(/\/$/, '') + '/login', '_blank');
  };
  go(5);
}

/* ----------------------------------------------------------------- boot */
buildStepper();
applyLang();

get('/api/server-info').then(function(r){
  serverIp = r.ip || '';
  resumeAvailable = !!r.resume_available;
  renderResume();
})['catch'](function(){});

/* Rejoin an install that is already running (e.g. the page was reloaded). */
get('/api/state').then(function(st){
  if (st && st.running){
    installing = true;
    go(4);
    setProgress(st.progress);
    paintTasks(st.steps);
    streamLogs();
  } else if (st && st.done && !st.error){
    showFinish(st);
  }
})['catch'](function(){});
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
