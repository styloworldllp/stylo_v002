import frappe

COMMAND_CENTER_ROLES = (
	"Command Center Super Admin",
	"Command Center Admin",
	"Command Center Support Staff",
)


def check_app_permission():
	if frappe.session.user == "Administrator":
		return True
	roles = frappe.get_roles()
	return any(r in roles for r in COMMAND_CENTER_ROLES)
