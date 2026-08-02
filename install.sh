#!/usr/bin/env bash
# ============================================================================
#  ShopBot - Telegram Shop Bot + Admin Panel
#  Interactive installer & manager for Debian / Ubuntu servers
#
#  Usage:
#      bash <(curl -fsSL https://raw.githubusercontent.com/Alirezahk15/shopbot/main/install.sh)
#  After installation simply run:
#      shopbot
# ============================================================================
set -uo pipefail

# ---------------------------------------------------------------- constants
REPO="${REPO:-Alirezahk15/shopbot}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/shopbot}"
SERVICE_BOT="shopbot"
SERVICE_PANEL="shopbot-panel"
RUN_USER="shopbot"
WIZARD_PORT="${WIZARD_PORT:-8080}"
TMP_DIR="/tmp/shopbot-src"
LOG_FILE="/var/log/shopbot-install.log"
STATE_FILE="/var/lib/shopbot-install-state.json"
BACKUP_DIR="$INSTALL_DIR/backups"
LAUNCHER="/usr/local/bin/shopbot"
SELF_URL="https://raw.githubusercontent.com/$REPO/$BRANCH/install.sh"

# ------------------------------------------------------------------ colours
if [[ -t 1 ]]; then
  R=$'\e[0m'; B=$'\e[1m'; DIM=$'\e[2m'
  RED=$'\e[38;5;203m'; GRN=$'\e[38;5;114m'; YLW=$'\e[38;5;221m'
  BLU=$'\e[38;5;111m'; PUR=$'\e[38;5;141m'; CYN=$'\e[38;5;116m'; GRY=$'\e[38;5;245m'
else
  R=""; B=""; DIM=""; RED=""; GRN=""; YLW=""; BLU=""; PUR=""; CYN=""; GRY=""
fi

log()  { printf '%s\n' "$(date '+%F %T') $*" >>"$LOG_FILE" 2>/dev/null || true; }
say()  { printf '%s\n' "$*"; log "$*"; }
info() { say "  ${BLU}i${R}  $*"; }
ok()   { say "  ${GRN}OK${R} $*"; }
warn() { say "  ${YLW}!${R}  $*"; }
err()  { say "  ${RED}x${R}  $*"; }
step() { say ""; say "${PUR}${B}>> $*${R}"; }

die() {
  err "$1"
  [[ $# -gt 1 ]] && { say ""; say "  ${YLW}How to fix:${R}"; shift; for l in "$@"; do say "    - $l"; done; }
  say ""
  say "  ${GRY}Full log: $LOG_FILE${R}"
  exit 1
}

pause() { say ""; read -rp "  ${GRY}Press Enter to continue...${R} " _ || true; }

# ------------------------------------------------------------------- checks
require_root() {
  [[ ${EUID:-$(id -u)} -eq 0 ]] || die "This script must run as root." \
    "Run it again with: sudo bash $0"
}

require_debian() {
  command -v apt-get >/dev/null 2>&1 || die \
    "Unsupported distribution (apt-get not found)." \
    "ShopBot supports Debian 11+ and Ubuntu 20.04+."
}

is_installed() { [[ -d "$INSTALL_DIR" && -f "$INSTALL_DIR/.env" ]]; }

svc_state() {
  local s="$1"
  if ! systemctl list-unit-files 2>/dev/null | grep -q "^${s}.service"; then
    printf '%s' "${GRY}not installed${R}"
  elif systemctl is-active --quiet "$s"; then
    printf '%s' "${GRN}running${R}"
  else
    printf '%s' "${RED}stopped${R}"
  fi
}

# --------------------------------------------------------------- apt helper
wait_for_apt() {
  local waited=0 max=420
  while fuser /var/lib/dpkg/lock-frontend /var/lib/apt/lists/lock \
        /var/cache/apt/archives/lock >/dev/null 2>&1; do
    (( waited == 0 )) && info "Waiting for another package manager to finish..."
    sleep 5; waited=$((waited + 5))
    if (( waited >= max )); then
      die "Another process has held the apt lock for ${max}s." \
        "Wait for unattended-upgrades to finish, then retry." \
        "Or inspect it with: sudo lsof /var/lib/dpkg/lock-frontend"
    fi
  done
}

apt_install() {
  wait_for_apt
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$@" >>"$LOG_FILE" 2>&1
}

# ------------------------------------------------------------------ banner
banner() {
  clear 2>/dev/null || true
  cat <<EOF
${PUR}${B}
   ____  _                 ____        _
  / ___|| |__   ___  _ __ | __ )  ___ | |_
  \\___ \\| '_ \\ / _ \\| '_ \\|  _ \\ / _ \\| __|
   ___) | | | | (_) | |_) | |_) | (_) | |_
  |____/|_| |_|\\___/| .__/|____/ \\___/ \\__|
                    |_|
${R}${GRY}  Telegram Shop Bot + Admin Panel${R}
${GRY}  ------------------------------------------------${R}
EOF
}

status_line() {
  if is_installed; then
    local ver="unknown"
    [[ -f "$INSTALL_DIR/VERSION" ]] && ver=$(<"$INSTALL_DIR/VERSION")
    local domain=""
    domain=$(grep -sE '^PANEL_DOMAIN=' "$INSTALL_DIR/.env" | cut -d= -f2- | tr -d '"' || true)
    say "  Status : ${GRN}installed${R}  ${GRY}(v${ver})${R}"
    say "  Bot    : $(svc_state $SERVICE_BOT)     Panel: $(svc_state $SERVICE_PANEL)"
    [[ -n "$domain" ]] && say "  Panel  : ${CYN}https://${domain}${R}"
  else
    say "  Status : ${YLW}not installed${R}"
  fi
  say "${GRY}  ------------------------------------------------${R}"
}

# ============================================================ 1. INSTALL
do_install() {
  if is_installed; then
    warn "ShopBot is already installed at $INSTALL_DIR"
    read -rp "  Re-run the setup wizard anyway? [y/N] " a
    [[ "${a,,}" == "y" ]] || return 0
  fi

  step "Installing system packages"
  wait_for_apt
  DEBIAN_FRONTEND=noninteractive apt-get update -qq >>"$LOG_FILE" 2>&1
  apt_install python3 python3-pip python3-venv git curl wget rsync \
              nginx sqlite3 openssl ufw certbot python3-certbot-nginx \
              build-essential libssl-dev dnsutils psmisc \
    || die "Package installation failed." \
           "Check your network / apt sources, then retry." \
           "Details: tail -50 $LOG_FILE"
  ok "System packages ready"

  step "Installing Node.js 20 (for the admin panel build)"
  local need_node=1
  if command -v node >/dev/null 2>&1; then
    local major
    major=$(node -v | sed 's/v\([0-9]*\).*/\1/')
    [[ "$major" -ge 18 ]] && need_node=0
  fi
  if [[ $need_node -eq 1 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >>"$LOG_FILE" 2>&1 \
      || die "Could not add the NodeSource repository." "Check outbound HTTPS access."
    apt_install nodejs || die "Node.js installation failed."
  fi
  ok "Node.js $(node -v 2>/dev/null) ready"

  step "Downloading ShopBot source"
  rm -rf "$TMP_DIR"
  local url="https://github.com/$REPO.git"
  [[ -n "${GITHUB_TOKEN:-}" ]] && url="https://x-access-token:${GITHUB_TOKEN}@github.com/$REPO.git"
  git clone --depth 1 -b "$BRANCH" "$url" "$TMP_DIR" >>"$LOG_FILE" 2>&1 \
    || die "Could not download the source code." \
           "Verify the repository name and branch: $REPO ($BRANCH)" \
           "If the repo is private, export GITHUB_TOKEN=... first."
  ok "Source downloaded"

  step "Checking port $WIZARD_PORT"
  if ss -ltn 2>/dev/null | grep -q ":$WIZARD_PORT "; then
    die "Port $WIZARD_PORT is already in use." \
        "Free it, or run: WIZARD_PORT=8090 bash $0"
  fi
  command -v ufw >/dev/null 2>&1 && ufw allow "$WIZARD_PORT/tcp" >>"$LOG_FILE" 2>&1
  ok "Port $WIZARD_PORT is free"

  local ip
  ip=$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')

  say ""
  say "${GRN}${B}  Setup wizard is starting.${R}"
  say ""
  say "  Open this address in your browser:"
  say "      ${CYN}${B}http://${ip}:${WIZARD_PORT}${R}"
  say ""
  say "  ${GRY}Keep this terminal open until the wizard finishes.${R}"
  say ""

  export SHOPBOT_WIZARD_PORT="$WIZARD_PORT"
  export SHOPBOT_INSTALL_LOG="$LOG_FILE"
  install_launcher
  exec python3 "$TMP_DIR/setup/wizard.py"
}

# ============================================================ 2. UPDATE
do_update() {
  is_installed || { err "ShopBot is not installed yet. Choose option 1 first."; return 1; }

  step "Backing up the database"
  mkdir -p "$BACKUP_DIR"
  local stamp backup
  stamp=$(date +%Y%m%d_%H%M%S)
  backup="$BACKUP_DIR/pre_update_$stamp.db"
  if [[ -f "$INSTALL_DIR/shop.db" ]]; then
    sqlite3 "$INSTALL_DIR/shop.db" ".backup '$backup'" 2>>"$LOG_FILE" \
      || cp "$INSTALL_DIR/shop.db" "$backup"
    ok "Backup saved to $backup"
  else
    warn "No database found yet - skipping backup"
  fi

  step "Fetching the latest version"
  rm -rf "$TMP_DIR"
  local url="https://github.com/$REPO.git"
  [[ -n "${GITHUB_TOKEN:-}" ]] && url="https://x-access-token:${GITHUB_TOKEN}@github.com/$REPO.git"
  git clone --depth 1 -b "$BRANCH" "$url" "$TMP_DIR" >>"$LOG_FILE" 2>&1 \
    || { err "Download failed - your installation was NOT modified."; return 1; }
  ok "Latest version downloaded"

  step "Updating application files"
  rsync -a --delete \
    --exclude '.env' --exclude '*.db' --exclude '*.db-wal' --exclude '*.db-shm' \
    --exclude 'backups/' --exclude 'venv/' --exclude 'uploads/' \
    --exclude '__pycache__/' --exclude '.git/' --exclude 'node_modules/' \
    "$TMP_DIR/" "$INSTALL_DIR/" >>"$LOG_FILE" 2>&1 \
    || { err "Copying files failed. Restore from $backup if needed."; return 1; }
  ok "Files updated"

  step "Updating Python dependencies"
  if [[ -f "$INSTALL_DIR/requirements.txt" ]]; then
    "$INSTALL_DIR/venv/bin/pip" install -q --upgrade -r "$INSTALL_DIR/requirements.txt" >>"$LOG_FILE" 2>&1 \
      || { err "pip install failed. See $LOG_FILE"; return 1; }
    ok "Python dependencies up to date"
  else
    warn "requirements.txt not found - skipped"
  fi

  step "Applying database migrations"
  ( cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" migrate_db.py >>"$LOG_FILE" 2>&1 ) \
    && ok "Database schema is current" \
    || warn "Migration script reported an issue - see $LOG_FILE"

  step "Rebuilding the admin panel"
  if [[ -d "$INSTALL_DIR/panel" ]]; then
    ( cd "$INSTALL_DIR/panel" && npm ci --no-audit --no-fund >>"$LOG_FILE" 2>&1 \
      && npm run build >>"$LOG_FILE" 2>&1 ) \
      && ok "Panel rebuilt" \
      || { err "Panel build failed. See $LOG_FILE"; return 1; }
  fi

  chown -R "$RUN_USER:$RUN_USER" "$INSTALL_DIR" 2>/dev/null || true

  step "Restarting services"
  systemctl daemon-reload
  systemctl restart "$SERVICE_BOT" "$SERVICE_PANEL"
  sleep 2
  ok "Bot: $(svc_state $SERVICE_BOT)   Panel: $(svc_state $SERVICE_PANEL)"

  install_launcher
  say ""
  ok "${GRN}${B}Update completed successfully.${R}"
}

# ============================================================ 3. UNINSTALL
do_uninstall() {
  say ""
  warn "${B}This will remove ShopBot, its services and its nginx site.${R}"
  read -rp "  Type ${B}REMOVE${R} to confirm: " confirm
  [[ "$confirm" == "REMOVE" ]] || { info "Cancelled."; return 0; }

  local keep="n"
  if [[ -f "$INSTALL_DIR/shop.db" ]]; then
    read -rp "  Keep a copy of the database in /root ? [Y/n] " keep
    if [[ "${keep,,}" != "n" ]]; then
      local out="/root/shopbot-final-$(date +%Y%m%d_%H%M%S).db"
      cp "$INSTALL_DIR/shop.db" "$out" 2>/dev/null && ok "Database saved to $out"
    fi
  fi

  step "Stopping services"
  systemctl stop "$SERVICE_BOT" "$SERVICE_PANEL" 2>/dev/null || true
  systemctl disable "$SERVICE_BOT" "$SERVICE_PANEL" 2>/dev/null || true
  rm -f "/etc/systemd/system/${SERVICE_BOT}.service" \
        "/etc/systemd/system/${SERVICE_PANEL}.service"
  systemctl daemon-reload 2>/dev/null || true
  ok "Services removed"

  step "Removing the nginx site"
  rm -f /etc/nginx/sites-enabled/shopbot /etc/nginx/sites-available/shopbot
  if nginx -t >/dev/null 2>&1; then
    systemctl reload nginx >/dev/null 2>&1 || true
    ok "nginx reloaded"
  else
    warn "nginx config test failed - please review it manually"
  fi

  step "Removing files"
  rm -rf "$INSTALL_DIR" "$TMP_DIR" "$STATE_FILE" "$LAUNCHER"
  ok "Files removed"

  step "Removing the service account"
  if id "$RUN_USER" >/dev/null 2>&1; then
    userdel -r "$RUN_USER" >/dev/null 2>&1 || userdel "$RUN_USER" >/dev/null 2>&1 || true
    ok "User '$RUN_USER' removed"
  fi

  command -v ufw >/dev/null 2>&1 && ufw delete allow "$WIZARD_PORT/tcp" >/dev/null 2>&1

  say ""
  ok "${GRN}${B}ShopBot has been completely removed.${R}"
}

# ============================================================ 4. SERVICES
do_restart() {
  is_installed || { err "ShopBot is not installed."; return 1; }
  step "Restarting services"
  systemctl restart "$SERVICE_BOT" "$SERVICE_PANEL"
  sleep 2
  ok "Bot: $(svc_state $SERVICE_BOT)   Panel: $(svc_state $SERVICE_PANEL)"
}

do_stop() {
  is_installed || { err "ShopBot is not installed."; return 1; }
  systemctl stop "$SERVICE_BOT" "$SERVICE_PANEL"
  ok "Services stopped"
}

do_start() {
  is_installed || { err "ShopBot is not installed."; return 1; }
  systemctl start "$SERVICE_BOT" "$SERVICE_PANEL"
  sleep 2
  ok "Bot: $(svc_state $SERVICE_BOT)   Panel: $(svc_state $SERVICE_PANEL)"
}

do_status() {
  is_installed || { err "ShopBot is not installed."; return 1; }
  step "Service status"
  systemctl --no-pager --lines=0 status "$SERVICE_BOT" 2>&1 | head -8
  say ""
  systemctl --no-pager --lines=0 status "$SERVICE_PANEL" 2>&1 | head -8
}

do_logs() {
  say ""
  say "  1) Bot logs        2) Panel logs        3) Installer log"
  read -rp "  Choose [1-3]: " c
  case "$c" in
    1) journalctl -u "$SERVICE_BOT" -n 100 --no-pager ;;
    2) journalctl -u "$SERVICE_PANEL" -n 100 --no-pager ;;
    3) tail -n 100 "$LOG_FILE" ;;
    *) warn "Invalid choice" ;;
  esac
}

# ============================================================ 5. BACKUP
do_backup() {
  is_installed || { err "ShopBot is not installed."; return 1; }
  [[ -f "$INSTALL_DIR/shop.db" ]] || { err "No database found."; return 1; }
  mkdir -p "$BACKUP_DIR"
  local out="$BACKUP_DIR/manual_$(date +%Y%m%d_%H%M%S).db"
  sqlite3 "$INSTALL_DIR/shop.db" ".backup '$out'" 2>>"$LOG_FILE" || cp "$INSTALL_DIR/shop.db" "$out"
  ok "Backup created: $out"
  say "  ${GRY}Copy it off the server with:${R}"
  say "    scp root@$(hostname -I | awk '{print $1}'):$out ./"
}

# ============================================================ 6. PASSWORD
do_reset_password() {
  is_installed || { err "ShopBot is not installed."; return 1; }
  step "Reset admin panel password"
  if [[ -f "$INSTALL_DIR/reset_panel_admin.py" ]]; then
    ( cd "$INSTALL_DIR" && "$INSTALL_DIR/venv/bin/python" reset_panel_admin.py )
  else
    err "reset_panel_admin.py is missing from $INSTALL_DIR"
    return 1
  fi
  systemctl restart "$SERVICE_PANEL" 2>/dev/null || true
  ok "Panel restarted"
}

# ============================================================ 7. SSL
do_ssl() {
  is_installed || { err "ShopBot is not installed."; return 1; }
  read -rp "  Domain name (e.g. bot.example.com): " domain
  [[ -n "$domain" ]] || { err "Domain cannot be empty."; return 1; }
  read -rp "  Email for Let's Encrypt notices: " email
  step "Requesting a certificate for $domain"
  certbot --nginx -d "$domain" --non-interactive --agree-tos \
          -m "${email:-admin@$domain}" --redirect \
    && ok "HTTPS is now active: https://$domain" \
    || err "Certificate request failed. Make sure $domain points to this server."
}

# ---------------------------------------------------------------- launcher
install_launcher() {
  local src="$INSTALL_DIR/install.sh"
  [[ -f "$src" ]] || src="$TMP_DIR/install.sh"
  if [[ -f "$src" ]]; then
    cp "$src" "$LAUNCHER" 2>/dev/null && chmod +x "$LAUNCHER" 2>/dev/null && return 0
  fi
  cat >"$LAUNCHER" <<EOF
#!/usr/bin/env bash
bash <(curl -fsSL $SELF_URL) "\$@"
EOF
  chmod +x "$LAUNCHER"
}

# -------------------------------------------------------------------- menu
menu() {
  while true; do
    banner
    status_line
    say ""
    say "   ${B}${GRN}1${R})  Install ShopBot            ${GRY}(guided web wizard)${R}"
    say "   ${B}${BLU}2${R})  Update to the latest version"
    say "   ${B}${RED}3${R})  Uninstall ShopBot"
    say ""
    say "   ${B}4${R})  Restart services            ${B}5${R})  Start services"
    say "   ${B}6${R})  Stop services               ${B}7${R})  Service status"
    say "   ${B}8${R})  View logs                   ${B}9${R})  Backup database"
    say ""
    say "   ${B}10${R}) Reset panel password        ${B}11${R}) Setup / renew SSL"
    say ""
    say "   ${B}0${R})  Exit"
    say "${GRY}  ------------------------------------------------${R}"
    read -rp "  ${B}Select an option [0-11]:${R} " choice

    case "$choice" in
      1)  do_install ;;
      2)  do_update; pause ;;
      3)  do_uninstall; pause ;;
      4)  do_restart; pause ;;
      5)  do_start; pause ;;
      6)  do_stop; pause ;;
      7)  do_status; pause ;;
      8)  do_logs; pause ;;
      9)  do_backup; pause ;;
      10) do_reset_password; pause ;;
      11) do_ssl; pause ;;
      0)  say ""; say "  ${GRY}Bye.${R}"; exit 0 ;;
      *)  warn "Invalid option: $choice"; sleep 1 ;;
    esac
  done
}

# -------------------------------------------------------------------- main
require_root
require_debian
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
touch "$LOG_FILE" 2>/dev/null || true

# Non-interactive shortcuts:  shopbot install | update | uninstall | restart ...
case "${1:-}" in
  install)   do_install; exit $? ;;
  update)    do_update; exit $? ;;
  uninstall) do_uninstall; exit $? ;;
  restart)   do_restart; exit $? ;;
  start)     do_start; exit $? ;;
  stop)      do_stop; exit $? ;;
  status)    do_status; exit $? ;;
  backup)    do_backup; exit $? ;;
  "")        menu ;;
  *)         err "Unknown command: $1"
             say "  Valid: install update uninstall restart start stop status backup"
             exit 1 ;;
esac
