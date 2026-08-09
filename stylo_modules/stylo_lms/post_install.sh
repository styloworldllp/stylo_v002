#!/bin/bash
# Stylo LMS post-install
# LMS requires the payments app. If BMS is installed, payments is already there.
# If not, this script installs payments first automatically.

set -e

SITE="${1}"
BENCH="${2:-/home/stylo/stylo}"

cd "$BENCH"

echo "[Stylo LMS] Checking prerequisite: payments app..."
PAYMENTS_INSTALLED=$(bench --site "$SITE" list-apps 2>/dev/null | grep "^payments$" || true)
if [ -z "$PAYMENTS_INSTALLED" ]; then
  echo "[Stylo LMS] payments not found — installing it as prerequisite..."
  bench --site "$SITE" install-app payments
fi

echo "[Stylo LMS] Running migrate..."
bench --site "$SITE" migrate

echo "[Stylo LMS] Clearing cache..."
bench --site "$SITE" clear-cache

echo "[Stylo LMS] Post-install complete."
echo "[Stylo LMS] Access at: https://$SITE/lms"
