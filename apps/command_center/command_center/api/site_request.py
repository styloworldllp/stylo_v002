import frappe

from command_center.api.server import select_best_server

SUPER_ADMIN_ROLE = "Command Center Super Admin"


def _require_super_admin():
	if SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Only a Command Center Super Admin can do this", frappe.PermissionError)


@frappe.whitelist()
def get_form_choices():
	"""Country/Currency/Timezone options for the New Request form's Setup Wizard fields —
	these were plain free-text inputs before, which let a value like "delhi" (not the IANA
	key "Asia/Kolkata") reach frappe.desk.page.setup_wizard.setup_wizard.setup_complete()
	and hard-crash the deployment on a ZoneInfoNotFoundError with no useful message. Country/
	Currency go through this dedicated endpoint rather than frappe.client.get_list because
	that REST path needs DocType-meta read access Command Center Admin/Super Admin don't
	have (same reason api/licenses.py and api/sites.py have their own list endpoints)."""
	import zoneinfo

	return {
		"countries": frappe.get_all("Country", pluck="name", order_by="name"),
		"currencies": frappe.get_all("Currency", pluck="name", order_by="name"),
		"timezones": sorted(zoneinfo.available_timezones()),
	}


@frappe.whitelist()
def approve(site_request: str):
	_require_super_admin()
	sr = frappe.get_doc("Site Request", site_request)

	if sr.status != "Pending Approval":
		frappe.throw(f"Site Request must be Pending Approval, currently {sr.status}")

	if not sr.server:
		sr.server = select_best_server()
		sr.server_auto_selected = 1

	sr.status = "Approved"
	sr.approved_by = frappe.session.user
	sr.save(ignore_permissions=True)
	frappe.db.commit()

	frappe.enqueue(
		"command_center.api.deploy.run_deployment",
		queue="long",
		timeout=3600,
		site_request=sr.name,
	)

	return {"status": "Approved", "server": sr.server, "server_auto_selected": bool(sr.server_auto_selected)}


@frappe.whitelist()
def reject(site_request: str, reason: str | None = None):
	_require_super_admin()
	sr = frappe.get_doc("Site Request", site_request)

	if sr.status != "Pending Approval":
		frappe.throw(f"Site Request must be Pending Approval, currently {sr.status}")

	sr.status = "Rejected"
	sr.approved_by = frappe.session.user
	if reason:
		sr.failure_reason = reason
	sr.save(ignore_permissions=True)
	frappe.db.commit()

	return {"status": "Rejected"}


@frappe.whitelist()
def submit_for_approval(site_request: str):
	"""Admin-facing: move a Draft request into the Super Admin's approval queue."""
	sr = frappe.get_doc("Site Request", site_request)
	if sr.owner != frappe.session.user and SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Not permitted", frappe.PermissionError)
	if sr.status != "Draft":
		frappe.throw(f"Site Request must be Draft, currently {sr.status}")
	sr.status = "Pending Approval"
	sr.save()
	frappe.db.commit()
	return {"status": "Pending Approval"}


@frappe.whitelist()
def retry_deployment(site_request: str):
	"""Re-enqueue run_deployment — steps already logged as successful in Deploy Log are
	skipped (see api/deploy.py::_already_done_steps), so this resumes rather than restarts."""
	_require_super_admin()
	sr = frappe.get_doc("Site Request", site_request)

	if sr.status != "Failed":
		frappe.throw(f"Site Request must be Failed to retry, currently {sr.status}")

	sr.db_set("status", "Approved")
	frappe.db.commit()

	frappe.enqueue(
		"command_center.api.deploy.run_deployment",
		queue="long",
		timeout=3600,
		site_request=sr.name,
	)

	return {"status": "Approved"}
