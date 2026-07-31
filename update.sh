#!/bin/bash
# =============================================================================
#  ShopBot — اسکریپت آپدیت
# =============================================================================
set -euo pipefail

GREEN='\033[0;32m'; BLUE='\033[0;34m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  [✓]${NC} $1"; }
info() { echo -e "${BLUE}  [→]${NC} $1"; }
die()  { echo -e "${RED}  [✗] خطا: $1${NC}"; exit 1; }

[[ $EUID -ne 0 ]] && die "با دسترسی root اجرا کنید: sudo bash update.sh"

INSTALL_DIR="/opt/shopbot"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}  ── ShopBot Update ──${NC}"
echo ""

# بکاپ دیتابیس قبل از آپدیت
info "بکاپ دیتابیس..."
BACKUP_FILE="$INSTALL_DIR/backups/pre_update_$(date +%Y%m%d_%H%M%S).db"
mkdir -p "$INSTALL_DIR/backups"
[[ -f "$INSTALL_DIR/shop.db" ]] && cp "$INSTALL_DIR/shop.db" "$BACKUP_FILE" && ok "بکاپ: $BACKUP_FILE"

# توقف سرویس‌ها
info "توقف سرویس‌ها..."
systemctl stop shopbot shopbot-panel 2>/dev/null || true

# کپی فایل‌های جدید (بدون .env و دیتابیس)
info "کپی فایل‌های جدید..."
rsync -a \
    --exclude='.env' \
    --exclude='*.db' \
    --exclude='backups/' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='panel/dist' \
    --exclude='venv' \
    "$SCRIPT_DIR/" "$INSTALL_DIR/"
ok "فایل‌ها کپی شدند"

# آپدیت وابستگی‌های Python
info "آپدیت وابستگی‌های Python..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade -q \
    "python-telegram-bot>=20.0" \
    "fastapi>=0.100.0" \
    "uvicorn[standard]>=0.23.0" \
    "python-jose[cryptography]>=3.3.0" \
    "bcrypt>=4.0.0" \
    "pydantic>=2.0.0" \
    "python-dotenv" requests
ok "وابستگی‌ها آپدیت شدند"

# Build مجدد پنل React
if [[ -d "$INSTALL_DIR/panel" ]]; then
    info "Build مجدد پنل React..."
    cd "$INSTALL_DIR/panel"
    npm install --silent --no-progress 2>/dev/null
    npm run build --silent 2>/dev/null
    cd "$INSTALL_DIR"
    ok "پنل React build شد"
fi

# تنظیم مجوزها
chown -R shopbot:shopbot "$INSTALL_DIR"

# راه‌اندازی مجدد
info "راه‌اندازی مجدد سرویس‌ها..."
systemctl daemon-reload
systemctl start shopbot shopbot-panel
sleep 3

BOT_ST=$(systemctl is-active shopbot 2>/dev/null || echo "failed")
API_ST=$(systemctl is-active shopbot-panel 2>/dev/null || echo "failed")
echo ""
echo -e "  🤖 ربات:   $([ "$BOT_ST" = "active" ] && echo "${GREEN}● فعال${NC}" || echo "${RED}● خطا${NC}")"
echo -e "  🌐 پنل:    $([ "$API_ST" = "active" ] && echo "${GREEN}● فعال${NC}" || echo "${RED}● خطا${NC}")"
echo ""
ok "آپدیت کامل شد!"