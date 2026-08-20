#!/bin/bash
# Stylo Lending post-install
# Lending requires erpnext — Stylo BMS must be installed first.

set -e

SITE="${1}"
BENCH="${2:-/home/stylo/stylo}"

cd "$BENCH"
# bench isn't guaranteed to be on PATH in a non-interactive SSH shell (confirmed missing on stangroup)
export PATH="$BENCH/env/bin:$PATH"

echo "[Stylo Lending] Checking prerequisite: Stylo BMS (erpnext)..."
ERPNEXT_INSTALLED=$(bench --site "$SITE" list-apps 2>/dev/null | grep "^erpnext$" || true)
if [ -z "$ERPNEXT_INSTALLED" ]; then
  echo "ERROR: Stylo BMS (erpnext) must be installed before Stylo Lending."
  echo "Run: ./add_module.sh $SITE <server> stylo_bms first."
  exit 1
fi

echo "[Stylo Lending] Running migrate..."
bench --site "$SITE" migrate

echo "[Stylo Lending] Clearing cache..."
bench --site "$SITE" clear-cache

echo "[Stylo Lending] Post-install complete."
