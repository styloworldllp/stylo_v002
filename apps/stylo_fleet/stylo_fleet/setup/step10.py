import frappe

PARAMEDIC_ROLE = "Fleet Paramedic"
STATION_ROLE = "Fleet Station"
OPERATIONS_ROLE = "Fleet Operations"
ADMIN_ROLE = "Fleet Admin"

ROLES = [PARAMEDIC_ROLE, STATION_ROLE, OPERATIONS_ROLE, ADMIN_ROLE]

# Doc-level permissions per spec §15. These govern what each role can see/edit
# directly in the Desk UI — the real authorization gate for *actions* is
# require_role() inside each whitelisted API function (doc saves there use
# ignore_permissions=True since the fields are system-derived).
AMBULANCE_PERMS = [
	{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
	{"role": ADMIN_ROLE, "read": 1, "write": 1, "create": 1, "delete": 1},
	{"role": OPERATIONS_ROLE, "read": 1, "write": 1},
	{"role": STATION_ROLE, "read": 1},
	{"role": PARAMEDIC_ROLE, "read": 1},
]

TRANSACTION_PERMS = [
	{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
	{"role": ADMIN_ROLE, "read": 1, "write": 1, "submit": 1, "cancel": 1},
	{"role": OPERATIONS_ROLE, "read": 1},
	{"role": STATION_ROLE, "read": 1},
	{"role": PARAMEDIC_ROLE, "read": 1},
]

MASTER_PERMS = [
	{"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
	{"role": ADMIN_ROLE, "read": 1, "write": 1, "create": 1, "delete": 1},
	{"role": OPERATIONS_ROLE, "read": 1, "write": 1},
	{"role": STATION_ROLE, "read": 1},
	{"role": PARAMEDIC_ROLE, "read": 1},
]

PERM_PLAN = {
	"Ambulance": AMBULANCE_PERMS,
	"Ambulance Shift": TRANSACTION_PERMS,
	"Ambulance Activity": TRANSACTION_PERMS,
	"Ambulance Refill": TRANSACTION_PERMS,
	"Ambulance Issue": TRANSACTION_PERMS,
	"Ambulance Station": MASTER_PERMS,
	"Paramedic": MASTER_PERMS,
	"Ambulance Settings": MASTER_PERMS,
}


def _create_roles():
	for role_name in ROLES:
		if frappe.db.exists("Role", role_name):
			print(f"Skip (exists): Role {role_name}")
			continue
		frappe.get_doc({
			"doctype": "Role",
			"role_name": role_name,
			"desk_access": 1,
		}).insert(ignore_permissions=True)
		print(f"Created: Role {role_name}")


def _apply_permissions():
	for doctype, perm_rows in PERM_PLAN.items():
		dt = frappe.get_doc("DocType", doctype)
		if dt.permissions:
			print(f"Skip (already has permissions): {doctype}")
			continue
		for row in perm_rows:
			dt.append("permissions", row)
		dt.save(ignore_permissions=True)
		print(f"Applied permissions: {doctype}")


def run():
	_create_roles()
	_apply_permissions()
	frappe.db.commit()
	print("Step 10 (Hardening: roles + permissions) done.")
