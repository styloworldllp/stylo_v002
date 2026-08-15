# Styloworld — Full Project Context

## What This Is

**Styloworld** is a white-labeled, private fork of the Frappe/ERPNext ecosystem. It is branded as "Stylo" — never "Frappe". This repo (`styloworldllp/stylo_v002`) is the full bench monorepo containing all customized apps.

The local bench is at `/Users/bhanuprakashkandula/Desktop/Stylo_Code` (also mirrored at `/Users/bhanuprakashkandula/Desktop/Stylo_ecosystem` for the demo server ecosystem).

---

## CRITICAL RULES — READ FIRST

1. **NEVER use official frappe/erpnext GitHub repos.** Always use `styloworldllp/stylo_v002`.
2. **NEVER say "Frappe" in any user-visible string.** Always say "Stylo".
3. **Brain AI config is done via Brain Settings UI (API key).** No hardcoded Ollama URLs in scripts.
4. **Data never leaves the site.** 21 CFR Part 11 + GDPR compliant design only.
5. **All version numbers are Stylo v2.x.x**, not Frappe v15/v16.

---

## Stylo Module System — Client Site Deployment

Every client site is built from Stylo modules. **Stylo Core is always first.**
All other modules can be added at any time — even after the site is live.

| Module | Apps | Depends On | Purpose |
|---|---|---|---|
| Stylo Core | frappe, stylo_core | — | Base — required on every site |
| Stylo BMS | payments, erpnext, india_compliance | Core | ERP + India GST. Gantt built in. |
| Stylo HR | hrms | Core + BMS | HR & Payroll |
| Stylo CRM | crm | Core | Sales, leads, deals |
| Stylo Brain | brain | Core | AI assistant |
| Stylo Analytics | insights | Core | BI dashboards, self-serve reporting |
| Stylo LMS | lms | Core + payments* | Learning Management System |
| Stylo Lending | lending | Core + BMS | Loan management |
| Stylo Desk | telephony, helpdesk | Core | Customer support & ticketing |
| Stylo Reco | mint | Core (BMS recommended) | Bank reconciliation |

*LMS auto-installs payments if BMS is not already on the site.

### Scripts (in `stylo_modules/`)

```bash
# Create a new site
./stylo_modules/new_site.sh <sitename> <server> <module1> [module2] ...

# Add a module to an existing site (non-destructive — data is preserved)
./stylo_modules/add_module.sh <sitename> <server> <module>

# Examples
./stylo_modules/new_site.sh nhs2.stylo.io demo stylo_core
./stylo_modules/new_site.sh client.stylo.io demo stylo_core stylo_bms stylo_brain
./stylo_modules/new_site.sh full.stylo.io demo stylo_core stylo_bms stylo_hr stylo_crm stylo_brain stylo_analytics
./stylo_modules/add_module.sh nhs.stylo.io demo stylo_bms
./stylo_modules/add_module.sh client.stylo.io demo stylo_desk
```

See `stylo_modules/README.md` for full module reference and all site configurations.

---

## GitHub

- **Org**: `styloworldllp`
- **Token**: `GITHUB_TOKEN_IN_CLAUDE_SETTINGS`
- **Main repo**: `styloworldllp/stylo_v002`
- **Clone/push URL**: `https://GITHUB_TOKEN_IN_CLAUDE_SETTINGS@github.com/styloworldllp/stylo_v002.git`

Push command:
```bash
git push https://GITHUB_TOKEN_IN_CLAUDE_SETTINGS@github.com/styloworldllp/stylo_v002.git main
```

If push is rejected (diverged history), fetch + merge then push:
```bash
git fetch https://GITHUB_TOKEN_IN_CLAUDE_SETTINGS@github.com/styloworldllp/stylo_v002.git main
git merge FETCH_HEAD --no-edit
git push https://GITHUB_TOKEN_IN_CLAUDE_SETTINGS@github.com/styloworldllp/stylo_v002.git main
```

---

## GoDaddy DNS (stylo.io)

- **API Key**: `GODADDY_API_KEY_IN_CLAUDE_SETTINGS`
- **Secret**: `GODADDY_SECRET_IN_CLAUDE_SETTINGS`
- **Domain**: `stylo.io`

Add/update an A record:
```bash
curl -s -X PUT "https://api.godaddy.com/v1/domains/stylo.io/records/A/<subdomain>" \
  -H "Authorization: sso-key <GODADDY_API_KEY>:<GODADDY_SECRET>" \
  -H "Content-Type: application/json" \
  -d '[{"data": "<IP>", "ttl": 600}]'
```

---

## Servers

### demo.stylo.io — Primary Demo Server

| Field | Value |
|---|---|
| IP | `57.155.90.17` |
| Domain | `demo.stylo.io` |
| SSH user | `stylo` |
| SSH password | `stylo123Admin` |
| Bench root | `/home/stylo/stylo/` |
| Site name | `demo.stylo.io` |
| Admin password | `stylo123Admin` |
| Web service | `stylo-web.service` |
| MySQL root password | `stylo123Admin` |

```bash
# Connect
sshpass -p 'stylo123Admin' ssh -o StrictHostKeyChecking=no stylo@57.155.90.17

# Restart web
sudo systemctl restart stylo-web.service

# Build (must use NVM node 24)
source ~/.nvm/nvm.sh && nvm use 24 && cd /home/stylo/stylo && bench build --app frappe
```

**Ollama** is running at `http://localhost:11434` on this server.
- Models: `qwen2.5:1.5b`, `qwen2.5:3b`

### stangroup.stylo.io — Client Demo Server

| Field | Value |
|---|---|
| IP | `104.43.114.1` |
| Domain | `stangroup.stylo.io` |
| SSH user (frappe) | `frappe` / `stylo123Admin` |
| SSH user (admin) | `azureuser` / `stylo123Admin` |
| Bench root | `/home/frappe/stylo/` |
| Site name | `stangroup.stylo.io` |
| Admin password | `stylo123Admin` |
| Web service | `stangroup-web.service` |
| MySQL root password | `stylo123Admin` |

```bash
# Connect as frappe (bench commands)
sshpass -p 'stylo123Admin' ssh -o StrictHostKeyChecking=no frappe@104.43.114.1

# Connect as azureuser (sudo commands)
sshpass -p 'stylo123Admin' ssh -o StrictHostKeyChecking=no azureuser@104.43.114.1

# Restart web
sudo systemctl restart stangroup-web

# Build (node esbuild, NOT yarn/bench build — faster)
cd /home/frappe/stylo/apps/frappe && node esbuild --production --apps <appname>
```

**Systemd web service** (`/etc/systemd/system/stangroup-web.service`):
```ini
[Service]
User=frappe
WorkingDirectory=/home/frappe/stylo/sites
ExecStart=/home/frappe/stylo/env/bin/gunicorn \
  --bind 127.0.0.1:8000 --workers 2 --worker-class gthread \
  --threads 4 --timeout 120 --max-requests 5000 \
  --max-requests-jitter 500 frappe.app:application
Environment=PYTHONPATH=/home/frappe/stylo/apps/frappe
Environment=SITES_PATH=.
```

**Installed apps on stangroup** (`sites/apps.txt`):
```
frappe
erpnext
hrms
india_compliance
payments
stylo_core
crm
brain
```

---

## Local Bench (Stylo_Code)

- **Path**: `/Users/bhanuprakashkandula/Desktop/Stylo_Code`
- **Active site**: `stylo.localhost` (developer mode)
- **Startup**: `./start_bench.sh` → runs `bench start`
- **Processes**: web :8000, socketio :9000, watcher :6787, scheduler, workers

---

## App Structure (in `apps/`)

| App | Purpose |
|---|---|
| `frappe` | Core framework (white-labeled as Stylo) |
| `erpnext` | ERP — accounts, inventory, manufacturing |
| `hrms` | HR & Payroll |
| `crm` | CRM — leads, deals, field visits |
| `payments` | Razorpay, Stripe, PayTM, etc. |
| `india_compliance` | GST & Indian tax |
| `stylo_core` | Styloworld custom app — license, branding, marketplace |
| `brain` | AI assistant — local Ollama, 21 CFR compliant |
| `stylo_migrator` | Data migration tool |

---

## Branding — Where "Frappe" is Changed to "Stylo"

These files have already been fixed. If creating new sites or reverting, re-check:

| File | What was fixed |
|---|---|
| `apps/frappe/frappe/website/doctype/website_settings/website_settings.json` | `default: "Stylo"` for `app_name` field |
| `apps/frappe/frappe/core/doctype/system_settings/system_settings.json` | `default: "Stylo"` for `app_name` and `otp_issuer_name` |
| `apps/frappe/frappe/www/login.py` | Fallback `_("Stylo")` instead of `_("Frappe")` |
| `apps/frappe/frappe/www/desk.py` | `or "Stylo"` instead of `or "Frappe"` |
| `apps/frappe/frappe/twofactor.py` | OTP issuer → `"Stylo"` |
| `apps/frappe/frappe/email/doctype/email_account/email_account.py` | Default sender name → `"Stylo"` |
| `apps/frappe/frappe/hooks.py` | `app_email = "support@stylo.io"` |
| `apps/frappe/frappe/desk/doctype/changelog_feed/changelog_feed.py` | `get_feed()` returns `[]` (no external calls) |

**After creating a new site**, also run these in bench console to override any DB defaults:
```python
frappe.db.set_single_value('Website Settings', 'app_name', 'Stylo')
frappe.db.set_single_value('System Settings', 'app_name', 'Stylo')
frappe.db.set_single_value('System Settings', 'otp_issuer_name', 'Stylo')
frappe.db.commit()
```

---

## Deploying a New Site (Full Procedure)

```bash
# 1. Clone bench from private GitHub
git clone https://GITHUB_TOKEN_IN_CLAUDE_SETTINGS@github.com/styloworldllp/stylo_v002.git /home/frappe/stylo

# 2. Create Python virtualenv and install frappe
cd /home/frappe/stylo
python3 -m venv env
./env/bin/pip install -e apps/frappe

# 3. Create site
bench new-site <sitename> \
  --db-root-username root \
  --db-root-password <mysql_root_pw> \
  --admin-password stylo123Admin \
  --mariadb-user-host-login-scope='%'

# 4. Install apps (in order)
for app in payments erpnext hrms india_compliance crm brain stylo_core stylo_migrator; do
  bench --site <sitename> install-app $app
done

# 5. Fix app_name in DB
bench --site <sitename> execute frappe.db.set_single_value --args "['Website Settings','app_name','Stylo']"
bench --site <sitename> execute frappe.db.set_single_value --args "['System Settings','setup_complete',1]"

# 6. Install node deps for apps that have their own package.json
cd apps/erpnext && yarn install
cd ../../apps/frappe && yarn install

# 7. Build JS bundles (gitignored *.bundle.js files must be present — rsync from local if missing)
cd apps/frappe && node esbuild --production  # builds all apps

# 8. Clear cache
bench --site <sitename> clear-cache

# 9. Setup nginx + SSL + systemd (see stangroup config above as template)
#    IMPORTANT: web systemd unit alone is NOT enough — you MUST also create a
#    socketio systemd unit and an nginx /socket.io proxy block, or desk pages
#    will randomly freeze/hang (browser's socket.io client retries in a tight
#    loop against a dead port, saturating the ~6-connections-per-host limit
#    and starving real API calls). See "Socket.io Service — Required on Every
#    Site" below.
```

### Socket.io Service — Required on Every Site

Every production site needs a running socket.io process on `socketio_port`
(default `9000`, set in `sites/common_site_config.json`). Without it, the
browser's socket.io client fast-retries against a dead port forever, which
starves the browser's connection pool and makes desk pages (Customize Form,
DocType list, etc.) appear permanently stuck/frozen — this looks exactly like
a doctype-specific bug but isn't; it happens on every page equally.

Create `/etc/systemd/system/<sitename>-socketio.service` (adjust user/paths to
match the site's web service):

```ini
[Unit]
Description=<Site Name> Socket.IO Server
After=network.target

[Service]
User=frappe
WorkingDirectory=/home/frappe/stylo
ExecStart=/usr/bin/node apps/frappe/socketio.js
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now <sitename>-socketio.service
```

And add this nginx block alongside the site's other `location` blocks:

```nginx
location /socket.io {
    proxy_pass http://127.0.0.1:9000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

Verify with `sudo ss -tlnp | grep 9000` — must show the node process listening.

### Known issue: *.bundle.js files are gitignored

The `*.bundle.js` esbuild entry point files are gitignored and must be present for `bench build` to produce JS output. If a new server only has the git clone, rsync them from local:

```bash
for app in frappe erpnext hrms crm brain stylo_core; do
  sshpass -p 'stylo123Admin' rsync -avz \
    -e "ssh -o StrictHostKeyChecking=no" \
    --include="*.bundle.js" --include="*.bundle.ts" --include="*/" --exclude="*" \
    /Users/bhanuprakashkandula/Desktop/Stylo_Code/apps/$app/$app/public/ \
    frappe@<server_ip>:/home/frappe/stylo/apps/$app/$app/public/
done
```

---

## Deploy Code Update to Servers

### To demo.stylo.io:
```bash
# Rsync specific app
sshpass -p 'stylo123Admin' rsync -avz -e "ssh -o StrictHostKeyChecking=no" \
  /Users/bhanuprakashkandula/Desktop/Stylo_Code/apps/<app>/ \
  stylo@57.155.90.17:/home/stylo/stylo/apps/<app>/

# Migrate + build + restart
sshpass -p 'stylo123Admin' ssh -o StrictHostKeyChecking=no stylo@57.155.90.17 \
  "source ~/.nvm/nvm.sh && nvm use 24 && cd /home/stylo/stylo && \
   bench --site demo.stylo.io migrate && \
   bench build --app frappe && \
   sudo systemctl restart stylo-web.service"
```

### To stangroup.stylo.io:
```bash
# Pull from GitHub
sshpass -p 'stylo123Admin' ssh -o StrictHostKeyChecking=no frappe@104.43.114.1 \
  "cd /home/frappe/stylo && \
   git pull https://GITHUB_TOKEN_IN_CLAUDE_SETTINGS@github.com/styloworldllp/stylo_v002.git main"

# Migrate + build + restart
sshpass -p 'stylo123Admin' ssh -o StrictHostKeyChecking=no frappe@104.43.114.1 \
  "cd /home/frappe/stylo && source env/bin/activate && \
   bench --site stangroup.stylo.io migrate && \
   cd apps/frappe && node esbuild --production && cd ../.. && \
   bench --site stangroup.stylo.io clear-cache && \
   sudo systemctl restart stangroup-web"
```

---

## Brain AI App

- **Location**: `apps/brain/`
- **Module**: `brain/brain/`
- **Key files**:
  - `brain/brain/doctype/brain_settings/` — config: model, provider (Nuerix/Gemini), retention, audit toggle
  - `brain/brain/doctype/brain_chat_session/` — session tracking
  - `brain/brain/doctype/brain_chat_message/` — append-only messages, GDPR anonymizable
  - `brain/brain/doctype/brain_audit_log/` — immutable SHA256 hash-chained audit log (21 CFR)
  - `brain/ai/agent.py` — main AI agent, tool calls
  - `brain/ai/chat.py` — session create/resume, message logging
  - `brain/api/gdpr.py` — export and anonymize user data
  - `brain/public/js/brain.js` — frontend chat UI
- **Provider names**: "Nuerix" (Ollama local), "Gemini" (Google) — NOT "Ollama", NOT "Frappe"
- **Compliance**: All sessions stored in DB, audit log is immutable with SHA256 chaining, GDPR anonymization available, no external calls

---

## Stylo_Code vs Stylo_ecosystem

- `Stylo_Code` — the main local bench, used for development and as source of truth for GitHub pushes
- `Stylo_ecosystem` — a separate local copy used for the demo server ecosystem (brain, stylo_core pushed from here)
- Both should be kept in sync with GitHub

---

## User

- **Name**: Bhanu Prakash Kandula
- **Email**: kandulabhanuprakash12345@gmail.com
- **Role**: Founder/CTO of Styloworld
- **Style**: Prefers direct action over planning. Says "do it" means do it now. Very compliance-aware (21 CFR, GDPR).
