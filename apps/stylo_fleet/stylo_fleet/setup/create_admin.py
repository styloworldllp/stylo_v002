import frappe

ADMIN_EMAIL = "admin@nhs.stylo.io"
ADMIN_PASSWORD = "Stylo@Demo123"


def run():
	if not frappe.db.exists("User", ADMIN_EMAIL):
		user = frappe.get_doc({
			"doctype": "User",
			"email": ADMIN_EMAIL,
			"first_name": "NHS",
			"last_name": "Admin",
			"send_welcome_email": 0,
			"new_password": ADMIN_PASSWORD,
		})
		user.append("roles", {"role": "Fleet Admin"})
		user.append("roles", {"role": "System Manager"})
		user.insert(ignore_permissions=True)
		print(f"Created admin user: {ADMIN_EMAIL}")
	else:
		user = frappe.get_doc("User", ADMIN_EMAIL)
		existing = {r.role for r in user.roles}
		for role in ("Fleet Admin", "System Manager"):
			if role not in existing:
				user.append("roles", {"role": role})
		user.save(ignore_permissions=True)
		print(f"Admin user already existed, ensured roles: {ADMIN_EMAIL}")

	frappe.db.commit()
