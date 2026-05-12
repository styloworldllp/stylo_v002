#!/bin/bash
# Local development startup — portable, no hardcoded paths.
# For macOS with Homebrew MariaDB, add Homebrew to PATH first if needed.
set -e

BENCH_DIR="$(cd "$(dirname "$0")" && pwd)"
BENCH="$BENCH_DIR/env/bin/bench"
SITE="${SITE_NAME:-stylo.localhost}"

cd "$BENCH_DIR"

"$BENCH" use "$SITE"
exec "$BENCH" start
