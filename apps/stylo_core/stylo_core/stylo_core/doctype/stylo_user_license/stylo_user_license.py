import frappe
from frappe.model.document import Document

TIER_MODULE_CAP = {
	"Stylo User": 1,
	"Stylo Manager": 2,
	"Stylo Pro": None,  # no cap — auto-synced to all entitled modules instead
}


class StyloUserLicense(Document):
	def validate(self):
		license_doc = self._get_site_license()
		entitled = [m.module_key for m in (license_doc.entitled_modules or [])] if license_doc else []

		if self.tier == "Stylo Pro":
			# Spec: "ALL company-entitled modules" — auto-sync rather than validate a
			# user-supplied list, so this never drifts when the company buys a new module.
			self.set("assigned_modules", [{"module_key": k} for k in entitled])
			return

		assigned = [m.module_key for m in (self.assigned_modules or [])]

		cap = TIER_MODULE_CAP.get(self.tier)
		if cap is not None and len(assigned) > cap:
			frappe.throw(
				f"{self.tier} is limited to {cap} module(s), but {len(assigned)} are assigned"
			)

		ungranted = [m for m in assigned if m not in entitled]
		if ungranted:
			frappe.throw(
				f"Module(s) not entitled on this site's license: {', '.join(ungranted)}"
			)

	def _get_site_license(self):
		from stylo_core.license_api import _get_active_license

		license_row = _get_active_license(frappe.local.site)
		return frappe.get_doc("Stylo License", license_row.name) if license_row else None
