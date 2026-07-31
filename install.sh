#!/bin/bash
# =============================================================================
#  ShopBot — Web Setup Wizard Launcher
#  فقط Python3 نصب می‌کند و Wizard را روی پورت 8080 اجرا می‌کند
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

[[ $EUID -ne 0 ]] && echo -e "${RED}خطا: با دسترسی root اجرا کنید:  sudo bash install.sh${NC}" && exit 1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIZARD="$SCRIPT_DIR/setup/wizard.py"
PORT=8080

[[ ! -f "$WIZARD" ]] && echo -e "${RED}خطا: فایل setup/wizard.py یافت نشد${NC}" && exit 1

# ── نصب Python3 اگر موجود نیست ──────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${CYAN}  نصب Python3...${NC}"
    apt-get update -qq
    apt-get install -y -qq python3
fi

# ── دریافت IP سرور ───────────────────────────────────────────────────────────
SERVER_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "127.0.0.1")

# ── پیام راهنما ──────────────────────────────────────────────────────────────
clear
echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║        🤖  ShopBot Setup Wizard                  ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  ${CYAN}برای شروع نصب، این آدرس را در مرورگر باز کنید:${NC}"
echo ""
echo -e "  ${BOLD}  ➜  http://${SERVER_IP}:${PORT}${NC}"
echo ""
echo -e "  ─────────────────────────────────────────────────"
echo -e "  برای توقف wizard:  Ctrl + C"
echo ""

# ── اجرای Wizard ─────────────────────────────────────────────────────────────
exec python3 "$WIZARD"
