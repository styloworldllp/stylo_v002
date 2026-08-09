#!/bin/bash
# Stylo Reco post-install (mint — bank reconciliation)
# No hard dependency but works best alongside Stylo BMS.

set -e

SITE="${1}"
BENCH="${2:-/home/stylo/stylo}"

cd "$BENCH"

ERPNEXT_INSTALLED=$(bench --site "$SITE" list-apps 2>/dev/null | grep "^erpnext$" || true)
if [ -z "$ERPNEXT_INSTALLED" ]; then
  echo "[Stylo Reco] WARNING: Stylo BMS is not installed. Reco works best with BMS for bank reconciliation."
fi

echo "[Stylo Reco] Running migrate..."
bench --site "$SITE" migrate

echo "[Stylo Reco] Clearing cache..."
bench --site "$SITE" clear-cache

echo "[Stylo Reco] Post-install complete."
echo "[Stylo Reco] NOTE: Configure Google Document AI credentials in Reco Settings."
