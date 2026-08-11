"""
license_management.py — runs on the Stylo Cloud master server.

Handles:
- release_license(): admin action to issue a license after payment confirmed
- check_expiring_licenses(): daily scheduler for renewal notifications
- update_license_statuses(): moves Active → Grace Period → Expired automatically
"""

import uuid

import frappe
from frappe.utils import add_days, add_months, date_diff, nowdate, today
from frappe.utils.password import get_decrypted_password

# Stylo module install keys (stylo_modules/) -> commercial license keys (license_map.py).
# stylo_core/stylo_brain/stylo_command_center are never commercial entitlements (core is
# mandatory infra, brAIn is complimentary, command center is internal-only); stylo_reco has
# no separate license key (bundled free into bms — see license_map.py).
INSTALL_TO_LICENSE_KEY = {
	"stylo_bms": "bms",
	"stylo_hr": "hr",
	"stylo_crm": "crm",
	"stylo_analytics": "insights",
	"stylo_lms": "lms",
	"stylo_lending": "lending",
	"stylo_desk": "desk",
}


def _site_api_key(lic_name: str) -> str:
	"""Decrypted site_api_key right after insert — always re-fetch rather than trust the
	in-memory Document value, since Frappe may mask Password fields post-save."""
	return get_decrypted_password("Stylo License", lic_name, "site_api_key", raise_exception=False)


# ── Release license after payment confirmed ────────────────────────────────

@frappe.whitelist()
def release_license(license_request_name: str):
	"""Admin action button: confirm payment and issue the Stylo License."""
	req = frappe.get_doc("Stylo License Request", license_request_name)

	if req.status == "Issued":
		frappe.throw("License has already been issued for this request.")
	if req.status not in ("Pending Payment", "Confirmed"):
		frappe.throw(f"Cannot issue license — request is in status: {req.status}")

	frappe.only_for("System Manager")

	start = today()
	end = add_months(start, int(req.duration_months or 12))

	# Entitled modules from base + all addons (base_module is retained on the Request for
	# the commercial quoting flow, even though it no longer exists on Stylo License itself)
	module_keys = [req.base_module] if req.base_module else []
	for addon in req.addon_modules or []:
		if addon.module_key and addon.module_key not in module_keys:
			module_keys.append(addon.module_key)

	lic = frappe.new_doc("Stylo License")
	lic.license_key = str(uuid.uuid4())
	lic.site = req.site or ""
	lic.client_name = req.client_name
	lic.client_contact_email = req.client_contact_email or ""
	lic.consultant = req.consultant
	lic.license_request = req.name
	lic.entitled_modules = [{"module_key": k} for k in module_keys]
	lic.user_limit = int(req.num_users or 0)
	lic.start_date = start
	lic.end_date = end
	lic.grace_end_date = add_days(end, 30)
	lic.status = "Active"
	lic.insert(ignore_permissions=True)

	req.status = "Issued"
	req.save(ignore_permissions=True)
	frappe.db.commit()

	_send_license_confirmation(lic, req)

	return {"license": lic.name, "key": lic.license_key, "site_api_key": _site_api_key(lic.name)}


@frappe.whitelist()
def release_demo_license(site_request: str):
	"""Command Center action: declare a site Demo/POC — unlimited access, no payment, no
	Stylo License Request involved. Demo → Active later is purely a status flip by a human
	(see Stylo License Architecture V1.0 — demo lifecycle), never a new record."""
	if not any(
		r in frappe.get_roles() for r in ("Command Center Super Admin", "Command Center Admin")
	):
		frappe.throw("Not permitted", frappe.PermissionError)

	sr = frappe.get_doc("Site Request", site_request)
	module_keys = [
		INSTALL_TO_LICENSE_KEY[m.module_key]
		for m in (sr.requested_modules or [])
		if m.module_key in INSTALL_TO_LICENSE_KEY
	]

	lic = frappe.new_doc("Stylo License")
	lic.license_key = str(uuid.uuid4())
	lic.site = sr.sitename
	lic.client_name = sr.client_name
	lic.client_contact_email = sr.client_contact_email or ""
	lic.entitled_modules = [{"module_key": k} for k in module_keys if k]
	lic.user_limit = 9999
	lic.status = "Demo"
	lic.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"license": lic.name, "site_api_key": _site_api_key(lic.name)}


@frappe.whitelist()
def import_existing_license(site: str, client_name: str, entitled_modules: list):
	"""Command Center action: back-fill a Stylo License for a site that already existed
	before Command Center could track it (e.g. demo.stylo.io, nhs.stylo.io). status=Active
	with a generous default user_limit — a human tunes it down later; this just establishes
	the record and the site_api_key needed to activate real login-time enforcement."""
	if not any(
		r in frappe.get_roles() for r in ("Command Center Super Admin", "Command Center Admin")
	):
		frappe.throw("Not permitted", frappe.PermissionError)

	if frappe.db.exists("Stylo License", {"site": site, "status": ["!=", "Terminated"]}):
		frappe.throw(f"An active Stylo License already exists for {site}")

	start = today()
	end = add_months(start, 12)

	lic = frappe.new_doc("Stylo License")
	lic.license_key = str(uuid.uuid4())
	lic.site = site
	lic.client_name = client_name
	lic.entitled_modules = [{"module_key": k} for k in entitled_modules]
	lic.user_limit = 9999
	lic.start_date = start
	lic.end_date = end
	lic.grace_end_date = add_days(end, 30)
	lic.status = "Active"
	lic.insert(ignore_permissions=True)
	frappe.db.commit()

	return {"license": lic.name, "site_api_key": _site_api_key(lic.name)}


# ── Add module to existing site ────────────────────────────────────────────

@frappe.whitelist()
def release_addon(addon_request_name: str):
	"""Admin action: unlock an additional module on an existing site's license."""
	req = frappe.get_doc("Stylo License Addon Request", addon_request_name)

	if req.status == "Applied":
		frappe.throw("This addon has already been applied.")
	if req.status not in ("Pending Payment", "Confirmed"):
		frappe.throw(f"Cannot apply addon — status is: {req.status}")

	frappe.only_for("System Manager")

	lic = frappe.get_doc("Stylo License", req.license)

	# 1. Add module to entitled_modules (no-op if already entitled)
	existing = [m.module_key for m in (lic.entitled_modules or [])]
	if req.module_to_add not in existing:
		lic.append("entitled_modules", {"module_key": req.module_to_add})

	# 2. Increase user limit if requested
	if int(req.user_count_change or 0) > 0:
		lic.user_limit = int(lic.user_limit or 0) + int(req.user_count_change)

	lic.save(ignore_permissions=True)

	req.status = "Applied"
	req.save(ignore_permissions=True)
	frappe.db.commit()

	_send_addon_confirmation(lic, req)

	return {
		"success": True,
		"entitled_modules": [m.module_key for m in (lic.entitled_modules or [])],
		"user_limit": lic.user_limit,
	}


def _entitled_modules_display(lic) -> str:
	from stylo_core.license_map import MODULE_DISPLAY_NAMES

	return ", ".join(
		MODULE_DISPLAY_NAMES.get(m.module_key, m.module_key) for m in (lic.entitled_modules or [])
	) or "—"


def _send_addon_confirmation(lic, req):
	from stylo_core.license_map import MODULE_DISPLAY_NAMES
	module_name = MODULE_DISPLAY_NAMES.get(req.module_to_add, req.module_to_add)
	recipients = [req.consultant]
	if lic.client_contact_email:
		recipients.append(lic.client_contact_email)

	frappe.sendmail(
		recipients=list(set(recipients)),
		subject=f"{module_name} unlocked for {lic.site}",
		message=f"""
<p>The module <b>{module_name}</b> has been added to your Stylo license.</p>
<table>
<tr><td><b>Site:</b></td><td>{lic.site}</td></tr>
<tr><td><b>All Licensed Modules:</b></td><td>{_entitled_modules_display(lic)}</td></tr>
<tr><td><b>User Limit:</b></td><td>{lic.user_limit}</td></tr>
</table>
<p>Users on {lic.site} will have access to {module_name} on their next login.</p>
""",
		now=True,
	)


def _send_license_confirmation(lic, req):
	recipients = [req.consultant]
	if req.client_contact_email:
		recipients.append(req.client_contact_email)

	frappe.sendmail(
		recipients=list(set(recipients)),
		subject=f"Stylo License Activated — {lic.client_name}",
		message=f"""
<p>Your Stylo license has been activated.</p>
<table>
<tr><td><b>Client:</b></td><td>{lic.client_name}</td></tr>
<tr><td><b>Site:</b></td><td>{lic.site or 'TBD'}</td></tr>
<tr><td><b>Modules:</b></td><td>{_entitled_modules_display(lic)}</td></tr>
<tr><td><b>Users:</b></td><td>{lic.user_limit} (total slots)</td></tr>
<tr><td><b>Valid until:</b></td><td>{lic.end_date}</td></tr>
<tr><td><b>License key:</b></td><td><code>{lic.license_key}</code></td></tr>
</table>
<p>For renewal, please contact your Stylo consultant at least 30 days before expiry.</p>
""",
		now=True,
	)


# ── Daily scheduler ────────────────────────────────────────────────────────

def check_expiring_licenses():
	"""Daily job: send renewal reminders and update license statuses."""
	update_license_statuses()
	_send_renewal_reminders()


def update_license_statuses():
	"""Move licenses from Active → Grace Period → Expired based on today's date."""
	today_str = today()

	# Active → Grace Period (past end_date but within grace)
	frappe.db.sql("""
		UPDATE `tabStylo License`
		SET status = 'Grace Period'
		WHERE status = 'Active'
		  AND end_date < %s
		  AND grace_end_date >= %s
	""", (today_str, today_str))

	# Grace Period → Expired (past grace_end_date)
	frappe.db.sql("""
		UPDATE `tabStylo License`
		SET status = 'Expired'
		WHERE status = 'Grace Period'
		  AND grace_end_date < %s
	""", (today_str,))

	frappe.db.commit()


def _send_renewal_reminders():
	"""Send email reminders at 60, 30, 15, 7 days before expiry and on expiry/grace-end."""
	today_str = today()
	reminder_days = [60, 30, 15, 7]

	admin_email = (
		frappe.db.get_single_value("System Settings", "email_footer_address")
		or "hello@stylo.io"
	)

	licenses = frappe.get_all(
		"Stylo License",
		filters={"status": ["in", ["Active", "Grace Period"]]},
		fields=["name", "client_name", "site", "consultant", "client_contact_email",
		        "end_date", "grace_end_date", "user_limit", "status"],
	)

	for lic in licenses:
		days_left = date_diff(lic.end_date, today_str)
		grace_days_left = date_diff(lic.grace_end_date, today_str)

		recipients = [r for r in [lic.consultant, lic.client_contact_email] if r]

		if days_left in reminder_days:
			urgency = "Critical" if days_left <= 7 else ("Urgent" if days_left <= 15 else "Action needed")
			if days_left <= 7:
				recipients.append(admin_email)
			_send_reminder(
				recipients=list(set(recipients)),
				client_name=lic.client_name,
				site=lic.site,
				days_left=days_left,
				end_date=lic.end_date,
				subject=f"{urgency}: Stylo license for {lic.client_name} expires in {days_left} days",
				phase="expiry",
			)

		elif days_left == 0:
			recipients.append(admin_email)
			_send_reminder(
				recipients=list(set(recipients)),
				client_name=lic.client_name,
				site=lic.site,
				days_left=0,
				end_date=lic.end_date,
				subject=f"Stylo license expired — {lic.client_name} is in 30-day grace period",
				phase="grace_start",
			)

		elif grace_days_left == 0:
			recipients.append(admin_email)
			_send_reminder(
				recipients=list(set(recipients)),
				client_name=lic.client_name,
				site=lic.site,
				days_left=grace_days_left,
				end_date=lic.grace_end_date,
				subject=f"URGENT: {lic.client_name} site will be locked today — license grace period ended",
				phase="grace_end",
			)


def _send_reminder(recipients, client_name, site, days_left, end_date, subject, phase):
	if phase == "expiry":
		body = f"""
<p>This is a reminder that the Stylo license for <b>{client_name}</b> ({site or 'N/A'})
expires on <b>{end_date}</b> — in <b>{days_left} days</b>.</p>
<p>Please initiate a renewal request through Stylo Cloud to avoid service interruption.</p>
"""
	elif phase == "grace_start":
		body = f"""
<p>The Stylo license for <b>{client_name}</b> ({site or 'N/A'}) has expired today.</p>
<p>A <b>30-day grace period</b> has started. Users will see a warning on login but can
still access the system. Please renew immediately to avoid a site lock.</p>
"""
	else:
		body = f"""
<p>The grace period for <b>{client_name}</b> ({site or 'N/A'}) has ended.</p>
<p>The site has been <b>locked</b>. Users can no longer log in.</p>
<p>Please contact Stylo support to process the renewal and unlock the site.</p>
"""

	frappe.sendmail(recipients=recipients, subject=subject, message=body, now=True)
