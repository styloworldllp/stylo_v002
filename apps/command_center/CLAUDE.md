# Stylo Command Center — App Context

## What This Is

Internal ops console for the Stylo team — **not a client-facing product**. Three roles:

- **Command Center Super Admin** — founding team. Approves Site Requests, sees Server credentials, manages licenses.
- **Command Center Admin** — employees. Create Site Requests for clients, see their own sites.
- **Command Center Support Staff** — support team. Read-only ticket rollup; actual ticket work happens in Helpdesk.

## Deployment Model — This App Is NOT in the `styloworldllp/stylo_v002` Git Repo

Deliberate decision: this app's source (doctypes, deployment automation, SSH-handling code)
stays **out of** the shared monorepo that every client server clones, so client-facing boxes
never carry Command Center's source. It is deployed as a **standalone folder**, synced by
direct `rsync`/`scp`, not `git pull`.

**Practical consequence**: if you're editing this app, do it either (a) on the local dev
bench at `/Users/bhanuprakashkandula/Desktop/Stylo_Code/apps/command_center` and manually
`rsync` changes out to the server, or (b) connect directly to the server hosting Command
Center via VS Code Remote-SSH + Claude Code and edit the deployed copy in place. Either way,
**do not add this folder to `styloworldllp/stylo_v002`** unless that decision is deliberately
revisited.

Platform-wide fixes discovered *while* working on this app (e.g. a bug in `apps/frappe` or
in `stylo_modules/*.sh`) are a different story — those DO belong in the shared repo and
should be committed/pushed normally, since they benefit every site, not just this one.

## Where It's Hosted

- **Site**: `console.stylo.io`
- **Server**: `demo` (`stylo@57.155.90.17`, bench `/home/stylo/stylo`, service `stylo-web.service`) — same physical server as `demo.stylo.io` and `nhs.stylo.io`, just a separate site on the same bench.
- Apps installed alongside it on this site: `frappe`, `stylo_core` (required — licensing doctypes live there), `telephony` + `helpdesk` (so the Support page's `HD Ticket` rollup has real local data to query).
- SSL: Let's Encrypt, `certbot certonly --nginx -d console.stylo.io`. Nginx block is in `/etc/nginx/sites-available/stylo` on that server (appended after the `nhs.stylo.io` block).

## Deploying a Change to the Live Instance

```bash
# From local dev bench (or directly on the server if editing in place)
sshpass -p 'stylo123Admin' rsync -avz --exclude 'node_modules' --exclude '__pycache__' --exclude '.git' \
  -e "ssh -o StrictHostKeyChecking=no" \
  apps/command_center/ \
  stylo@57.155.90.17:/home/stylo/stylo/apps/command_center/

# Backend-only change: just restart
sshpass -p 'stylo123Admin' ssh stylo@57.155.90.17 "sudo systemctl restart stylo-web.service"

# Doctype/schema change: migrate first
sshpass -p 'stylo123Admin' ssh stylo@57.155.90.17 \
  "cd /home/stylo/stylo && bench --site console.stylo.io migrate"

# Frontend change: build locally (apps/command_center/frontend && yarn build), then rsync
# the whole app again (the build writes into command_center/public/frontend/ and
# command_center/www/command_center.html, both inside this same folder) — do NOT try to
# run `yarn build` on the server itself unless you've confirmed its Node/nvm setup first
# (see gotchas below).
```

## Architecture

```
command_center/
├── command_center/
│   ├── command_center/doctype/     Server, Server Metric, Site, Site Request,
│   │                                Deploy Log, Command Center Settings, + 2 child tables
│   ├── api/
│   │   ├── site_request.py         approve/reject/retry — role-gated, enqueues deploy.py
│   │   ├── server.py                weighted selection algorithm + recommendation preview
│   │   ├── deploy.py                paramiko: run_deployment/add_module_to_site
│   │   ├── metrics.py               agent ingest endpoint (allow_guest + API key auth)
│   │   ├── dashboard.py             summary stats for the frontend home page
│   │   └── tickets.py               read-only HD Ticket rollup by site
│   ├── agent/command_center_agent.py   stdlib-only monitoring script, deployed to EVERY
│   │                                    managed server (see /opt/stylo/ on demo/stangroup)
│   ├── module_map.py                module_key -> [apps], mirrors stylo_modules/README.md
│   └── install.py                   after_install: adds HD Ticket.site custom field
└── frontend/                        Vue3 + frappe-ui SPA, mirrors apps/crm/frontend's build setup
```

`Site`/`Site Request` link to `stylo_core`'s existing `Stylo License`/`Stylo License Request`
doctypes — licensing logic is NOT duplicated here, `stylo_core` already owns it
(`license_api.py`, `license_management.py`).

## Server Onboarding (adding a new managed server)

1. Create a `Server` record (Super Admin only) — host, SSH user, `auth_method` +
   password/key, `bench_path`, `web_service_name`, `max_sites`, `hosting_type`.
2. Generate an `agent_api_key` on that record (any random string — used to authenticate
   the monitoring agent's metric pushes, not an SSH credential).
3. `scp` `command_center/agent/command_center_agent.py` to `/opt/stylo/command_center_agent.py`
   on the target server, and a matching `/opt/stylo/agent_config.json`:
   ```json
   {"server": "<Server.name>", "api_key": "<the agent_api_key you generated>",
    "endpoint": "https://console.stylo.io/api/method/command_center.api.metrics.ingest",
    "bench_path": "<Server.bench_path>"}
   ```
4. Add a cron entry: `*/3 * * * * /usr/bin/python3 /opt/stylo/command_center_agent.py >> /var/log/stylo_agent.log 2>&1`
5. Run it once manually first (`/usr/bin/python3 /opt/stylo/command_center_agent.py`) to confirm
   a `200 {"status": "ok"}` before relying on cron.

Currently onboarded: `demo` (57.155.90.17) and `stangroup` (104.43.114.1), both `hosting_type: Stylo-Managed`.

## Gotchas Hit During the Original Build (read before debugging something that "should just work")

- **`frappe.get_all(fields=[...])` rejects raw SQL function strings** in this Frappe
  version (e.g. `"count(name) as count"`) — throws `ValidationError: SQL functions are
  not allowed as strings in SELECT`. Tally in Python instead, or use the dict aggregate
  syntax (`{"COUNT": "name"}`) if you need it at scale.
- **`demo`'s nvm default was pinned to Node 16** — `bench build` spawns its yarn/esbuild
  subprocess with a stripped environment (`get_node_env()` in `frappe/build.py` only sets
  `NODE_OPTIONS`, nothing else), so an interactive `nvm use 24` in your SSH session does
  NOT carry through. Fix was `nvm alias default 24` on that server — if builds start
  failing with a Node version complaint again, check `nvm alias default` first.
- **`stylo_modules/new_site.sh`/`add_module.sh` had a real bug** (fixed upstream, commit
  `a213b3a`): `ssh` inside the `while read APP < apps.txt` loop would consume the *next*
  unread line of `apps.txt` as if it were input to the remote command, silently skipping
  every app after the first in any multi-app module. Already fixed in the shared repo —
  if you're running an old checkout, `git pull` first.
- **`helpdesk`'s search indexing needs `nltk`**, not declared as a dependency anywhere —
  `env/bin/pip install nltk` if a migrate fails on `helpdesk.search.download_corpus`.
- **macOS ships bash 3.2**; the shared deploy scripts use `declare -A` (bash 4+). Use
  `/opt/homebrew/bin/bash` (`brew install bash`) if running them from a Mac.

## Relationship to Stylo Licensing (V1.0)

Command Center does **not** implement licensing logic — that lives entirely in `stylo_core`
(shared, git-tracked, installed on every site). Command Center only surfaces it:

- `Licenses.vue` reads `stylo_core`'s `Stylo License`/`Stylo License Module` via
  `command_center/api/licenses.py` (a dedicated whitelisted method, not a generic
  `frappe.client.get_list` call — that REST endpoint needs `DocType`-meta read access that
  Command Center Admin/Super Admin don't have, and shouldn't need for this).
- `SiteRequests.vue`'s **"Declare Demo/POC"** button (visible once a request is `Deployed`)
  calls `stylo_core.license_management.release_demo_license` — creates a `Stylo License` with
  `status="Demo"` directly (no payment, no `Stylo License Request`), giving that site
  effectively-unlimited access via `stylo_core`'s existing Demo-status bypass. Converting a
  Demo license to a paid one later is a `status` field flip on the `Stylo License` record
  itself (done from the license record, not from Command Center) — zero data migration by
  design.
- The three Command Center roles are structurally separate from `stylo_core`'s customer-side
  `Stylo License Administrator` role — Command Center operates *above* customer licensing
  (can issue/modify any site's `Stylo License`), the customer-side role operates *within* a
  single site's license (view inventory, assign tiers, disable users — never touches
  commercial terms or issues licenses itself).

## Not Yet Built

- **Phase 7 (Client-Premise hardened deployment)** — bytecode/Cython packaging + Docker +
  offline license signing for clients whose own IT holds root. Deliberately deferred until
  an actual client-premise deal exists; see the original planning conversation for the full
  design if/when it's needed.
- Azure-specific integration (metrics via Azure Monitor API, or auto-provisioning new Azure
  VMs) — discussed and explicitly deferred, not started.
- Retroactive import of existing sites (demo.stylo.io, nhs.stylo.io, stangroup.stylo.io) as
  tracked `Site` records — Command Center currently only tracks sites created through it
  going forward.
