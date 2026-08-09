#!/bin/bash
# ============================================================
# new_site.sh — Create a new Stylo site and install modules
# ============================================================
# Usage:
#   ./stylo_modules/new_site.sh <sitename> <server> <module1> [module2] ...
#
# Servers:
#   demo       — stylo@57.155.90.17     bench: /home/stylo/stylo
#   stangroup  — frappe@104.43.114.1    bench: /home/frappe/stylo
#
# Modules (install in this order):
#   stylo_core    — always first
#   stylo_bms     — ERP (payments + erpnext + india_compliance)
#   stylo_hr      — HR & Payroll (requires stylo_bms)
#   stylo_crm     — CRM
#   stylo_brain   — AI assistant
#
# Examples:
#   ./stylo_modules/new_site.sh nhs2.stylo.io demo stylo_core
#   ./stylo_modules/new_site.sh client.stylo.io demo stylo_core stylo_bms stylo_brain
#   ./stylo_modules/new_site.sh full.stylo.io demo stylo_core stylo_bms stylo_hr stylo_crm stylo_brain
# ============================================================

set -e

# ---------- Server config ----------
declare -A SERVER_USER=( [demo]="stylo" [stangroup]="frappe" )
declare -A SERVER_IP=( [demo]="57.155.90.17" [stangroup]="104.43.114.1" )
declare -A SERVER_BENCH=( [demo]="/home/stylo/stylo" [stangroup]="/home/frappe/stylo" )
declare -A SERVER_SERVICE=( [demo]="stylo-web.service" [stangroup]="stangroup-web" )
SSH_PASS="stylo123Admin"
DB_ROOT_PASS="stylo123Admin"
ADMIN_PASS="stylo123Admin"

# ---------- Args ----------
SITE="$1"
SERVER="$2"
shift 2
MODULES=("$@")

# ---------- Validate ----------
if [ -z "$SITE" ] || [ -z "$SERVER" ] || [ ${#MODULES[@]} -eq 0 ]; then
  echo "Usage: $0 <sitename> <server> <module1> [module2] ..."
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

echo "============================================================"
echo "  Stylo New Site: $SITE"
echo "  Server: $SERVER ($USER@$IP)"
echo "  Bench: $BENCH"
echo "  Modules: ${MODULES[*]}"
echo "============================================================"

SSH="sshpass -p '$SSH_PASS' ssh -o StrictHostKeyChecking=no $USER@$IP"

# ---------- Step 1: Create site ----------
echo ""
echo ">>> [1/3] Creating site $SITE ..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$USER@$IP" \
  "cd $BENCH && bench new-site '$SITE' \
    --db-root-username root \
    --db-root-password '$DB_ROOT_PASS' \
    --admin-password '$ADMIN_PASS' \
    --mariadb-user-host-login-scope='%'"

# ---------- Step 2: Install modules ----------
echo ""
echo ">>> [2/3] Installing modules ..."

for MODULE in "${MODULES[@]}"; do
  MODULE_DIR="$SCRIPT_DIR/$MODULE"

  if [ ! -f "$MODULE_DIR/apps.txt" ]; then
    echo "ERROR: Unknown module '$MODULE' — no apps.txt found at $MODULE_DIR/apps.txt"
    exit 1
  fi

  echo ""
  echo "  --- Installing module: $MODULE ---"

  # Read apps and install each
  while IFS= read -r APP || [ -n "$APP" ]; do
    APP="$(echo "$APP" | tr -d '[:space:]')"
    [ -z "$APP" ] && continue
    echo "  Installing app: $APP"
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$USER@$IP" \
      "cd $BENCH && bench --site '$SITE' install-app '$APP'"
  done < "$MODULE_DIR/apps.txt"

  # Run post_install on the server by copying and executing
  echo "  Running post_install for $MODULE..."
  sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no \
    "$MODULE_DIR/post_install.sh" "$USER@$IP:/tmp/stylo_post_install_$MODULE.sh"
  sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$USER@$IP" \
    "chmod +x /tmp/stylo_post_install_$MODULE.sh && \
     /tmp/stylo_post_install_$MODULE.sh '$SITE' '$BENCH' && \
     rm /tmp/stylo_post_install_$MODULE.sh"
done

# ---------- Step 3: Restart service ----------
echo ""
echo ">>> [3/3] Restarting web service: $SERVICE ..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$USER@$IP" \
  "sudo systemctl restart $SERVICE"

echo ""
echo "============================================================"
echo "  Done! Site is live at: https://$SITE"
echo "  Admin login: Administrator / $ADMIN_PASS"
echo "============================================================"
