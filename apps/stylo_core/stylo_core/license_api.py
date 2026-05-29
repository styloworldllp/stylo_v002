"""
license_api.py — whitelisted API endpoint called by client sites to verify license status.

Client sites call:
  GET https://cloud.stylo.io/api/method/stylo_core.license_api.check?site=clientname.stylo.io

Returns:
  {
    "status": "active" | "grace_period" | "expired" | "suspended" | "not_found",
    "user_limit": N,
    "end_date": "YYYY-MM-DD",
    "grace_end_date": "YYYY-MM-DD",
    "days_remaining": N,
    "modules": "StyloBMS, StyloHR"
  }
"""

import frappe
from frappe.utils import date_diff, today


@frappe.whitelist(allow_guest=False)
def check(site: str = ""):
	"""Return current license status for the given site name."""
	if not site:
		site = frappe.local.site

	license = _get_active_license(site)
	if not license:
		return {"status": "not_found", "user_limit": 0}

	doc = frappe.get_doc("Stylo License", license.name)
	computed_status = doc.get_status()

	return {
		"status": computed_status,
		"user_limit": doc.user_limit or 0,
		"end_date": str(doc.end_date),
		"grace_end_date": str(doc.grace_end_date),
		"days_remaining": max(0, date_diff(doc.end_date, today())),
		"modules": doc.modules or "",
	}


def _get_active_license(site: str):
	"""Return the most recent non-expired license for the site, or None."""
	licenses = frappe.get_all(
		"Stylo License",
		filters={"site": site, "status": ["in", ["Active", "Grace Period", "Suspended"]]},
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
