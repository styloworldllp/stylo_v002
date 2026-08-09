#!/bin/bash
# Stylo Core post-install — sets Stylo branding, favicon, workspace icons
# Called by new_site.sh / add_module.sh with SITE and BENCH_ROOT already set

set -e

SITE="${1}"
BENCH="${2:-/home/stylo/stylo}"

cd "$BENCH"

echo "[Stylo Core] Running migrate..."
bench --site "$SITE" migrate

echo "[Stylo Core] Setting Stylo branding..."
bench --site "$SITE" execute frappe.db.set_single_value \
  --args "['Website Settings','app_name','Stylo']"
bench --site "$SITE" execute frappe.db.set_single_value \
  --args "['System Settings','app_name','Stylo']"
bench --site "$SITE" execute frappe.db.set_single_value \
  --args "['System Settings','otp_issuer_name','Stylo']"
bench --site "$SITE" execute frappe.db.set_single_value \
  --args "['System Settings','setup_complete','1']"

echo "[Stylo Core] Setting Stylo favicon..."
bench --site "$SITE" execute frappe.db.set_single_value \
  --args "['Website Settings','favicon','/assets/stylo_core/images/stylo-favicon.svg']"

echo "[Stylo Core] Committing DB..."
bench --site "$SITE" execute frappe.db.commit

echo "[Stylo Core] Installing workspace icons..."
bench --site "$SITE" execute stylo_core.install_icons.run

echo "[Stylo Core] Clearing cache..."
bench --site "$SITE" clear-cache

echo "[Stylo Core] Post-install complete."
