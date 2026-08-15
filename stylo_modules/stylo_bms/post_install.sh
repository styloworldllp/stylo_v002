#!/bin/bash
# Stylo BMS post-install — migrate and clear cache after ERP apps are installed

set -e

SITE="${1}"
BENCH="${2:-/home/stylo/stylo}"

cd "$BENCH"

echo "[Stylo BMS] Running migrate..."
bench --site "$SITE" migrate

echo "[Stylo BMS] Clearing cache..."
bench --site "$SITE" clear-cache

echo "[Stylo BMS] Post-install complete."
