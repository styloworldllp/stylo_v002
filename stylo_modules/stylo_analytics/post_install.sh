#!/bin/bash
# Stylo Analytics post-install (insights)

set -e

SITE="${1}"
BENCH="${2:-/home/stylo/stylo}"

cd "$BENCH"
# bench isn't guaranteed to be on PATH in a non-interactive SSH shell (confirmed missing on stangroup)
export PATH="$BENCH/env/bin:$PATH"

echo "[Stylo Analytics] Running migrate..."
bench --site "$SITE" migrate

echo "[Stylo Analytics] Clearing cache..."
bench --site "$SITE" clear-cache

echo "[Stylo Analytics] Post-install complete."
echo "[Stylo Analytics] Access at: https://$SITE/insights"
