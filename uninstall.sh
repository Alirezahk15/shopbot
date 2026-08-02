#!/usr/bin/env bash
# Kept for backwards compatibility.
# The real uninstall lives in install.sh so it stays in sync with the installer.
#
#   shopbot            -> interactive menu
#   shopbot uninstall  -> same as running this script
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x /usr/local/bin/shopbot ]]; then
    exec /usr/local/bin/shopbot uninstall
elif [[ -f "$DIR/install.sh" ]]; then
    exec bash "$DIR/install.sh" uninstall
fi

echo "install.sh not found next to this script." >&2
exit 1
