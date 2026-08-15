import frappe

DEMO_PASSWORD = "Stylo@Demo123"

STATIONS = [
	{"station_name": "Central Base Station", "station_type": "Base"},
	{"station_name": "Riverside Refill Depot", "station_type": "Refill"},
	{"station_name": "Eastgate Service Center", "station_type": "Service"},
]

USERS = [
	# (email, first, last, role)
	("ravi.kumar@nhs.stylo.io", "Ravi", "Kumar", "Fleet Paramedic"),
	("anjali.sharma@nhs.stylo.io", "Anjali", "Sharma", "Fleet Paramedic"),
	("suresh.nair@nhs.stylo.io", "Suresh", "Nair", "Fleet Paramedic"),
	("meena.station@nhs.stylo.io", "Meena", "Iyer", "Fleet Station"),
	("karthik.ops@nhs.stylo.io", "Karthik", "Rao", "Fleet Operations"),
]

PARAMEDICS = [
	# (paramedic_name, user, base_station)
	("Ravi Kumar", "ravi.kumar@nhs.stylo.io", "Central Base Station"),
	("Anjali Sharma", "anjali.sharma@nhs.stylo.io", "Central Base Station"),
	("Suresh Nair", "suresh.nair@nhs.stylo.io", "Eastgate Service Center"),
]

AMBULANCES = [
	{
		"ambulance_id": "AMB-001", "vehicle_number": "KA-01-AB-1234", "vehicle_type": "Van",
		"base_station": "Central Base Station", "kit_capacity": 10,
		"minimum_operational_kits": 3, "refill_threshold": 5,
	},
	{
		"ambulance_id": "AMB-002", "vehicle_number": "KA-01-AB-5678", "vehicle_type": "Van",
		"base_station": "Central Base Station", "kit_capacity": 12,
		"minimum_operational_kits": 4, "refill_threshold": 6,
	},
	{
		"ambulance_id": "AMB-003", "vehicle_number": "KA-02-CD-9012", "vehicle_type": "Type II",
		"base_station": "Eastgate Service Center", "kit_capacity": 10,
		"minimum_operational_kits": 3, "refill_threshold": 5,
	},
]


def run():
	for s in STATIONS:
		if not frappe.db.exists("Ambulance Station", s["station_name"]):
			frappe.get_doc({"doctype": "Ambulance Station", "active": 1, **s}).insert(ignore_permissions=True)
			print(f"Created station: {s['station_name']}")

	for email, first, last, role in USERS:
		if not frappe.db.exists("User", email):
			user = frappe.get_doc({
				"doctype": "User",
				"email": email,
				"first_name": first,
				"last_name": last,
				"send_welcome_email": 0,
				"new_password": DEMO_PASSWORD,
			})
			user.append("roles", {"role": role})
			user.insert(ignore_permissions=True)
			print(f"Created user: {email} ({role})")
		else:
			user = frappe.get_doc("User", email)
			if not any(r.role == role for r in user.roles):
				user.append("roles", {"role": role})
				user.save(ignore_permissions=True)

	for name, user_email, base_station in PARAMEDICS:
		if not frappe.db.exists("Paramedic", name):
			frappe.get_doc({
				"doctype": "Paramedic",
				"paramedic_name": name,
				"user": user_email,
				"base_station": base_station,
				"eligible": 1,
				"active": 1,
			}).insert(ignore_permissions=True)
			print(f"Created paramedic: {name}")

	for a in AMBULANCES:
		if not frappe.db.exists("Ambulance", a["ambulance_id"]):
			frappe.get_doc({
				"doctype": "Ambulance",
				"active": 1,
				"available_kits": a["kit_capacity"],
				"cleanliness_status": "Clean",
				"mechanical_status": "Fit",
				**a,
			}).insert(ignore_permissions=True)
			print(f"Created ambulance: {a['ambulance_id']}")

	frappe.db.commit()
	print("Demo data seeded.")
