FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# ── License secret — injected at build time, never visible at runtime ─────────
# Build with: docker build --build-arg STYLO_BUILD_SECRET=your-secret .
ARG STYLO_BUILD_SECRET
ENV STYLO_BUILD_SECRET=${STYLO_BUILD_SECRET}

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    git curl wget \
    mariadb-client \
    libmariadb-dev \
    wkhtmltopdf \
    xvfb \
    libssl-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libxml2-dev \
    libxslt1-dev \
    redis-tools \
    gettext-base \
    supervisor \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js 18 ────────────────────────────────────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g yarn \
    && rm -rf /var/lib/apt/lists/*

# ── Create frappe user ────────────────────────────────────────────────────────
RUN useradd -ms /bin/bash frappe
WORKDIR /home/frappe/frappe-bench
RUN chown -R frappe:frappe /home/frappe

USER frappe

# ── Python virtualenv ─────────────────────────────────────────────────────────
RUN python3 -m venv env

# ── Install bench CLI ─────────────────────────────────────────────────────────
RUN env/bin/pip install --quiet frappe-bench

# ── Create bench structure ────────────────────────────────────────────────────
RUN mkdir -p apps sites logs config

# ── Copy apps source (from build context) ────────────────────────────────────
# Apps are copied from the repo — no git clone at image build time.
# This keeps the image build reproducible and fast.
COPY --chown=frappe:frappe apps/ apps/

# ── Install Python packages for all apps ─────────────────────────────────────
RUN env/bin/pip install --quiet -e apps/frappe \
    && env/bin/pip install --quiet -e apps/erpnext \
    && env/bin/pip install --quiet -e apps/payments \
    && env/bin/pip install --quiet -e apps/hrms \
    && env/bin/pip install --quiet -e apps/lms \
    && env/bin/pip install --quiet -e apps/crm \
    && env/bin/pip install --quiet -e apps/helpdesk \
    && env/bin/pip install --quiet -e apps/gameplan \
    && env/bin/pip install --quiet -e apps/telephony \
    && env/bin/pip install --quiet -e apps/india_compliance \
    && env/bin/pip install --quiet -e apps/stylo_core \
    && env/bin/pip install --quiet -e apps/brain

# ── Protect stylo_core source — compile to .pyc, delete .py ─────────────────
# Frappe uses importlib which supports .pyc without .py source files.
# -b flag writes .pyc files next to the source before we delete .py.
RUN env/bin/python -m compileall -b -q apps/stylo_core/ \
    && find apps/stylo_core -name "*.py" -delete \
    && find apps/stylo_core -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ── Install Node deps and build frontend assets ───────────────────────────────
COPY --chown=frappe:frappe sites/apps.txt sites/apps.txt

RUN cd apps/frappe && yarn install --frozen-lockfile --silent 2>/dev/null || yarn install --silent
RUN cd apps/crm/frontend && yarn install --frozen-lockfile --silent 2>/dev/null || yarn install --silent
RUN cd apps/helpdesk/desk && yarn install --frozen-lockfile --silent 2>/dev/null || yarn install --silent
RUN cd apps/lms/frontend && yarn install --frozen-lockfile --silent 2>/dev/null || yarn install --silent

# Build all app assets
RUN FRAPPE_BENCH_ROOT=/home/frappe/frappe-bench \
    env/bin/python apps/frappe/frappe/build.py \
    && env/bin/bench build --app crm \
    && env/bin/bench build --app helpdesk \
    && env/bin/bench build --app lms \
    && env/bin/bench build --app stylo_core \
    && env/bin/bench build --app brain

# ── Copy sites config template (entrypoint generates actual config from env vars) ──
COPY --chown=frappe:frappe sites/common_site_config.json sites/common_site_config.json.template

# ── Copy entrypoint and gunicorn config ──────────────────────────────────────
COPY --chown=frappe:frappe docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --chown=frappe:frappe gunicorn.conf.py gunicorn.conf.py

USER root
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
USER frappe

EXPOSE 8000 9000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["web"]
