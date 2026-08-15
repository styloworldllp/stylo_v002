import frappe

from stylo_fleet.utils.auth import require_role, OPERATIONS_ROLE, STATION_ROLE

BLOCKING_MECHANICAL_STATUSES = {"Maintenance Required", "Breakdown"}


@frappe.whitelist()
def get_control_centre_summary():
	"""Ambulance Control Centre data per spec §13.1: fleet-wide exception counts
	plus the per-ambulance status table. Fleet-wide view, so restricted to
	Operations/Admin — a paramedic only sees their own assigned ambulance per
	spec §15, not the whole fleet.
	"""
	require_role(OPERATIONS_ROLE)
	ambulances = frappe.get_all(
		"Ambulance",
		filters={"active": 1},
		fields=[
			"name as ambulance_id", "vehicle_number", "current_paramedic", "operational_status",
			"availability_status", "availability_reason", "available_kits", "kit_capacity",
			"kit_status", "cleanliness_status", "mechanical_status", "location_label",
			"last_location_at", "gps_status",
		],
	)

	summary = {
		"total_active": len(ambulances),
		"available_now": 0,
		"on_call": 0,
		"refill_due_or_insufficient": 0,
		"cleaning_required": 0,
		"maintenance_required_or_breakdown": 0,
		"no_active_paramedic": 0,
		"location_stale_or_offline": 0,
	}

	for amb in ambulances:
		if amb.availability_status == "Available":
			summary["available_now"] += 1
		if amb.operational_status == "On Call":
			summary["on_call"] += 1
		if amb.kit_status in ("Refill Due", "Insufficient", "No Kits"):
			summary["refill_due_or_insufficient"] += 1
		if amb.cleanliness_status != "Clean":
			summary["cleaning_required"] += 1
		if amb.mechanical_status in BLOCKING_MECHANICAL_STATUSES:
			summary["maintenance_required_or_breakdown"] += 1
		if not amb.current_paramedic:
			summary["no_active_paramedic"] += 1
		if amb.gps_status in ("Stale", "Offline"):
			summary["location_stale_or_offline"] += 1

	return {"summary": summary, "fleet": ambulances}


@frappe.whitelist()
def get_refill_queue():
	"""Refill Dashboard data per spec §13.2: pending queue + today's completions
	+ partial-refill exceptions. This is the station operator's own work queue,
	so Station is allowed here (unlike the fleet-wide Control Centre).
	"""
	require_role(STATION_ROLE, OPERATIONS_ROLE)
	pending = frappe.get_all(
		"Ambulance Refill",
		filters={"status": "Pending"},
		fields=[
			"name", "ambulance", "station", "balance_before_refill",
			"required_to_full", "expected_load_quantity", "requested_at",
		],
		order_by="requested_at asc",
	)

	completed_today = frappe.get_all(
		"Ambulance Refill",
		filters={"status": "Completed", "completed_at": [">=", frappe.utils.today()]},
		fields=["name", "ambulance", "actual_loaded_quantity", "completed_at"],
	)

	partial_exceptions = frappe.get_all(
		"Ambulance Refill",
		filters={"status": "Completed", "exception_reason": ["is", "set"]},
		fields=["name", "ambulance", "expected_load_quantity", "actual_loaded_quantity", "exception_reason", "completed_at"],
		order_by="completed_at desc",
		limit_page_length=50,
	)

	return {
		"pending": pending,
		"completed_today": completed_today,
		"partial_exceptions": partial_exceptions,
	}
