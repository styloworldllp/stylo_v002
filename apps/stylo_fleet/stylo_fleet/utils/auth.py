import frappe

PARAMEDIC_ROLE = "Fleet Paramedic"
STATION_ROLE = "Fleet Station"
OPERATIONS_ROLE = "Fleet Operations"
ADMIN_ROLE = "Fleet Admin"


def require_role(*roles):
	"""Raise PermissionError unless the current user is System Manager, Fleet
	Admin (per spec §15, Admin = Yes on every action), or has one of the given
	Stylo Fleet roles.

	Every whitelisted stylo_fleet API function saves its documents with
	ignore_permissions=True (the fields it touches are system-derived, not
	meant to be hand-edited via the standard DocType permission system) — so
	this check is the actual authorization gate for who may call the action
	at all. Doc-level DocPerm rows (see setup/step10.py) separately control
	what each role can see/edit directly in the Desk UI.
	"""
	user_roles = set(frappe.get_roles())
	if "System Manager" in user_roles or ADMIN_ROLE in user_roles:
		return
	if not user_roles.intersection(roles):
		frappe.throw(
			f"Not permitted. This action requires one of: {', '.join(roles)}.",
			frappe.PermissionError,
		)
