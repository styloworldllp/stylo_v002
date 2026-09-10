"""
Team management — a Command-Center-styled front for creating Frappe Users with one of the
three Command Center roles, instead of using the generic Desk /app/user/new form. Doesn't
duplicate User as a doctype; just wraps frappe.get_doc("User", ...) with role validation.
"""

import secrets
import string

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


def _generate_password(length: int = 16) -> str:
	# At least one of each character class, rest random — avoids ambiguous-looking chars.
	alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
	symbols = "!@#$%^&*"
	pwd = [
		secrets.choice(string.ascii_uppercase),
		secrets.choice(string.ascii_lowercase),
		secrets.choice(string.digits),
		secrets.choice(symbols),
	]
	pwd += [secrets.choice(alphabet + symbols) for _ in range(length - len(pwd))]
	secrets.SystemRandom().shuffle(pwd)
	return "".join(pwd)


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


@frappe.whitelist()
def reset_team_member_password(email: str):
	"""Super Admin sets a brand-new password for a team member directly (no email round-trip
	needed — useful when the member is locked out or the welcome email never arrived).
	Returns the plaintext password once; it is never stored or logged anywhere."""
	_require_super_admin()

	if not frappe.db.exists("Has Role", {"parent": email, "role": ["in", COMMAND_CENTER_ROLES]}):
		frappe.throw("That user is not a Command Center team member", frappe.PermissionError)

	new_password = _generate_password()
	user = frappe.get_doc("User", email)
	user.new_password = new_password
	user.save(ignore_permissions=True)
	frappe.db.commit()
	return {"email": email, "new_password": new_password}


@frappe.whitelist()
def update_team_member_role(email: str, role: str):
	"""Replace a team member's Command Center role with a different one of the three."""
	_require_super_admin()

	if role not in COMMAND_CENTER_ROLES:
		frappe.throw(f"Invalid role: {role}")

	if not frappe.db.exists("Has Role", {"parent": email, "role": ["in", COMMAND_CENTER_ROLES]}):
		frappe.throw("That user is not a Command Center team member", frappe.PermissionError)

	user = frappe.get_doc("User", email)
	for row in list(user.roles):
		if row.role in COMMAND_CENTER_ROLES:
			user.remove(row)
	user.append("roles", {"role": role})
	user.save(ignore_permissions=True)
	frappe.db.commit()
	return {"email": email, "role": role}


@frappe.whitelist()
def set_team_member_status(email: str, enabled: bool):
	"""Enable or disable a team member's login without deleting the User record."""
	_require_super_admin()

	if not frappe.db.exists("Has Role", {"parent": email, "role": ["in", COMMAND_CENTER_ROLES]}):
		frappe.throw("That user is not a Command Center team member", frappe.PermissionError)

	frappe.db.set_value("User", email, "enabled", 1 if int(enabled) else 0)
	frappe.db.commit()
	return {"email": email, "enabled": bool(int(enabled))}
