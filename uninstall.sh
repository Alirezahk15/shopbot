#!/bin/bash
# =============================================================================
#  ShopBot — اسکریپت حذف
# =============================================================================
set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'

[[ $EUID -ne 0 ]] && echo -e "${RED}با root اجرا کنید${NC}" && exit 1

echo -e "${RED}  ── حذف ShopBot ──${NC}"
echo ""
echo -e "${YELLOW}  هشدار: دیتابیس و تمام داده‌ها حذف می‌شوند!${NC}"
read -rp "  مطمئن هستید؟ (yes/NO): " CONFIRM
[[ "$CONFIRM" != "yes" ]] && echo "لغو شد." && exit 0

echo ""
echo -e "  [→] توقف و حذف سرویس‌ها..."
systemctl stop shopbot shopbot-panel 2>/dev/null || true
systemctl disable shopbot shopbot-panel 2>/dev/null || true
rm -f /etc/systemd/system/shopbot.service
rm -f /etc/systemd/system/shopbot-panel.service
systemctl daemon-reload

echo "  [→] حذف Nginx config..."
rm -f /etc/nginx/sites-enabled/shopbot
rm -f /etc/nginx/sites-available/shopbot
nginx -t > /dev/null 2>&1 && systemctl reload nginx

echo "  [→] حذف فایل‌های پروژه..."
rm -rf /opt/shopbot

echo "  [→] حذف کاربر shopbot..."
userdel -r shopbot 2>/dev/null || true

echo ""
echo -e "${GREEN}  ShopBot با موفقیت حذف شد.${NC}"