import frappe
from frappe.utils import cint

from stylo_fleet.engine.activity import log_activity
from stylo_fleet.engine.availability import recompute_availability
from stylo_fleet.engine.kits import consume_kits
from stylo_fleet.api.refill import create_refill_request, REFILL_TRIGGER_STATUSES
from stylo_fleet.api.issue import create_issue
from stylo_fleet.engine.location import update_location
from stylo_fleet.utils.auth import require_role, PARAMEDIC_ROLE, OPERATIONS_ROLE


@frappe.whitelist()
def attend_call(ambulance, latitude=None, longitude=None):
	"""Start a call. Per spec §8.2: validates shift/assignment and readiness,
	captures time/location, logs a Call Started activity, sets On Call.
	"""
	require_role(PARAMEDIC_ROLE, OPERATIONS_ROLE)
	amb = frappe.get_doc("Ambulance", ambulance)

	if not amb.current_shift or not amb.current_paramedic:
		frappe.throw(f"Ambulance {ambulance} has no active shift/paramedic assigned.")
	if amb.operational_status == "On Call":
		frappe.throw(f"Ambulance {ambulance} already has an active call.")
	if amb.current_call_activity:
		frappe.throw(f"Ambulance {ambulance} already has an open call ({amb.current_call_activity}).")

	recompute_availability(amb)
	if amb.availability_status == "Unavailable":
		frappe.throw(f"Ambulance {ambulance} is not available: {amb.availability_reason}")

	previous_status = amb.operational_status
	amb.operational_status = "On Call"
	update_location(amb, latitude, longitude)
	amb.save(ignore_permissions=True)

	activity_name = log_activity(
		activity_type="Call Started",
		ambulance=ambulance,
		shift=amb.current_shift,
		paramedic=amb.current_paramedic,
		latitude=latitude,
		longitude=longitude,
		previous_status=previous_status,
		new_status="On Call",
		kit_balance_before=amb.available_kits,
		kit_balance_after=amb.available_kits,
	)

	frappe.db.set_value("Ambulance", ambulance, "current_call_activity", activity_name)
	frappe.db.commit()
	return activity_name


@frappe.whitelist()
def complete_call(
	ambulance,
	kits_consumed,
	ambulance_clean=1,
	contamination_required=0,
	mechanical_issue=0,
	issue_severity=None,
	remarks=None,
	latitude=None,
	longitude=None,
):
	"""Complete a call. Per spec §8.3/§8.4: paramedic reports kits consumed,
	cleanliness, and mechanical observations only — the system derives everything
	else (kit balance, kit status, availability, next operational status).
	"""
	require_role(PARAMEDIC_ROLE, OPERATIONS_ROLE)
	amb = frappe.get_doc("Ambulance", ambulance)

	if amb.operational_status != "On Call":
		frappe.throw(f"Ambulance {ambulance} is not currently on a call.")
	if not amb.current_call_activity:
		frappe.throw(f"Ambulance {ambulance} has no open call to complete.")

	balance_before, balance_after = consume_kits(amb, kits_consumed)

	if cint(ambulance_clean) and not cint(contamination_required):
		amb.cleanliness_status = "Clean"
	else:
		create_issue(
			amb, issue_type="Cleaning",
			category="Contamination" if cint(contamination_required) else None,
			description=remarks or "Reported at Complete Call",
		)

	if cint(mechanical_issue):
		create_issue(amb, issue_type="Mechanical", severity=issue_severity, description=remarks)

	amb.current_call_activity = None
	update_location(amb, latitude, longitude)
	recompute_availability(amb)
	amb.operational_status = "Available" if amb.availability_status in ("Available", "Warning") else "Unavailable"
	amb.save(ignore_permissions=True)

	if amb.kit_status in REFILL_TRIGGER_STATUSES:
		create_refill_request(ambulance)

	activity_name = log_activity(
		activity_type="Call Completed",
		ambulance=ambulance,
		shift=amb.current_shift,
		paramedic=amb.current_paramedic,
		latitude=latitude,
		longitude=longitude,
		previous_status="On Call",
		new_status=amb.operational_status,
		kit_balance_before=balance_before,
		kit_balance_after=balance_after,
		remarks=remarks,
	)

	frappe.db.commit()
	return activity_name
