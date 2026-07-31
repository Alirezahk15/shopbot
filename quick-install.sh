#!/bin/bash
# =============================================================
#  ShopBot — Quick Installer
#  فقط یک دستور روی سرور اجرا کنید:
#  bash <(curl -fsSL https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/quick-install.sh)
# =============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

[[ $EUID -ne 0 ]] && echo -e "${RED}با root اجرا کنید: sudo bash <(...)${NC}" && exit 1

REPO_URL="https://github.com/Alirezahk15/shopbot.git"
TMP_DIR="/tmp/shopbot-install"
PORT=8080

echo -e "${GREEN}${BOLD}"
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║        🤖  ShopBot — Quick Install               ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. نصب git و python3
if ! command -v git &>/dev/null || ! command -v python3 &>/dev/null; then
    echo -e "${CYAN}  نصب git و python3...${NC}"
    apt-get update -qq
    apt-get install -y -qq git python3
fi

# 2. clone پروژه
echo -e "${CYAN}  دانلود ShopBot...${NC}"
rm -rf "$TMP_DIR"
git clone --depth=1 "$REPO_URL" "$TMP_DIR" 2>/dev/null \
    || { echo -e "${RED}  خطا: clone ناموفق. آدرس REPO_URL را بررسی کنید.${NC}"; exit 1; }

# 3. دریافت IP سرور
SERVER_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "127.0.0.1")

echo ""
echo -e "  ${CYAN}Wizard آماده است. در مرورگر باز کنید:${NC}"
echo ""
echo -e "  ${BOLD}  ➜  http://${SERVER_IP}:${PORT}${NC}"
echo ""
echo "  ───────────────────────────────────────────────────"
echo "  برای توقف:  Ctrl + C"
echo ""

# 4. اجرای wizard
exec python3 "$TMP_DIR/setup/wizard.py"