import frappe
from frappe.utils import cint

from stylo_fleet.utils.auth import require_role, ADMIN_ROLE


def _create_user_with_role(email, first_name, last_name, role, password=None):
	if frappe.db.exists("User", email):
		user = frappe.get_doc("User", email)
		if not any(r.role == role for r in user.roles):
			user.append("roles", {"role": role})
			user.save(ignore_permissions=True)
		return user
	user = frappe.get_doc({
		"doctype": "User",
		"email": email,
		"first_name": first_name,
		"last_name": last_name or "",
		"send_welcome_email": 0,
	})
	if password:
		user.new_password = password
	user.append("roles", {"role": role})
	user.insert(ignore_permissions=True)
	return user


def _split_name(full_name):
	parts = full_name.strip().split(" ", 1)
	return parts[0], (parts[1] if len(parts) > 1 else "")


@frappe.whitelist()
def get_people():
	require_role(ADMIN_ROLE)
	paramedics = frappe.get_all(
		"Paramedic", fields=["name", "paramedic_name", "user", "base_station", "active"], order_by="paramedic_name"
	)
	station_operators = frappe.get_all(
		"Station Operator", fields=["name", "operator_name", "user", "station", "active"], order_by="operator_name"
	)
	ops_rows = frappe.get_all(
		"Has Role", filters={"role": "Fleet Operations", "parenttype": "User"}, fields=["parent as user"]
	)
	operations = []
	for row in ops_rows:
		u = frappe.db.get_value("User", row.user, ["full_name", "enabled"], as_dict=True)
		if u:
			operations.append({"user": row.user, "full_name": u.full_name, "enabled": u.enabled})

	return {"paramedics": paramedics, "station_operators": station_operators, "operations": operations}


@frappe.whitelist()
def get_master_options():
	require_role(ADMIN_ROLE)
	return {
		"stations": frappe.get_all("Ambulance Station", filters={"active": 1}, pluck="name"),
	}


@frappe.whitelist()
def create_paramedic(full_name, email, base_station, password=None):
	require_role(ADMIN_ROLE)
	if frappe.db.exists("Paramedic", full_name):
		frappe.throw(f"Paramedic {full_name} already exists.")
	first, last = _split_name(full_name)
	_create_user_with_role(email, first, last, "Fleet Paramedic", password)
	frappe.get_doc({
		"doctype": "Paramedic",
		"paramedic_name": full_name,
		"user": email,
		"base_station": base_station,
		"eligible": 1,
		"active": 1,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return full_name


@frappe.whitelist()
def create_station_operator(full_name, email, station, password=None):
	require_role(ADMIN_ROLE)
	if frappe.db.exists("Station Operator", full_name):
		frappe.throw(f"Station Operator {full_name} already exists.")
	first, last = _split_name(full_name)
	_create_user_with_role(email, first, last, "Fleet Station", password)
	frappe.get_doc({
		"doctype": "Station Operator",
		"operator_name": full_name,
		"user": email,
		"station": station,
		"active": 1,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return full_name


@frappe.whitelist()
def create_operations_user(full_name, email, password=None):
	require_role(ADMIN_ROLE)
	first, last = _split_name(full_name)
	_create_user_with_role(email, first, last, "Fleet Operations", password)
	frappe.db.commit()
	return email


@frappe.whitelist()
def create_ambulance(ambulance_id, vehicle_number, vehicle_type, base_station,
					  kit_capacity, minimum_operational_kits, refill_threshold):
	require_role(ADMIN_ROLE)
	if frappe.db.exists("Ambulance", ambulance_id):
		frappe.throw(f"Ambulance {ambulance_id} already exists.")
	kit_capacity = cint(kit_capacity)
	frappe.get_doc({
		"doctype": "Ambulance",
		"ambulance_id": ambulance_id,
		"vehicle_number": vehicle_number,
		"vehicle_type": vehicle_type,
		"base_station": base_station,
		"active": 1,
		"kit_capacity": kit_capacity,
		"available_kits": kit_capacity,
		"minimum_operational_kits": cint(minimum_operational_kits),
		"refill_threshold": cint(refill_threshold),
		"cleanliness_status": "Clean",
		"mechanical_status": "Fit",
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return ambulance_id


@frappe.whitelist()
def create_station(station_name, station_type):
	require_role(ADMIN_ROLE)
	if frappe.db.exists("Ambulance Station", station_name):
		frappe.throw(f"Station {station_name} already exists.")
	frappe.get_doc({
		"doctype": "Ambulance Station",
		"station_name": station_name,
		"station_type": station_type,
		"active": 1,
	}).insert(ignore_permissions=True)
	frappe.db.commit()
	return station_name
