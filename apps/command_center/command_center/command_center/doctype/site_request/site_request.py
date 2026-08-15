import frappe
from frappe.model.document import Document

SUPER_ADMIN_ROLE = "Command Center Super Admin"


class SiteRequest(Document):
	def validate(self):
		# Defense in depth: approval/rejection must go through the whitelisted
		# api/site_request.py::approve()/reject() methods (built in Phase 3), which
		# check this role explicitly before enqueuing deployment. This blocks the
		# same transition from a raw doc.save() by anyone who only has doctype-level
		# write access (e.g. an Admin on their own request).
		if self.has_value_changed("status") and self.status in ("Approved", "Rejected"):
			if SUPER_ADMIN_ROLE not in frappe.get_roles():
				frappe.throw("Only a Command Center Super Admin can approve or reject a Site Request")


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or SUPER_ADMIN_ROLE in frappe.get_roles(user):
		return ""
	return f"(`tabSite Request`.`owner` = {frappe.db.escape(user)})"
