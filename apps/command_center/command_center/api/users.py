"""
Team management — a Command-Center-styled front for creating Frappe Users with one of the
three Command Center roles, instead of using the generic Desk /app/user/new form. Doesn't
duplicate User as a doctype; just wraps frappe.get_doc("User", ...) with role validation.
"""

import frappe

SUPER_ADMIN_ROLE = "Command Center Super Admin"
COMMAND_CENTER_ROLES = (
	"Command Center Super Admin",
	"Command Center Admin",
	"Command Center Support Staff",
)


def _require_super_admin():
	if SUPER_ADMIN_ROLE not in frappe.get_roles():
		frappe.throw("Not permitted", frappe.PermissionError)


@frappe.whitelist()
def list_team():
	_require_super_admin()
	rows = frappe.get_all(
		"Has Role",
		filters={"role": ["in", COMMAND_CENTER_ROLES], "parenttype": "User"},
		fields=["parent as email", "role"],
	)
	users_by_email = {}
	for row in rows:
		users_by_email.setdefault(row.email, []).append(row.role)

	if not users_by_email:
		return []

	user_rows = frappe.get_all(
		"User",
		filters={"name": ["in", list(users_by_email.keys())]},
		fields=["name as email", "full_name", "enabled"],
	)
	for u in user_rows:
		u["roles"] = users_by_email.get(u["email"], [])
	return user_rows


@frappe.whitelist()
def add_team_member(email: str, full_name: str, role: str):
	_require_super_admin()

	if role not in COMMAND_CENTER_ROLES:
		frappe.throw(f"Invalid role: {role}")

	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		if role not in [r.role for r in user.roles]:
			user.append("roles", {"role": role})
			user.save(ignore_permissions=True)
			frappe.db.commit()
		return {"email": user.name, "status": "role added to existing user"}

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": full_name,
			"send_welcome_email": 1,
			"roles": [{"role": role}],
		}
	)
	user.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"email": user.name, "status": "created"}
