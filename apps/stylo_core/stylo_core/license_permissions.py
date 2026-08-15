"""
Grants Stylo License Administrator (a customer-side role, see Stylo Licensing Architecture
V1.0 §7) read+write access to the core `User` doctype — just enough to toggle `enabled`
(disable a licensed user) per the spec's affirmative permission list. Frappe's own `User`
doctype isn't owned by this app, so this is done via Custom DocPerm rather than editing
frappe/core/doctype/user/user.json directly. Idempotent — safe to call on every migrate.
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

ROLE = "Stylo License Administrator"


def run():
	if not frappe.db.exists("Role", ROLE):
		return

	if not frappe.db.exists(
		"Custom DocPerm", {"parent": "User", "role": ROLE, "permlevel": 0, "if_owner": 0}
	):
		add_permission("User", ROLE, permlevel=0, ptype="read")
		update_permission_property("User", ROLE, 0, "write", 1)
