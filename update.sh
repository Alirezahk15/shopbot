#!/usr/bin/env bash
# Kept for backwards compatibility.
# Everything now lives in the single install.sh menu, so there is only one
# place where the update logic can drift out of date.
#
#   shopbot          -> interactive menu
#   shopbot update   -> same as running this script
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -x /usr/local/bin/shopbot ]]; then
    exec /usr/local/bin/shopbot update
elif [[ -f "$DIR/install.sh" ]]; then
    exec bash "$DIR/install.sh" update
fi

echo "install.sh not found next to this script." >&2
echo "Run:  bash <(curl -fsSL https://raw.githubusercontent.com/Alirezahk15/shopbot/main/install.sh)" >&2
exit 1
