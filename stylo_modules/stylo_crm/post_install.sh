#!/bin/bash
# Stylo CRM post-install

set -e

SITE="${1}"
BENCH="${2:-/home/stylo/stylo}"

cd "$BENCH"

echo "[Stylo CRM] Running migrate..."
bench --site "$SITE" migrate

echo "[Stylo CRM] Clearing cache..."
bench --site "$SITE" clear-cache

echo "[Stylo CRM] Post-install complete."
