#!/bin/bash
# Stylo Brain post-install — installs app and migrates
# AI provider and API key are configured via Brain Settings in the UI after install

set -e

SITE="${1}"
BENCH="${2:-/home/stylo/stylo}"

cd "$BENCH"
# bench isn't guaranteed to be on PATH in a non-interactive SSH shell (confirmed missing on stangroup)
export PATH="$BENCH/env/bin:$PATH"

echo "[Stylo Brain] Running migrate..."
bench --site "$SITE" migrate

echo "[Stylo Brain] Clearing cache..."
bench --site "$SITE" clear-cache

echo "[Stylo Brain] Post-install complete."
echo "[Stylo Brain] NOTE: Configure AI provider and API key via Brain Settings in the desk UI."
