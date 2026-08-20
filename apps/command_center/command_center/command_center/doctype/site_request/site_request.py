import frappe
from frappe.model.document import Document

SUPER_ADMIN_ROLE = "Command Center Super Admin"

# base_module (the New Request form's single Select dropdown) -> the module_key
# run_deployment actually reads from requested_modules. "insights" is the one label that
# doesn't just get a "stylo_" prefix.
BASE_MODULE_TO_KEY = {
	"bms": "stylo_bms",
	"hr": "stylo_hr",
	"crm": "stylo_crm",
	"lms": "stylo_lms",
	"desk": "stylo_desk",
	"brain": "stylo_brain",
	"insights": "stylo_analytics",
}


class SiteRequest(Document):
	def before_insert(self):
		# Real bug hit live: base_module and requested_modules were entirely disconnected —
		# nothing ever converted a form's base_module selection into the child table
		# run_deployment reads, so every site created through the New Request dialog got an
		# empty requested_modules and ended up with nothing but bare `frappe` installed
		# (confirmed: stylo_core.install_icons.run failed on a "deployed" site with
		# "App stylo_core is not installed"). stylo_core is always required first per the
		# module system (see CLAUDE.md) — prepend it unconditionally.
		if not self.requested_modules:
			self.append("requested_modules", {"module_key": "stylo_core"})
			module_key = BASE_MODULE_TO_KEY.get(self.base_module)
			if module_key:
				self.append("requested_modules", {"module_key": module_key})

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
