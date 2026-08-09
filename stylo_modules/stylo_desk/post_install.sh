#!/bin/bash
# Stylo Desk post-install (telephony + helpdesk)
# telephony is installed before helpdesk (via apps.txt order) — helpdesk requires it.

set -e

SITE="${1}"
BENCH="${2:-/home/stylo/stylo}"

cd "$BENCH"

echo "[Stylo Desk] Running migrate..."
bench --site "$SITE" migrate

echo "[Stylo Desk] Clearing cache..."
bench --site "$SITE" clear-cache

echo "[Stylo Desk] Post-install complete."
echo "[Stylo Desk] Access at: https://$SITE/helpdesk"
