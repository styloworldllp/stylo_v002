"""
Paramiko-based deployment automation — replaces stylo_modules/new_site.sh and add_module.sh
for Stylo-Managed servers (plan §4). Runs inside an RQ background worker (frappe.enqueue).

Not used for Server.hosting_type == "Client-Premise" — that flow builds a handoff artifact
instead (plan §10, Phase 7), since Command Center has no standing SSH access to a box it
doesn't control.

Each step is logged to Deploy Log for audit/visibility as it happens, and the job halts on
the first failing step rather than continuing in a possibly-broken state.
"""

import os
import shlex

import frappe
from frappe.utils import get_bench_path, now_datetime
from frappe.utils.password import get_decrypted_password

from command_center.module_map import resolve_apps

SUPER_ADMIN_ROLE = "Command Center Super Admin"


class DeploymentError(Exception):
	pass


def _bench_prefix(bench_path):
	"""`bench` isn't guaranteed to be on PATH in a non-interactive SSH shell — confirmed
	missing entirely on stangroup (`bash: bench: command not found`, exit 127) even though
	the same command works fine on demo, which has it symlinked into /usr/local/bin. Every
	managed server's venv always has it at env/bin/bench relative to bench_path though, so
	put that on PATH explicitly rather than depending on each server's shell setup."""
	return f"cd {bench_path} && PATH={bench_path}/env/bin:$PATH"


def _log(site_request: str | None, site: str | None, step: str, output: str, success: bool):
	# ignore_links=True: several steps (create_site, and every step of import_existing_site
	# before its Site record is inserted) log against a sitename that doesn't have a Site
	# doc yet — Deploy Log's `site`/`site_request` are Link fields, so without this the
	# insert throws LinkValidationError and the whole deployment silently dies on its very
	# first logged step. Pure audit trail, doesn't need referential integrity at insert time.
	doc = frappe.get_doc(
		{
			"doctype": "Deploy Log",
			"site_request": site_request,
			"site": site,
			"timestamp": now_datetime(),
			"step": step,
			"output": output,
			"success": 1 if success else 0,
		}
	)
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()


def _get_ssh_client(server_doc):
	import paramiko

	client = paramiko.SSHClient()
	# Host key pinning is left as a follow-up hardening item; at minimum this logs
	# unrecognized hosts rather than silently trusting like the old sshpass scripts
	# did with StrictHostKeyChecking=no.
	client.set_missing_host_key_policy(paramiko.WarningPolicy())
	client.load_system_host_keys()

	connect_kwargs = {
		"hostname": server_doc.host,
		"port": server_doc.ssh_port or 22,
		"username": server_doc.ssh_user,
		"timeout": 30,
	}

	if server_doc.auth_method == "Password":
		connect_kwargs["password"] = get_decrypted_password("Server", server_doc.name, "ssh_password")
	else:
		import io

		key_str = get_decrypted_password("Server", server_doc.name, "ssh_key", raise_exception=False)
		if not key_str:
			raise DeploymentError(f"No SSH key configured for server {server_doc.name}")
		passphrase = get_decrypted_password(
			"Server", server_doc.name, "ssh_key_passphrase", raise_exception=False
		)
		pkey = paramiko.RSAKey.from_private_key(io.StringIO(key_str), password=passphrase or None)
		connect_kwargs["pkey"] = pkey

	client.connect(**connect_kwargs)
	return client


def _run_step(client, site_request_name, site_name, step_name, cmd):
	stdin, stdout, stderr = client.exec_command(cmd)
	exit_code = stdout.channel.recv_exit_status()
	out = stdout.read().decode(errors="replace")
	err = stderr.read().decode(errors="replace")
	output = f"$ {cmd}\n\n--- stdout ---\n{out}\n--- stderr ---\n{err}"
	success = exit_code == 0

	_log(site_request_name, site_name, step_name, output, success)

	if not success:
		raise DeploymentError(f"Step '{step_name}' failed (exit {exit_code}): {err[:500]}")

	return out


def _sftp_and_run_post_install(client, module_key, site, bench_path, site_request_name):
	local_path = os.path.join(get_bench_path(), "stylo_modules", module_key, "post_install.sh")
	if not os.path.exists(local_path):
		# Not every module ships a post_install.sh — treat as a no-op step.
		return

	remote_path = f"/tmp/stylo_post_install_{module_key}.sh"
	sftp = client.open_sftp()
	try:
		sftp.put(local_path, remote_path)
	finally:
		sftp.close()

	_run_step(
		client,
		site_request_name,
		site,
		f"post_install:{module_key}",
		f"chmod +x {remote_path} && {remote_path} '{site}' '{bench_path}' && rm -f {remote_path}",
	)


def _ensure_app_source_ready(client, bench_path, app, site_request_name, site_name):
	"""Makes an app's source actually usable on this bench before install-app runs — covers
	a real gap hit live on stangroup: telephony/helpdesk's source was cloned into apps/ (it's
	one repo, every app's folder is always there) but neither had ever been pip-installed
	into that server's venv nor registered in sites/apps.txt (both normally handled by
	`bench get-app`, which nothing in this automation calls since it assumes that already
	happened). Symptom without this: install-app fails first with `ModuleNotFoundError`,
	then — after fixing that by hand — with `App X not in apps.txt`. Every check here is
	idempotent (`pip show` / `grep -qx` first) so this is a fast no-op on a server that
	already has the app ready, and self-heals a server that doesn't — this must work
	"any time on any site" without needing a manual SSH pass first.

	Deeper gap also hit live: `lending`'s app folder didn't exist on demo's bench at all —
	it had never been pushed to styloworldllp/stylo_v002 in the first place (fixed
	separately by committing it), but even once it's in the shared repo, a server only gets
	it on its next `git pull`. The check below covers that — if the app folder is missing
	outright, pull first (the bench's own `origin` remote already carries stored
	credentials from its initial clone, so no token needs to live in this source file)."""
	_run_step(
		client, site_request_name, site_name, f"ensure_app_cloned:{app}",
		f"[ -d '{bench_path}/apps/{app}' ] || (cd {bench_path} && git pull origin main)",
	)
	_run_step(
		client, site_request_name, site_name, f"ensure_pip:{app}",
		f"{bench_path}/env/bin/pip show {app} >/dev/null 2>&1 || "
		f"{bench_path}/env/bin/pip install -e {bench_path}/apps/{app}",
	)
	_run_step(
		client, site_request_name, site_name, f"ensure_apps_txt:{app}",
		f"grep -qx '{app}' {bench_path}/sites/apps.txt || echo '{app}' >> {bench_path}/sites/apps.txt",
	)


def _ensure_app_assets_ready(client, bench_path, app, site_request_name, site_name):
	"""Post-install-app: makes sure the app's frontend is actually reachable, covering two
	more gaps hit live on stangroup for `helpdesk` (same class of app as crm/lms/mint/
	insights — a standalone Vue SPA in a frontend/ or desk/ folder, built with its own yarn
	build rather than Frappe's own esbuild, per apps/command_center/CLAUDE.md's existing CRM
	Frontend Build gotcha):
	  1. `sites/assets/<app>` is a symlink to `apps/<app>/<app>/public` that `bench build`
	     normally creates the first time it runs for that app — never happened here since
	     this automation never runs `bench build`. Without it, every asset the built SPA
	     references 404s even though the page itself loads.
	  2. The SPA itself was simply never built (no apps/<app>/<app>/public/<dirname>/
	     index.html) — `/`<app>` 404s outright.
	Both checks are idempotent (test for the symlink / for the build output marker file
	before doing anything), so this is a fast no-op everywhere it's already done."""
	public_dir = f"{bench_path}/apps/{app}/{app}/public"
	assets_link = f"{bench_path}/sites/assets/{app}"
	_run_step(
		client, site_request_name, site_name, f"ensure_assets_link:{app}",
		f"[ ! -d '{public_dir}' ] || [ -e '{assets_link}' ] || ln -s '{public_dir}' '{assets_link}'",
	)
	for dirname in ("frontend", "desk"):
		src = f"{bench_path}/apps/{app}/{dirname}"
		marker = f"{public_dir}/{dirname}/index.html"
		_run_step(
			client, site_request_name, site_name, f"ensure_frontend_built:{app}:{dirname}",
			f"[ ! -f '{src}/package.json' ] || [ -f '{marker}' ] || "
			f"(cd '{src}' && yarn install && yarn build)",
		)


def _ensure_dns_record(site_name, host_ip, site_request_name):
	"""Points <site_name>'s DNS A record at the server it was actually deployed to. Confirmed
	live as a real gap: a site created on `stangroup` had its DNS still resolving to `demo`'s
	IP (from an old/manual record, or never set at all) — the nginx vhost and SSL cert were
	provisioned correctly ON stangroup, but nothing on the public internet, including Let's
	Encrypt's own HTTP-01 validator, could ever reach it there, so cert issuance failed with
	a confusing "Invalid response" pointing at demo.stylo.io (demo's own fallback vhost is
	what the validator actually hit). Must run — and be given time to propagate — before
	_setup_nginx_ssl's certbot step.

	Credentials come from Command Center Settings (Password fields), not this source file —
	command_center is git-tracked now, so anything hardcoded here would leak into git
	history."""
	import time

	import requests

	settings = frappe.get_cached_doc("Command Center Settings")
	domain = settings.godaddy_domain or "stylo.io"
	api_key = get_decrypted_password(
		"Command Center Settings", "Command Center Settings", "godaddy_api_key", raise_exception=False
	)
	api_secret = get_decrypted_password(
		"Command Center Settings", "Command Center Settings", "godaddy_api_secret", raise_exception=False
	)
	if not api_key or not api_secret:
		raise DeploymentError(
			"GoDaddy API key/secret not configured in Command Center Settings — cannot "
			"point this site's DNS at its server."
		)

	if not site_name.endswith(f".{domain}"):
		raise DeploymentError(
			f"Site {site_name} is not under the configured DNS domain ({domain}) — "
			f"set up its DNS manually."
		)
	subdomain = site_name[: -(len(domain) + 1)]

	resp = requests.put(
		f"https://api.godaddy.com/v1/domains/{domain}/records/A/{subdomain}",
		headers={
			"Authorization": f"sso-key {api_key}:{api_secret}",
			"Content-Type": "application/json",
		},
		json=[{"data": host_ip, "ttl": 600}],
		timeout=30,
	)
	output = f"PUT A record {subdomain}.{domain} -> {host_ip}\nstatus: {resp.status_code}\n{resp.text}"
	success = resp.status_code < 300
	_log(site_request_name, site_name, "dns_record", output, success)
	if not success:
		raise DeploymentError(f"Step 'dns_record' failed: {resp.status_code} {resp.text[:500]}")

	# Give GoDaddy's own nameservers a moment to actually start answering the new value —
	# without this, certbot's very next step can still race a stale/absent answer.
	time.sleep(30)


def _setup_nginx_ssl(client, site_name, bench_path, site_request_name):
	"""Provisions a real public vhost for a newly created site. `bench new-site` only creates
	the Frappe-level site (DB + site folder) — without this, a request to the new domain has
	no matching nginx server block. Confirmed live: on a shared server (demo/nhs/console all
	behind one nginx, one shared `/etc/nginx/sites-available/stylo` file), an unmatched
	HTTPS SNI falls through to whichever server block nginx treats as the implicit default
	for that listen socket — here, demo.stylo.io's block, which has a *hardcoded*
	`location = / { return 302 https://demo.stylo.io/desk; }`. So a freshly "created" site
	just silently redirected to demo.stylo.io — nothing was actually serving it.

	Written to its own file under conf.d/ rather than appended into the shared
	sites-available/stylo file every other site lives in, so a bad render here can only ever
	break this one site's own file — never the already-working shared config. `nginx -t`
	gates every reload; if a render is ever wrong, this fails loudly as a Deploy Log step
	instead of silently corrupting nginx for demo/nhs/console too.

	Two-phase because the SSL cert doesn't exist yet when we need an HTTP vhost for certbot's
	nginx authenticator to attach the ACME challenge to."""
	conf_path = f"/etc/nginx/conf.d/{site_name}.conf"
	tmp_path = f"/tmp/nginx_{site_name}.conf"

	http_only = f"""server {{
    listen 80;
    server_name {site_name};
    location / {{
        return 301 https://$host$request_uri;
    }}
}}
"""
	sftp = client.open_sftp()
	try:
		with sftp.open(tmp_path, "w") as f:
			f.write(http_only)
	finally:
		sftp.close()

	_run_step(
		client, site_request_name, site_name, "nginx_http_only",
		f"sudo mv {tmp_path} {conf_path} && sudo nginx -t && sudo systemctl reload nginx",
	)

	_run_step(
		client, site_request_name, site_name, "issue_ssl_cert",
		f"sudo certbot certonly --nginx -d {site_name} --non-interactive --agree-tos "
		f"-m support@stylo.io",
	)

	full_conf = f"""server {{
    listen 80;
    server_name {site_name};
    return 301 https://$host$request_uri;
}}
server {{
    listen 443 ssl;
    server_name {site_name};
    ssl_certificate /etc/letsencrypt/live/{site_name}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{site_name}/privkey.pem;
    client_max_body_size 100m;

    location = / {{
        return 302 https://{site_name}/desk;
    }}

    location /assets {{
        alias {bench_path}/sites/assets;
        expires 30d;
        add_header Cache-Control "public, immutable";
        try_files $uri $uri/ =404;
    }}

    location /files {{
        alias {bench_path}/sites/{site_name}/public/files;
        expires 7d;
        try_files $uri =404;
    }}

    location /private/files {{
        internal;
        alias {bench_path}/sites/{site_name}/private/files;
    }}

    location / {{
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 120s;
    }}
}}
"""
	sftp = client.open_sftp()
	try:
		with sftp.open(tmp_path, "w") as f:
			f.write(full_conf)
	finally:
		sftp.close()

	_run_step(
		client, site_request_name, site_name, "nginx_full_ssl",
		f"sudo mv {tmp_path} {conf_path} && sudo nginx -t && sudo systemctl reload nginx",
	)


def _notify_site_updated(client, site_request_name, site_name, bench_path):
	"""Clears the target site's Redis-level cache (bootinfo/translations/etc. survive a
	`systemctl restart` — that only restarts the process, not Redis) and publishes Frappe's
	own built-in `version-update` realtime event, which every already-open desk session on
	that site is listening for out of the box (frappe/public/js/frappe/desk.js) — it pops the
	stock "The application has been updated... Refresh" dialog with a Refresh button that
	does `location.reload(true)`. Same mechanism `bench migrate` itself uses
	(frappe/migrate.py). No custom popup needed — we're just triggering the one Frappe
	already ships.

	Each step below is best-effort (caught, not re-raised) — confirmed live: refresh_icons
	failing (site genuinely had no stylo_core due to a separate now-fixed bug) propagated
	all the way up and flipped an otherwise fully-successful deployment (site created, DNS
	set, SSL issued) to "Failed", the same failure class already fixed once for the
	post-deploy email. None of these three are load-bearing for "is the site actually up."
	"""
	for step_name, cmd in (
		(
			"refresh_icons",
			f"{_bench_prefix(bench_path)} bench --site '{site_name}' execute stylo_core.install_icons.run",
		),
		(
			"clear_cache",
			f"{_bench_prefix(bench_path)} bench --site '{site_name}' clear-cache",
		),
		(
			"notify_update",
			f"{_bench_prefix(bench_path)} bench --site '{site_name}' execute frappe.publish_realtime "
			f"--args \"['version-update']\"",
		),
	):
		try:
			_run_step(client, site_request_name, site_name, step_name, cmd)
		except DeploymentError:
			pass


@frappe.whitelist()
def get_server_time():
	"""Called by the frontend right before triggering a module install so it can pass an
	accurate `since` floor to get_deploy_progress — using the server's own clock (not the
	browser's) avoids any client/server clock-skew edge case in the timestamp filter."""
	return now_datetime()


@frappe.whitelist()
def get_deploy_progress(site: str | None = None, site_request: str | None = None, since: str | None = None):
	"""Polled by the frontend's DeployProgress dialog for real-time task/step visibility
	into a background deployment (site creation or module install) — Deploy Log already
	captures every step as it happens, this just shapes it for a progress UI.

	`since` (a timestamp the frontend captures right before triggering the action) matters
	for `site` lookups specifically: a Site accumulates Deploy Log history across every
	module ever installed on it, so without a time floor, installing a *second* module
	would show old completed/failed steps from the *first* install mixed into "current"
	progress — site_request lookups don't need this since each Site Request's log history
	is inherently scoped to that one deployment."""
	if not any(r in frappe.get_roles() for r in ("Command Center Super Admin", "Command Center Admin")):
		frappe.throw("Not permitted", frappe.PermissionError)

	filters = {}
	if site:
		filters["site"] = site
	if site_request:
		filters["site_request"] = site_request
	if not filters:
		frappe.throw("site or site_request is required")
	if since:
		filters["timestamp"] = [">=", since]

	steps = frappe.get_all(
		"Deploy Log",
		filters=filters,
		fields=["step", "success", "output", "timestamp"],
		order_by="timestamp asc",
	)

	overall = "in_progress"
	if steps:
		if any(not s.success for s in steps):
			overall = "failed"
		elif steps[-1].step in ("restart_service", "set_license_config", "notify_update"):
			overall = "done"

	current_status = None
	if site_request:
		current_status = frappe.db.get_value("Site Request", site_request, "status")
	elif site:
		current_status = frappe.db.get_value("Site", site, "status")

	return {"steps": steps, "overall": overall, "current_status": current_status}


def _already_done_steps(site_request_name) -> set:
	"""Steps already logged as successful — used by retry to skip work that's already done."""
	rows = frappe.get_all(
		"Deploy Log",
		filters={"site_request": site_request_name, "success": 1},
		pluck="step",
	)
	return set(rows)


def run_deployment(site_request: str):
	sr = frappe.get_doc("Site Request", site_request)
	server_doc = frappe.get_doc("Server", sr.server)

	if server_doc.hosting_type != "Stylo-Managed":
		frappe.throw(
			f"Server {server_doc.name} is Client-Premise — automated SSH deployment does not apply. "
			"Use the build-and-handoff flow instead."
		)

	done = _already_done_steps(site_request)
	site_name = sr.sitename
	bench_path = server_doc.bench_path
	module_keys = [r.module_key for r in sr.requested_modules]
	apps = resolve_apps(module_keys)

	try:
		client = _get_ssh_client(server_doc)
	except Exception as e:
		sr.db_set("status", "Failed")
		sr.db_set("failure_reason", f"SSH connection failed: {e}")
		_log(site_request, None, "connect", str(e), False)
		frappe.db.commit()
		return

	try:
		# Step 1: create_site
		if "create_site" not in done:
			# Default is the standard Administrator/stylo123Admin used across every
			# Stylo-managed server (see CLAUDE.md) — a random per-site password was the
			# old behavior but doesn't match how Bhanu actually wants to log into a new
			# site's Administrator account day to day. A requester can still override it
			# per-request via Site Request.admin_password.
			admin_password = (
				get_decrypted_password(
					"Site Request", sr.name, "admin_password", raise_exception=False
				)
				or "stylo123Admin"
			)
			db_root_password = get_decrypted_password(
				"Server", server_doc.name, "db_root_password", raise_exception=False
			)
			_run_step(
				client,
				site_request,
				site_name,
				"create_site",
				f"{_bench_prefix(bench_path)} bench new-site '{site_name}' "
				f"--db-root-username root --db-root-password '{db_root_password}' "
				f"--admin-password '{admin_password}' "
				f"--mariadb-user-host-login-scope='%'",
			)

			site_doc = frappe.get_doc(
				{
					"doctype": "Site",
					"sitename": site_name,
					"server": server_doc.name,
					"client_name": sr.client_name,
					"site_request": sr.name,
					"status": "Provisioning",
					"admin_password": admin_password,
				}
			)
			site_doc.insert(ignore_permissions=True)
			frappe.db.commit()
		else:
			site_doc = frappe.get_doc("Site", site_name)
			admin_password = get_decrypted_password("Site", site_name, "admin_password", raise_exception=False)

		# Step 1b: complete_setup_wizard — must run before any module's post_install,
		# specifically stylo_core's (which flips System Settings.setup_complete = 1;
		# setup_complete() is a no-op once that's already true). Only frappe.desk's base
		# wizard is completed here — Company/Chart of Accounts (ERPNext-specific) is
		# deliberately left for a manual post-deploy step when BMS is requested.
		if "complete_setup_wizard" not in done:
			setup_args = {
				"language": "English",
				"country": sr.country,
				"currency": sr.currency,
				"timezone": sr.timezone,
				"email": sr.client_contact_email or f"admin@{site_name}",
				"full_name": sr.client_name,
				"password": admin_password,
				"enable_telemetry": 0,
			}
			_run_step(
				client,
				site_request,
				site_name,
				"complete_setup_wizard",
				f"{_bench_prefix(bench_path)} bench --site '{site_name}' execute "
				f"frappe.desk.page.setup_wizard.setup_wizard.setup_complete "
				f"--kwargs {shlex.quote(repr({'args': setup_args}))}",
			)

		# Step 2: install_app per resolved app
		for app in apps:
			step = f"install_app:{app}"
			if step in done:
				continue
			_ensure_app_source_ready(client, bench_path, app, site_request, site_name)
			_run_step(
				client,
				site_request,
				site_name,
				step,
				f"{_bench_prefix(bench_path)} bench --site '{site_name}' install-app '{app}'",
			)
			_ensure_app_assets_ready(client, bench_path, app, site_request, site_name)

		# Step 3: post_install per module (reuses existing stylo_modules/<module>/post_install.sh as-is)
		for module_key in module_keys:
			step = f"post_install:{module_key}"
			if step in done:
				continue
			_sftp_and_run_post_install(client, module_key, site_name, bench_path, site_request)
			site_doc.append("modules", {"module_key": module_key, "installed_on": now_datetime().date()})

		# Step 4: restart_service
		if "restart_service" not in done:
			_run_step(
				client,
				site_request,
				site_name,
				"restart_service",
				f"sudo systemctl restart {server_doc.web_service_name}",
			)

		# Step 4b: DNS — must point at this server BEFORE certbot tries to validate against
		# it (see _ensure_dns_record's docstring for the exact failure this prevents).
		if "dns_record" not in done:
			_ensure_dns_record(site_name, server_doc.host, site_request)

		# Step 5: nginx vhost + SSL — without this the site is only reachable on the
		# backend, never at its own public URL (see _setup_nginx_ssl's docstring).
		if "nginx_full_ssl" not in done:
			_setup_nginx_ssl(client, site_name, bench_path, site_request)

		site_doc.status = "Active"
		site_doc.save(ignore_permissions=True)
		sr.db_set("status", "Deployed")
		frappe.db.commit()
		_notify_site_updated(client, site_request, site_name, bench_path)

		# Best-effort notification — the deployment itself is already committed as Deployed/
		# Active above, so a broken/unconfigured Email Account (confirmed the actual failure
		# mode: "Please setup default outgoing Email Account") must not fall through to the
		# except block below and flip an already-successful deployment back to "Failed".
		try:
			frappe.sendmail(
				recipients=[sr.requested_by],
				subject=f"Site {site_name} is live",
				message=f"Your requested site <b>{site_name}</b> has been deployed and is now active.",
			)
		except Exception:
			frappe.log_error(title="Site-ready email failed (deployment itself succeeded)")

	except Exception as e:
		frappe.db.rollback()
		sr.db_set("status", "Failed")
		sr.db_set("failure_reason", str(e)[:2000])
		if frappe.db.exists("Site", site_name):
			frappe.db.set_value("Site", site_name, "status", "Failed")
		frappe.db.commit()

	finally:
		client.close()


@frappe.whitelist()
def request_add_module(site: str, module_key: str):
	"""HTTP entry point — role-gates and enqueues add_module_to_site so the request doesn't
	block on a live SSH session, matching how approve() enqueues run_deployment rather than
	running it inline.

	Checked here too (not just inside the job) so a duplicate click fails immediately with a
	clear message instead of silently queuing a second run — which previously produced a
	real duplicate `Site Module` row on stangroup.stylo.io when a failed first attempt was
	retried by clicking Install again."""
	if SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Not permitted", frappe.PermissionError)

	if frappe.db.exists("Site Module", {"parent": site, "module_key": module_key}):
		frappe.throw(f"{module_key} is already installed on {site}")

	frappe.enqueue(
		"command_center.api.deploy.add_module_to_site",
		queue="long",
		timeout=1800,
		site=site,
		module_key=module_key,
	)
	return {"status": "queued"}


def add_module_to_site(site: str, module_key: str):
	if SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Not permitted", frappe.PermissionError)

	site_doc = frappe.get_doc("Site", site)
	server_doc = frappe.get_doc("Server", site_doc.server)

	# Re-checked here (not just in request_add_module) as the authoritative guard against
	# re-running install steps for a module that's already on the site — request_add_module's
	# check only protects against a duplicate *click*, not e.g. this being invoked directly.
	if any(m.module_key == module_key for m in site_doc.modules):
		return

	if server_doc.hosting_type != "Stylo-Managed":
		frappe.throw(
			f"Server {server_doc.name} is Client-Premise — automated SSH deployment does not apply."
		)

	client = _get_ssh_client(server_doc)
	try:
		for app in resolve_apps([module_key]):
			_ensure_app_source_ready(client, server_doc.bench_path, app, None, site)
			_run_step(
				client,
				None,
				site,
				f"install_app:{app}",
				f"{_bench_prefix(server_doc.bench_path)} bench --site '{site}' install-app '{app}'",
			)
			_ensure_app_assets_ready(client, server_doc.bench_path, app, None, site)
		_sftp_and_run_post_install(client, module_key, site, server_doc.bench_path, None)
		_run_step(
			client, None, site, "restart_service", f"sudo systemctl restart {server_doc.web_service_name}"
		)
		site_doc.append("modules", {"module_key": module_key, "installed_on": now_datetime().date()})
		site_doc.save(ignore_permissions=True)
		frappe.db.commit()
		_notify_site_updated(client, None, site, server_doc.bench_path)
	finally:
		client.close()
