"""
Back-fills Site + Stylo License records for sites that already existed before Command Center
could track them (demo.stylo.io, nhs.stylo.io, stangroup.stylo.io) — SSH-detects what's
actually installed rather than trusting manual entry.
"""

import json
from collections import Counter

import frappe
from frappe.utils import now_datetime

from command_center.api.deploy import (
	SUPER_ADMIN_ROLE,
	_bench_prefix,
	_get_ssh_client,
	_log,
	_notify_site_updated,
	_run_step,
)
from frappe.utils.file_manager import save_file
from frappe.utils.password import get_decrypted_password
from command_center.module_map import detect_modules


@frappe.whitelist()
def list_sites():
	"""Site list with module counts — frappe.client.get_list (what createListResource uses)
	never returns child table rows, only get_doc does, so Sites.vue can't get `modules` from
	a plain list query. Batch the counts here instead, same fix as api/licenses.py."""
	sites = frappe.get_list(
		"Site",
		fields=["name", "sitename", "client_name", "server", "status"],
		order_by="modified desc",
		limit_page_length=200,
	)

	# frappe.get_all() rejects raw SQL function strings in `fields` in this Frappe version
	# (see command_center/api/dashboard.py for the same fix) — tally in Python instead.
	parents = frappe.get_all(
		"Site Module", filters={"parent": ["in", [s.name for s in sites]]}, pluck="parent"
	)
	count_by_site = Counter(parents)

	for s in sites:
		s["module_count"] = count_by_site.get(s.name, 0)

	return sites


@frappe.whitelist()
def request_import_site(server: str, sitename: str, client_name: str):
	"""HTTP entry point — enqueues import_existing_site instead of running it inline.

	Running it inline was the actual bug behind "clicking Import does nothing": on servers
	where console.stylo.io shares a systemd web service with the site being imported (demo
	and nhs both live on stylo-web.service), the restart_service step at the end of the
	import kills the very request that's running it — the browser's `await call()` never
	resolves, no error, dialog just sits there. Enqueueing (matching approve()/
	request_add_module()'s existing pattern) returns before any SSH work happens, so the
	restart can no longer cut its own request off. Also gives real progress/error visibility
	via get_deploy_progress on servers (e.g. stangroup) where that specific failure mode
	doesn't apply but something else might silently be going wrong.
	"""
	if SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Not permitted", frappe.PermissionError)

	if frappe.db.exists("Site", sitename):
		frappe.throw(f"Site {sitename} is already tracked in Command Center")

	frappe.enqueue(
		"command_center.api.sites.import_existing_site",
		queue="long",
		timeout=1800,
		server=server,
		sitename=sitename,
		client_name=client_name,
	)
	return {"status": "queued"}


def import_existing_site(server: str, sitename: str, client_name: str):
	server_doc = frappe.get_doc("Server", server)
	client = _get_ssh_client(server_doc)

	try:
		out = _run_step(
			client, None, sitename, "list_apps",
			f"{_bench_prefix(server_doc.bench_path)} bench --site '{sitename}' list-apps --format json",
		)

		installed_apps = json.loads(out).get(sitename, [])
		module_keys = detect_modules(installed_apps)

		site_doc = frappe.get_doc(
			{
				"doctype": "Site",
				"sitename": sitename,
				"server": server_doc.name,
				"client_name": client_name,
				"status": "Active",
				"created_by_user": frappe.session.user,
				"modules": [
					{"module_key": k, "installed_on": now_datetime().date()} for k in module_keys
				],
			}
		)
		site_doc.insert(ignore_permissions=True)
		frappe.db.commit()

		from stylo_core.license_management import INSTALL_TO_LICENSE_KEY, import_existing_license

		entitled = [INSTALL_TO_LICENSE_KEY[k] for k in module_keys if k in INSTALL_TO_LICENSE_KEY]
		result = import_existing_license(
			site=sitename, client_name=client_name, entitled_modules=entitled
		)

		site_doc.license = result["license"]
		site_doc.save(ignore_permissions=True)
		frappe.db.commit()

		# Push the master URL + this site's auth key into its own site_config so
		# check_user_license_on_login() actually reaches console.stylo.io instead of the
		# unconfigured no-op bypass.
		_push_license_config(client, sitename, server_doc, result["site_api_key"])
		_notify_site_updated(client, None, sitename, server_doc.bench_path)

	except Exception:
		frappe.db.rollback()
		_log(None, sitename, "import_failed", frappe.get_traceback()[:4000], False)
		frappe.db.commit()
	finally:
		client.close()


def _push_license_config(client, sitename, server_doc, site_api_key):
	cloud_url = frappe.utils.get_url()  # console.stylo.io's own URL — this site's home
	_run_step(
		client, None, sitename, "set_license_config",
		f"{_bench_prefix(server_doc.bench_path)} bench --site '{sitename}' set-config stylo_cloud_url '{cloud_url}' && "
		f"{_bench_prefix(server_doc.bench_path)} bench --site '{sitename}' set-config stylo_site_api_key '{site_api_key}'",
	)
	_run_step(
		client, None, sitename, "restart_service",
		f"sudo systemctl restart {server_doc.web_service_name}",
	)


@frappe.whitelist()
def push_license_config(sitename: str, site_api_key: str):
	"""Standalone entry point for sites that already have a Site record and just had a
	license issued/re-issued (e.g. via SiteRequests.vue's "Declare Demo/POC" action) — opens
	its own SSH session rather than reusing one from import_existing_site's flow."""
	if SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Not permitted", frappe.PermissionError)

	site_doc = frappe.get_doc("Site", sitename)
	server_doc = frappe.get_doc("Server", site_doc.server)
	client = _get_ssh_client(server_doc)
	try:
		_push_license_config(client, sitename, server_doc, site_api_key)
	finally:
		client.close()
	return {"status": "ok"}


@frappe.whitelist()
def request_delete_site(site: str, take_backup: bool = True):
	"""HTTP entry point — role-gates and enqueues delete_site. Deleting a site is
	irreversible (drop-site destroys the database), so this deliberately only fires from an
	explicit user action with its own confirmation in the frontend — never automatically."""
	if SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Not permitted", frappe.PermissionError)

	if not frappe.db.exists("Site", site):
		frappe.throw(f"Site {site} is not tracked in Command Center")

	frappe.enqueue(
		"command_center.api.sites.delete_site",
		queue="long",
		timeout=1800,
		site=site,
		take_backup=take_backup,
		deleted_by=frappe.session.user,
	)
	return {"status": "queued"}


def delete_site(site: str, take_backup: bool = True, deleted_by: str | None = None):
	site_doc = frappe.get_doc("Site", site)
	server_doc = frappe.get_doc("Server", site_doc.server)
	client = _get_ssh_client(server_doc)
	backup_doc = None

	try:
		if take_backup:
			# Taken and pulled off the target server BEFORE drop-site runs — drop-site
			# deletes the site's own folder (including its private/backups dir), so a
			# backup left there would be destroyed along with everything else. Attached
			# to this Site Backup doc via Frappe's own File doctype (frappe.utils.
			# file_manager.save_file) so it's stored durably on Command Center's own site
			# (console.stylo.io), permission-checked, and still downloadable long after
			# the Site/Server records it came from are gone.
			backup_doc = frappe.get_doc(
				{
					"doctype": "Site Backup",
					"site": site,
					"server": server_doc.name,
					"reason": "Pre-Delete",
					"status": "In Progress",
					"triggered_by": deleted_by,
				}
			).insert(ignore_permissions=True)
			frappe.db.commit()

			_run_step(
				client, None, site, "backup_site",
				f"{_bench_prefix(server_doc.bench_path)} bench --site '{site}' backup --with-files",
			)
			backup_dir = f"{server_doc.bench_path}/sites/{site}/private/backups"
			ls_out = _run_step(
				client, None, site, "locate_backup_files",
				f"ls -t {backup_dir} | head -5",
			)
			filenames = [line.strip() for line in ls_out.splitlines() if line.strip()]
			if not filenames:
				raise Exception(f"backup command reported success but no files found in {backup_dir}")

			sftp = client.open_sftp()
			try:
				for fname in filenames:
					with sftp.open(f"{backup_dir}/{fname}", "rb") as rf:
						content = rf.read()
					save_file(fname, content, "Site Backup", backup_doc.name, is_private=1)
			finally:
				sftp.close()

			backup_doc.db_set("status", "Completed")
			frappe.db.commit()

		db_root_password = get_decrypted_password(
			"Server", server_doc.name, "db_root_password", raise_exception=False
		)
		_run_step(
			client, None, site, "drop_site",
			f"{_bench_prefix(server_doc.bench_path)} bench drop-site '{site}' --force --no-backup "
			f"--db-root-username root --db-root-password '{db_root_password}'",
		)

		# Best-effort cleanup — a leftover nginx conf/web-service hiccup here shouldn't
		# block the deletion (the site's data is already gone at this point), so these two
		# don't use _run_step's hard-fail-and-abort behaviour.
		try:
			_run_step(
				client, None, site, "remove_nginx_vhost",
				f"sudo rm -f /etc/nginx/conf.d/{site}.conf && sudo nginx -t && sudo systemctl reload nginx",
			)
		except Exception:
			pass
		try:
			_run_step(
				client, None, site, "restart_service",
				f"sudo systemctl restart {server_doc.web_service_name}",
			)
		except Exception:
			pass

		if site_doc.license:
			frappe.db.set_value("Stylo License", site_doc.license, "status", "Terminated")
		# force=True: Deploy Log rows link to this Site (audit trail, by design outlives
		# the site itself) — without it, delete_doc refuses with LinkExistsError.
		frappe.delete_doc("Site", site, force=True, ignore_permissions=True)
		frappe.db.commit()

	except Exception:
		frappe.db.rollback()
		if backup_doc:
			backup_doc.db_set("status", "Failed")
			backup_doc.db_set("notes", frappe.get_traceback()[:2000])
		_log(None, site, "delete_site_failed", frappe.get_traceback()[:4000], False)
		frappe.db.commit()
	finally:
		client.close()
