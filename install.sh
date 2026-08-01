#!/bin/bash
# =============================================================================
#  ShopBot - Installer (English only)
#
#  Method 1 - Direct install (only when the repo is PUBLIC):
#    curl -fsSL -o /tmp/install.sh https://raw.githubusercontent.com/Alirezahk15/shopbot/main/install.sh
#    sudo bash /tmp/install.sh
#
#  Method 2 - Private repo with a Personal Access Token:
#    export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
#    curl -fsSL -o /tmp/install.sh -H "Authorization: Bearer $GITHUB_TOKEN" \
#      https://raw.githubusercontent.com/Alirezahk15/shopbot/main/install.sh
#    sudo -E bash /tmp/install.sh
#
#  Method 3 - Offline, from an already downloaded source tree:
#    sudo bash install.sh
# =============================================================================

set -uo pipefail

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; CYAN=$'\033[0;36m'
YELLOW=$'\033[1;33m'; BLUE=$'\033[0;34m'; BOLD=$'\033[1m'; DIM=$'\033[2m'; NC=$'\033[0m'

REPO="Alirezahk15/shopbot"
BRANCH="${BRANCH:-main}"
TMP_DIR="/tmp/shopbot-src"
PORT="${WIZARD_PORT:-8080}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
LOG_FILE="/var/log/shopbot-install.log"

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
log()   { printf '%s\n' "$*" >>"$LOG_FILE" 2>/dev/null || true; }
info()  { echo "${CYAN}  [*]${NC} $*"; log "[info] $*"; }
ok()    { echo "${GREEN}  [OK]${NC} $*"; log "[ok] $*"; }
warn()  { echo "${YELLOW}  [!]${NC} $*"; log "[warn] $*"; }
step()  { echo; echo "${BLUE}${BOLD}  >> $*${NC}"; log "[step] $*"; }

# fail "<title>" "<technical detail>" "<solution line 1>" "<solution line 2>" ...
fail() {
    local title="$1"; shift
    local detail="${1:-}"; shift || true
    echo
    echo "${RED}${BOLD}  ============================================================${NC}"
    echo "${RED}${BOLD}  [X] FAILED: ${title}${NC}"
    echo "${RED}${BOLD}  ============================================================${NC}"
    if [ -n "$detail" ]; then
        echo "${DIM}  Technical detail:${NC}"
        echo "${DIM}    ${detail}${NC}"
    fi
    if [ "$#" -gt 0 ]; then
        echo
        echo "${YELLOW}${BOLD}  HOW TO FIX THIS:${NC}"
        local i=1
        for line in "$@"; do
            if [ -n "$line" ]; then
                echo "${YELLOW}    ${i}) ${line}${NC}"
                i=$((i + 1))
            fi
        done
    fi
    echo
    echo "${DIM}  Full log: ${LOG_FILE}${NC}"
    echo "${DIM}  After fixing, just run the installer again - it resumes safely.${NC}"
    echo
    exit 1
}

# ---------------------------------------------------------------------------
# Root check
# ---------------------------------------------------------------------------
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    fail "Root privileges required" "Current user id is $(id -u), expected 0." \
        "Run the installer with sudo:  sudo bash install.sh" \
        "Or switch to root first:  sudo -i"
fi

mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true
: >"$LOG_FILE" 2>/dev/null || LOG_FILE=/tmp/shopbot-install.log

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
clear 2>/dev/null || true
echo "${GREEN}${BOLD}"
echo "  ============================================================"
echo "  |                                                          |"
echo "  |             S H O P B O T   -   I N S T A L L E R        |"
echo "  |                                                          |"
echo "  ============================================================"
echo "${NC}"

# ---------------------------------------------------------------------------
# OS check
# ---------------------------------------------------------------------------
if ! command -v apt-get >/dev/null 2>&1; then
    OS_NAME="unknown"
    [ -r /etc/os-release ] && OS_NAME="$(. /etc/os-release && echo "${PRETTY_NAME:-unknown}")"
    fail "Unsupported operating system" "apt-get not found. Detected: ${OS_NAME}" \
        "ShopBot supports Debian 11/12 and Ubuntu 20.04/22.04/24.04 only." \
        "Reinstall your server with Ubuntu 22.04 LTS and try again."
fi

# ---------------------------------------------------------------------------
# Wait for the apt/dpkg lock instead of dying on it
# ---------------------------------------------------------------------------
wait_for_apt() {
    local max="${1:-300}" waited=0 holder=""
    local locks="/var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/lib/apt/lists/lock /var/cache/apt/archives/lock"

    while :; do
        local busy=0
        for f in $locks; do
            if [ -e "$f" ] && fuser "$f" >/dev/null 2>&1; then busy=1; break; fi
        done
        pgrep -x unattended-upgr >/dev/null 2>&1 && busy=1
        [ "$busy" -eq 0 ] && return 0

        if [ "$waited" -eq 0 ]; then
            holder="$(fuser -v /var/lib/dpkg/lock-frontend 2>&1 | tail -n 1 | awk '{print $NF}')"
            warn "Another package manager is running (likely unattended-upgrades). Waiting..."
        fi
        if [ "$waited" -ge "$max" ]; then
            return 1
        fi
        printf '\r%s' "${DIM}      waiting for apt lock... ${waited}s / ${max}s${NC}"
        sleep 5
        waited=$((waited + 5))
    done
}

apt_lock_help() {
    fail "Could not acquire the apt/dpkg lock" \
        "/var/lib/dpkg/lock-frontend is held by another process." \
        "See who holds it:  ps -eo pid,etime,cmd | grep -E 'apt|dpkg' | grep -v grep" \
        "If it is unattended-upgrades, stop it:  sudo systemctl stop unattended-upgrades" \
        "Kill the stuck process:  sudo kill <PID>   (then  sudo kill -9 <PID>  if needed)" \
        "Repair dpkg afterwards:  sudo dpkg --configure -a && sudo apt-get update" \
        "As a last resort (ONLY if no apt process is alive): sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock"
}

# ---------------------------------------------------------------------------
# Prerequisites: git + python3 + curl
# ---------------------------------------------------------------------------
step "Step 1/4  Checking prerequisites"

MISSING=""
for bin in python3 git curl; do
    command -v "$bin" >/dev/null 2>&1 || MISSING="$MISSING $bin"
done

if [ -n "$MISSING" ]; then
    info "Installing missing packages:${MISSING}"
    wait_for_apt 300 || apt_lock_help
    echo
    if ! apt-get update -qq >>"$LOG_FILE" 2>&1; then
        warn "apt-get update reported problems, continuing anyway."
    fi
    wait_for_apt 300 || apt_lock_help
    if ! DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $MISSING >>"$LOG_FILE" 2>&1; then
        DETAIL="$(tail -n 3 "$LOG_FILE" 2>/dev/null | tr '\n' ' ')"
        case "$DETAIL" in
            *lock*|*Unable\ to\ acquire*) apt_lock_help ;;
        esac
        fail "Installing prerequisites (${MISSING# })" "$DETAIL" \
            "Check internet access:  ping -c 3 deb.debian.org" \
            "Refresh package lists:  sudo apt-get update --fix-missing" \
            "Fix broken packages:    sudo apt-get -f install" \
            "Then run the installer again."
    fi
    ok "Prerequisites installed"
else
    ok "python3, git and curl are already present"
fi

PY_VER="$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo 0.0)"
PY_MAJOR="${PY_VER%%.*}"; PY_MINOR="${PY_VER##*.}"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    fail "Python version too old" "Found Python ${PY_VER}, need 3.8 or newer." \
        "Install a newer Python:  sudo apt-get install -y python3.11 python3.11-venv" \
        "Or use Ubuntu 22.04 / 24.04 which ship a supported Python."
fi
ok "Python ${PY_VER} detected"

# ---------------------------------------------------------------------------
# Locate wizard.py (local source tree, otherwise clone)
# ---------------------------------------------------------------------------
step "Step 2/4  Locating ShopBot source"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)" || SCRIPT_DIR=""
WIZARD=""

if [ -n "$SCRIPT_DIR" ] && [ -f "${SCRIPT_DIR}/setup/wizard.py" ]; then
    WIZARD="${SCRIPT_DIR}/setup/wizard.py"
    ok "Local source tree found: ${SCRIPT_DIR}"
else
    info "No local source next to the script - downloading from GitHub"

    if [ -n "$GITHUB_TOKEN" ]; then
        CLONE_URL="https://x-access-token:${GITHUB_TOKEN}@github.com/${REPO}.git"
        info "Using GITHUB_TOKEN for a private repository"
    else
        CLONE_URL="https://github.com/${REPO}.git"
    fi

    rm -rf "$TMP_DIR"
    if ! git clone --depth=1 --branch "$BRANCH" "$CLONE_URL" "$TMP_DIR" >>"$LOG_FILE" 2>&1; then
        DETAIL="$(grep -iE 'fatal|error' "$LOG_FILE" | tail -n 1 | sed "s#${GITHUB_TOKEN:-__none__}#***#g")"
        if [ -z "$GITHUB_TOKEN" ]; then
            fail "Could not download ShopBot from GitHub" "$DETAIL" \
                "Most likely cause: the repository is PRIVATE (curl shows 404, git shows 'Authentication failed')." \
                "Make it public temporarily: GitHub > Settings > Danger Zone > Change visibility > Public" \
                "Or use a token: export GITHUB_TOKEN=ghp_xxx  then  sudo -E bash install.sh" \
                "Or copy the source to the server manually and run:  sudo bash install.sh" \
                "Check the branch name too - this installer uses branch '${BRANCH}'."
        else
            fail "GitHub authentication failed" "$DETAIL" \
                "Your GITHUB_TOKEN is invalid, expired, or lacks the 'repo' scope." \
                "Create a new one: GitHub > Settings > Developer settings > Personal access tokens" \
                "Make sure you exported it AND used sudo -E:  sudo -E bash install.sh" \
                "Verify the branch '${BRANCH}' exists in ${REPO}."
        fi
    fi
    WIZARD="${TMP_DIR}/setup/wizard.py"
    ok "Source downloaded to ${TMP_DIR}"
fi

if [ ! -f "$WIZARD" ]; then
    fail "setup/wizard.py not found" "Expected at: ${WIZARD}" \
        "The downloaded/copied source tree is incomplete." \
        "Delete the cache and retry:  sudo rm -rf ${TMP_DIR}" \
        "If installing offline, run install.sh from the project root folder."
fi

if ! python3 -c "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$WIZARD" >>"$LOG_FILE" 2>&1; then
    fail "setup/wizard.py is corrupted" "$(tail -n 2 "$LOG_FILE" | tr '\n' ' ')" \
        "The file was damaged in transfer (often Windows CRLF line endings)." \
        "Fix it:  sudo sed -i 's/\\r$//' ${WIZARD}" \
        "Or re-download a clean copy:  sudo rm -rf ${TMP_DIR}  and run the installer again."
fi
ok "Wizard script verified"

# ---------------------------------------------------------------------------
# Port availability
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Build the React setup wizard (same stack as the admin panel).
# This is best-effort: if Node.js or the build fails for any reason, the
# wizard still starts using its built-in HTML interface.
# ---------------------------------------------------------------------------
step "Step 3/4  Building the wizard interface"

SRC_ROOT="$(cd "$(dirname "$WIZARD")/.." 2>/dev/null && pwd)" || SRC_ROOT=""
UI_DIR="${SRC_ROOT}/setup/ui"
UI_BUILT=0

if [ -f "${UI_DIR}/dist/index.html" ]; then
    UI_BUILT=1
    ok "Wizard interface already built - skipping"
elif [ ! -f "${UI_DIR}/package.json" ]; then
    warn "Wizard UI source not found - using the built-in interface"
else
    NODE_MAJOR=0
    if command -v node >/dev/null 2>&1; then
        NODE_MAJOR="$(node -v 2>/dev/null | sed "s/^v//" | cut -d. -f1)"
        case "$NODE_MAJOR" in (*[!0-9]*|"") NODE_MAJOR=0 ;; esac
    fi

    if [ "$NODE_MAJOR" -lt 18 ]; then
        info "Installing Node.js 20 (needed to build the wizard interface)"
        wait_for_apt || true
        if curl -fsSL https://deb.nodesource.com/setup_20.x -o /tmp/nodesource.sh >>"$LOG_FILE" 2>&1 \
            && bash /tmp/nodesource.sh >>"$LOG_FILE" 2>&1 \
            && wait_for_apt \
            && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs >>"$LOG_FILE" 2>&1; then
            NODE_MAJOR="$(node -v 2>/dev/null | sed "s/^v//" | cut -d. -f1)"
            case "$NODE_MAJOR" in (*[!0-9]*|"") NODE_MAJOR=0 ;; esac
            ok "Node.js $(node -v 2>/dev/null) installed"
        else
            warn "Could not install Node.js now - the wizard will use its built-in interface"
            warn "The installer will install Node.js again later for the admin panel"
        fi
    else
        ok "Node.js $(node -v 2>/dev/null) detected"
    fi

    if [ "$NODE_MAJOR" -ge 18 ]; then
        info "Building the wizard interface (about 1-2 minutes)..."
        if ( cd "$UI_DIR" \
             && npm install --no-audit --no-fund --loglevel=error >>"$LOG_FILE" 2>&1 \
             && npm run build >>"$LOG_FILE" 2>&1 ); then
            if [ -f "${UI_DIR}/dist/index.html" ]; then
                UI_BUILT=1
                ok "Wizard interface built successfully"
            else
                warn "Build finished but no output was produced - using the built-in interface"
            fi
        else
            warn "Wizard interface build failed - using the built-in interface instead"
            warn "Details are in ${LOG_FILE} (this does not stop the installation)"
        fi
    fi
fi

if [ "$UI_BUILT" -eq 1 ]; then
    info "Interface: React (same design as the admin panel)"
else
    info "Interface: built-in HTML wizard (fully functional)"
fi

step "Step 4/4  Starting the setup wizard"

if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | grep -q ":${PORT} "; then
    HOLDER="$(ss -ltnp 2>/dev/null | grep ":${PORT} " | head -n 1 | sed 's/.*users:((//' | cut -d, -f1 | tr -d '\"')"
    fail "Port ${PORT} is already in use" "Held by: ${HOLDER:-unknown}" \
        "Find the process:  sudo ss -ltnp | grep :${PORT}" \
        "Stop it, or run the installer on another port:  sudo WIZARD_PORT=8081 bash install.sh" \
        "If a previous wizard is stuck:  sudo pkill -f setup/wizard.py"
fi

SERVER_IP="$(python3 - <<'PY' 2>/dev/null || echo 127.0.0.1
import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    print(s.getsockname()[0])
    s.close()
except Exception:
    print("127.0.0.1")
PY
)"

if command -v ufw >/dev/null 2>&1 && ufw status 2>/dev/null | grep -qi '^Status: active'; then
    ufw allow "${PORT}/tcp" >/dev/null 2>&1 && info "Opened port ${PORT} in UFW for the wizard"
fi

echo
echo "${GREEN}${BOLD}  ------------------------------------------------------------${NC}"
echo "${GREEN}${BOLD}   The setup wizard is ready. Open this URL in your browser:${NC}"
echo
echo "${BOLD}${CYAN}       http://${SERVER_IP}:${PORT}${NC}"
echo
echo "${DIM}   If the page does not load, open port ${PORT} in your provider's firewall.${NC}"
echo "${DIM}   Press Ctrl + C here to stop the wizard.${NC}"
echo "${GREEN}${BOLD}  ------------------------------------------------------------${NC}"
echo

export SHOPBOT_WIZARD_PORT="$PORT"
export SHOPBOT_INSTALL_LOG="$LOG_FILE"
exec python3 "$WIZARD"
