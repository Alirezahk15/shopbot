#!/bin/bash
# =============================================================================
#  ShopBot -- Installer
#
#  روش 1 -- نصب مستقیم (فقط وقتی ریپو Public است):
#    sudo bash <(curl -fsSL https://raw.githubusercontent.com/Alirezahk15/shopbot/main/install.sh)
#
#  روش 2 -- نصب از ریپوی Private با Personal Access Token:
#    export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
#    sudo -E bash <(curl -fsSL -H "Authorization: Bearer $GITHUB_TOKEN" \
#      https://raw.githubusercontent.com/Alirezahk15/shopbot/main/install.sh)
#
#  روش 3 -- اجرا از روی سورس دانلودشده (بدون نیاز به گیتهاب):
#    sudo bash install.sh
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'

[[ $EUID -ne 0 ]] && echo -e "${RED}خطا: با دسترسی root اجرا کنید.${NC}" && exit 1

REPO="Alirezahk15/shopbot"
REPO_URL="https://github.com/${REPO}.git"
TMP_DIR="/tmp/shopbot-src"
PORT=8080
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# برای ریپوی Private، توکن را در آدرس clone تزریق کن
if [[ -n "$GITHUB_TOKEN" ]]; then
    CLONE_URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git"
else
    CLONE_URL="$REPO_URL"
fi

# هدر
clear 2>/dev/null || true
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
    if ! git clone --depth=1 "$CLONE_URL" "$TMP_DIR" 2>/tmp/shopbot-clone-error.log; then
        echo ""
        echo -e "${RED}  ✗ خطا: دانلود پروژه از GitHub ناموفق بود.${NC}"
        if [[ -z "$GITHUB_TOKEN" ]]; then
            echo -e "${YELLOW}  ──────────────────────────────────────────────────────────"
            echo "  علت رایج: ریپو Private است و بدون توکن قابل دانلود نیست."
            echo "  (خطای 404 در curl و 'Authentication failed' در git)"
            echo ""
            echo "  راه‌حل‌ها (یکی را انتخاب کنید):"
            echo ""
            echo "  ۱) ریپو را موقتاً Public کنید:"
            echo "     GitHub → Settings → Danger Zone → Change visibility → Public"
            echo "     بعد از اتمام نصب می‌توانید دوباره Private کنید."
            echo ""
            echo "  ۲) با Personal Access Token نصب کنید (ریپو Private می‌ماند):"
            echo "     export GITHUB_TOKEN=ghp_xxxxxxxxxxxx"
            echo "     sudo -E bash <(curl -fsSL -H \"Authorization: Bearer \$GITHUB_TOKEN\" \\"
            echo "       https://raw.githubusercontent.com/${REPO}/main/install.sh)"
            echo ""
            echo "  ۳) سورس را دستی روی سرور کپی کنید و اجرا کنید:"
            echo "     sudo bash install.sh"
            echo -e "  ──────────────────────────────────────────────────────────${NC}"
        else
            echo -e "${YELLOW}  توکن GITHUB_TOKEN نامعتبر است یا دسترسی repo ندارد.${NC}"
            echo "  یک توکن با scope=repo بسازید: GitHub → Settings → Developer settings → Tokens"
        fi
        echo -e "${RED}  جزئیات فنی: $(tail -n 1 /tmp/shopbot-clone-error.log 2>/dev/null || echo 'unknown')${NC}"
        exit 1
    fi
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
