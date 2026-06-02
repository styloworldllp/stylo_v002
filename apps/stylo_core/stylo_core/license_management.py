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

	# Build licensed_modules from base + all addons (store keys only, not display names)
	all_modules = [req.base_module] if req.base_module else []
	for addon in req.addon_modules or []:
		if addon.module_key and addon.module_key not in all_modules:
			all_modules.append(addon.module_key)
	licensed_modules_str = ",".join(all_modules)

	lic = frappe.new_doc("Stylo License")
	lic.license_key = str(uuid.uuid4())
	lic.site = req.site or ""
	lic.client_name = req.client_name
	lic.client_contact_email = req.client_contact_email or ""
	lic.consultant = req.consultant
	lic.license_request = req.name
	lic.base_module = req.base_module or ""
	lic.licensed_modules = licensed_modules_str
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

	return {"license": lic.name, "key": lic.license_key}


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
<tr><td><b>Modules:</b></td><td>{lic.licensed_modules}</td></tr>
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
		        "end_date", "grace_end_date", "module_pack", "user_limit", "status"],
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
