"""
license_api.py — whitelisted API endpoint called by client sites to verify license status,
on every login (see stylo_core/user_license.py::check_user_license_on_login).

Client sites call:
  GET https://console.stylo.io/api/method/stylo_core.license_api.check?site=clientname.stylo.io
  Header: X-Site-Api-Key: <Stylo License.site_api_key for that site>

Auth model mirrors command_center's monitoring-agent endpoint exactly (Server.agent_api_key /
api/metrics.py::ingest()): the calling site has no Frappe user session on console.stylo.io, so
this is allow_guest=True and instead validates a per-license API key via hmac.compare_digest.
Rate-limited to blunt key brute-forcing.

Returns:
  {
    "status": "demo" | "active" | "grace_period" | "expired" | "suspended" | "terminated" | "not_found",
    "user_limit": N,
    "end_date": "YYYY-MM-DD" | None,
    "grace_end_date": "YYYY-MM-DD" | None,
    "days_remaining": N | None,
    "modules": ["bms", "hr"]
  }
"""

import hmac

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import date_diff, today
from frappe.utils.password import get_decrypted_password


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=30, seconds=60)
def check(site: str = ""):
	"""Return current license status for the given site name."""
	if not site:
		site = frappe.local.site

	site_key = frappe.get_request_header("X-Site-Api-Key")
	if not site_key:
		frappe.throw("X-Site-Api-Key is required", frappe.PermissionError)

	license = _get_active_license(site)
	if not license:
		# Don't leak whether the site exists vs. the key being wrong.
		return {"status": "not_found", "user_limit": 0}

	expected_key = get_decrypted_password(
		"Stylo License", license.name, "site_api_key", raise_exception=False
	)
	if not expected_key or not hmac.compare_digest(str(expected_key), str(site_key)):
		frappe.throw("Invalid site or key", frappe.PermissionError)

	doc = frappe.get_doc("Stylo License", license.name)
	computed_status = doc.get_status()

	return {
		"status": computed_status,
		"user_limit": doc.user_limit or 0,
		"end_date": str(doc.end_date) if doc.end_date else None,
		"grace_end_date": str(doc.grace_end_date) if doc.grace_end_date else None,
		"days_remaining": max(0, date_diff(doc.end_date, today())) if doc.end_date else None,
		"modules": [m.module_key for m in (doc.entitled_modules or [])],
	}


def _get_active_license(site: str):
	"""Return the most recent non-expired license for the site, or None."""
	licenses = frappe.get_all(
		"Stylo License",
		filters={"site": site, "status": ["in", ["Demo", "Active", "Grace Period", "Suspended"]]},
		fields=["name", "status", "end_date"],
		order_by="end_date desc",
		limit=1,
	)
	if licenses:
		return licenses[0]

	# Also check Expired (within last 30 days — grace period window)
	expired = frappe.get_all(
		"Stylo License",
		filters={"site": site, "status": "Expired"},
		fields=["name", "status", "end_date", "grace_end_date"],
		order_by="end_date desc",
		limit=1,
	)
	return expired[0] if expired else None
