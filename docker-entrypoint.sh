#!/bin/bash
set -e

BENCH_DIR=/home/frappe/frappe-bench
SITES_DIR=$BENCH_DIR/sites
SITE_NAME=${SITE_NAME:-stylo.example.com}

# ── Generate common_site_config.json from env vars ───────────────────────────
cat > "$SITES_DIR/common_site_config.json" <<EOF
{
  "db_host": "${DB_HOST:-mariadb}",
  "db_port": ${DB_PORT:-3306},
  "redis_cache": "${REDIS_CACHE_URL:-redis://redis:6379/0}",
  "redis_queue": "${REDIS_QUEUE_URL:-redis://redis:6379/1}",
  "redis_socketio": "${REDIS_SOCKETIO_URL:-redis://redis:6379/2}",
  "server_script_enabled": 0,
  "socketio_port": 9000,
  "webserver_port": 8000,
  "file_watcher_port": 6787
}
EOF

# ── Generate per-site site_config.json ───────────────────────────────────────
mkdir -p "$SITES_DIR/$SITE_NAME"
cat > "$SITES_DIR/$SITE_NAME/site_config.json" <<EOF
{
  "db_name": "${DB_NAME}",
  "db_password": "${DB_PASSWORD}",
  "db_type": "mariadb",
  "encryption_key": "${ENCRYPTION_KEY:-}",
  "stylo_license_key": "${STYLO_LICENSE_KEY:-}"
}
EOF

# ── Set default site ──────────────────────────────────────────────────────────
echo "$SITE_NAME" > "$SITES_DIR/currentsite.txt"

# ── Wait for MariaDB to be ready ──────────────────────────────────────────────
echo "Waiting for MariaDB at ${DB_HOST:-mariadb}:${DB_PORT:-3306}..."
until mariadb-admin ping -h "${DB_HOST:-mariadb}" -P "${DB_PORT:-3306}" \
      -u root -p"${DB_ROOT_PASSWORD}" --silent 2>/dev/null; do
  sleep 2
done
echo "MariaDB ready."

# ── Run migrations on first run or when deploying updates ────────────────────
if [ "${RUN_MIGRATE:-true}" = "true" ]; then
  echo "Running bench migrate..."
  cd "$BENCH_DIR" && env/bin/bench --site "$SITE_NAME" migrate || true
fi

# ── Start the requested process ───────────────────────────────────────────────
cd "$BENCH_DIR"

case "$1" in
  web)
    exec env/bin/gunicorn \
      --bind 0.0.0.0:8000 \
      --worker-class gthread \
      --workers "${GUNICORN_WORKERS:-4}" \
      --threads "${GUNICORN_THREADS:-4}" \
      --timeout 120 \
      --log-file - \
      frappe.app:application
    ;;

  worker-short)
    exec env/bin/bench worker --queue short,default
    ;;

  worker-long)
    exec env/bin/bench worker --queue long,default
    ;;

  scheduler)
    exec env/bin/bench schedule
    ;;

  socketio)
    exec node apps/frappe/socketio.js
    ;;

  *)
    exec "$@"
    ;;
esac
