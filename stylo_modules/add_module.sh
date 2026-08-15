#!/bin/bash
# ============================================================
# add_module.sh — Add a Stylo module to an existing site
# ============================================================
# Usage:
#   ./stylo_modules/add_module.sh <sitename> <server> <module>
#
# Examples:
#   ./stylo_modules/add_module.sh nhs.stylo.io demo stylo_bms
#   ./stylo_modules/add_module.sh client.stylo.io demo stylo_crm
#   ./stylo_modules/add_module.sh client.stylo.io demo stylo_brain
# ============================================================

set -e

# Requires bash 4+ (associative arrays). macOS ships bash 3.2 by default —
# run this with a modern bash (e.g. `brew install bash` and use /opt/homebrew/bin/bash).
if [ "${BASH_VERSINFO:-0}" -lt 4 ]; then
  echo "ERROR: this script needs bash 4+ (found ${BASH_VERSION:-unknown})." >&2
  echo "  On macOS: brew install bash && /opt/homebrew/bin/bash $0 \"\$@\"" >&2
  exit 1
fi

# ---------- Server config ----------
declare -A SERVER_USER=( [demo]="stylo" [stangroup]="frappe" )
declare -A SERVER_IP=( [demo]="57.155.90.17" [stangroup]="104.43.114.1" )
declare -A SERVER_BENCH=( [demo]="/home/stylo/stylo" [stangroup]="/home/frappe/stylo" )
declare -A SERVER_SERVICE=( [demo]="stylo-web.service" [stangroup]="stangroup-web" )
SSH_PASS="stylo123Admin"

# ---------- Args ----------
SITE="$1"
SERVER="$2"
MODULE="$3"

# ---------- Validate ----------
if [ -z "$SITE" ] || [ -z "$SERVER" ] || [ -z "$MODULE" ]; then
  echo "Usage: $0 <sitename> <server> <module>"
  echo "Servers: demo | stangroup"
  echo "Modules: stylo_core stylo_bms stylo_hr stylo_crm stylo_brain"
  exit 1
fi

if [ -z "${SERVER_USER[$SERVER]}" ]; then
  echo "ERROR: Unknown server '$SERVER'. Valid: demo | stangroup"
  exit 1
fi

USER="${SERVER_USER[$SERVER]}"
IP="${SERVER_IP[$SERVER]}"
BENCH="${SERVER_BENCH[$SERVER]}"
SERVICE="${SERVER_SERVICE[$SERVER]}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODULE_DIR="$SCRIPT_DIR/$MODULE"

if [ ! -f "$MODULE_DIR/apps.txt" ]; then
  echo "ERROR: Unknown module '$MODULE' — no apps.txt at $MODULE_DIR/apps.txt"
  exit 1
fi

echo "============================================================"
echo "  Add Module: $MODULE → $SITE"
echo "  Server: $SERVER ($USER@$IP)"
echo "============================================================"

# ---------- Install apps ----------
echo ""
echo ">>> Installing apps for module: $MODULE ..."
while IFS= read -r APP || [ -n "$APP" ]; do
  APP="$(echo "$APP" | tr -d '[:space:]')"
  [ -z "$APP" ] && continue
  echo "  Installing: $APP"
  sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$USER@$IP" \
    "cd $BENCH && bench --site '$SITE' install-app '$APP'" < /dev/null
done < "$MODULE_DIR/apps.txt"

# ---------- Post-install ----------
echo ""
echo ">>> Running post_install for $MODULE ..."
sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no \
  "$MODULE_DIR/post_install.sh" "$USER@$IP:/tmp/stylo_post_install_$MODULE.sh"
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$USER@$IP" \
  "chmod +x /tmp/stylo_post_install_$MODULE.sh && \
   /tmp/stylo_post_install_$MODULE.sh '$SITE' '$BENCH' && \
   rm /tmp/stylo_post_install_$MODULE.sh" < /dev/null

# ---------- Restart ----------
echo ""
echo ">>> Restarting $SERVICE ..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$USER@$IP" \
  "sudo systemctl restart $SERVICE" < /dev/null

echo ""
echo "============================================================"
echo "  Module $MODULE added to https://$SITE"
echo "============================================================"
