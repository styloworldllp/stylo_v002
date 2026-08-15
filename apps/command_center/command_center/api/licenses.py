"""
Read-only view over stylo_core's existing Stylo License / Stylo License Request doctypes —
not duplicated here, just surfaced. A dedicated whitelisted method is used instead of the
frontend calling frappe.client.get_list directly, because that generic REST endpoint also
requires DocType-meta read access (effectively System Manager only) on top of document-level
permissions — Command Center Admin/Super Admin have the latter (see stylo_license.json /
stylo_license_request.json permissions) but not the former, and shouldn't need it just to
read a list of licenses.
"""

import frappe

COMMAND_CENTER_ROLES = ("Command Center Super Admin", "Command Center Admin")


def _require_command_center_access():
	if not any(r in frappe.get_roles() for r in COMMAND_CENTER_ROLES):
		frappe.throw("Not permitted", frappe.PermissionError)


@frappe.whitelist()
def get_licenses():
	_require_command_center_access()
	licenses = frappe.get_list(
		"Stylo License",
		fields=["name", "site", "client_name", "end_date", "status"],
		order_by="end_date desc",
		limit_page_length=100,
	)

	module_rows = frappe.get_all(
		"Stylo License Module",
		filters={"parent": ["in", [lic.name for lic in licenses]]},
		fields=["parent", "module_key"],
	)
	modules_by_license = {}
	for row in module_rows:
		modules_by_license.setdefault(row.parent, []).append(row.module_key)

	for lic in licenses:
		lic["modules"] = modules_by_license.get(lic.name, [])

	return licenses
