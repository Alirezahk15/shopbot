#!/bin/bash
# =============================================================================
#  ShopBot -- Installer
#
#  روش 1 -- نصب مستقیم از اینترنت (یک دستور):
#    sudo bash <(curl -fsSL https://raw.githubusercontent.com/Alirezahk15/shopbot/main/install.sh)
#
#  روش 2 -- اجرا از روی پروژه دانلود شده:
#    sudo bash install.sh
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

[[ $EUID -ne 0 ]] && echo -e "${RED}خطا: با دسترسی root اجرا کنید.${NC}" && exit 1

REPO_URL="https://github.com/Alirezahk15/shopbot.git"
TMP_DIR="/tmp/shopbot-src"
PORT=8080

# هدر
clear
echo -e "${GREEN}${BOLD}"
echo "  ============================================================"
echo "  |          ShopBot -- Setup Wizard                        |"
echo "  ============================================================"
echo -e "${NC}"

# نصب پیش نیازها
NEED_PKG=0
command -v python3 &>/dev/null || NEED_PKG=1
command -v git     &>/dev/null || NEED_PKG=1

if [[ $NEED_PKG -eq 1 ]]; then
    echo -e "${CYAN}  نصب پیش نیازها (git, python3)...${NC}"
    apt-get update -qq
    apt-get install -y -qq git python3
fi

# تعیین محل wizard.py
# اگر اسکریپت از داخل پروژه اجرا شود از همان مسیر استفاده کن
# اگر با curl اجرا شود پروژه را clone کن
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)" || SCRIPT_DIR=""
LOCAL_WIZARD="${SCRIPT_DIR}/setup/wizard.py"

if [[ -f "$LOCAL_WIZARD" ]]; then
    WIZARD="$LOCAL_WIZARD"
    echo -e "${CYAN}  فایل های پروژه یافت شدند.${NC}"
else
    echo -e "${CYAN}  دانلود ShopBot از GitHub...${NC}"
    rm -rf "$TMP_DIR"
    git clone --depth=1 "$REPO_URL" "$TMP_DIR" 2>/dev/null \
        || { echo -e "${RED}  خطا: دانلود ناموفق. اتصال اینترنت را بررسی کنید.${NC}"; exit 1; }
    WIZARD="${TMP_DIR}/setup/wizard.py"
fi

[[ ! -f "$WIZARD" ]] && echo -e "${RED}  خطا: فایل setup/wizard.py یافت نشد.${NC}" && exit 1

# دریافت IP سرور
SERVER_IP=$(python3 -c "import socket; s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); s.connect(('8.8.8.8',80)); print(s.getsockname()[0]); s.close()" 2>/dev/null || echo "127.0.0.1")

echo ""
echo -e "  ${CYAN}Wizard آماده است. در مرورگر باز کنید:${NC}"
echo ""
echo -e "  ${BOLD}  =>  http://${SERVER_IP}:${PORT}${NC}"
echo ""
echo -e "  ------------------------------------------------------------"
echo -e "  برای توقف: Ctrl + C"
echo ""

exec python3 "$WIZARD"