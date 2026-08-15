import frappe
from frappe.utils import now_datetime, getdate

from stylo_fleet.engine.activity import log_activity
from stylo_fleet.engine.availability import recompute_availability
from stylo_fleet.engine.location import update_location
from stylo_fleet.utils.auth import require_role, PARAMEDIC_ROLE, OPERATIONS_ROLE
from stylo_fleet.api.scheduling import reconcile_assignment


@frappe.whitelist()
def start_shift(ambulance, paramedic, latitude=None, longitude=None, start_check_result=None):
	"""Start a shift: create + submit an Ambulance Shift, assign the paramedic to the ambulance."""
	require_role(PARAMEDIC_ROLE, OPERATIONS_ROLE)
	amb = frappe.get_doc("Ambulance", ambulance)

	if not amb.active:
		frappe.throw(f"Ambulance {ambulance} is inactive.")
	if amb.current_shift:
		frappe.throw(f"Ambulance {ambulance} already has an open shift ({amb.current_shift}).")

	shift = frappe.new_doc("Ambulance Shift")
	shift.ambulance = ambulance
	shift.paramedic = paramedic
	shift.status = "Open"
	shift.start_datetime = now_datetime()
	shift.start_latitude = latitude
	shift.start_longitude = longitude
	shift.start_check_result = start_check_result
	shift.insert(ignore_permissions=True)
	shift.submit()

	amb.current_paramedic = paramedic
	amb.current_shift = shift.name
	amb.assignment_start = shift.start_datetime
	update_location(amb, latitude, longitude)
	recompute_availability(amb)
	amb.operational_status = "Available" if amb.availability_status in ("Available", "Warning") else "Unavailable"
	amb.save(ignore_permissions=True)

	log_activity(
		activity_type="Shift Started",
		ambulance=ambulance,
		shift=shift.name,
		paramedic=paramedic,
		latitude=latitude,
		longitude=longitude,
		new_status=amb.operational_status,
		remarks=start_check_result,
	)

	reconcile_assignment(ambulance, paramedic, shift.name, getdate(shift.start_datetime))

	frappe.db.commit()
	return shift.name


@frappe.whitelist()
def end_shift(shift, latitude=None, longitude=None, end_check_result=None):
	"""End a shift: close the Ambulance Shift, clear the ambulance's driver assignment.

	Per spec: does not reset kit/cleanliness/mechanical readiness — only the assignment closes.
	"""
	require_role(PARAMEDIC_ROLE, OPERATIONS_ROLE)
	shift_doc = frappe.get_doc("Ambulance Shift", shift)

	if shift_doc.status != "Open":
		frappe.throw(f"Shift {shift} is not open.")

	amb = frappe.get_doc("Ambulance", shift_doc.ambulance)
	if amb.operational_status == "On Call":
		frappe.throw("Cannot end shift while ambulance is On Call. Complete the active call first.")

	shift_doc.end_datetime = now_datetime()
	shift_doc.end_latitude = latitude
	shift_doc.end_longitude = longitude
	shift_doc.end_check_result = end_check_result
	shift_doc.status = "Closed"
	shift_doc.save(ignore_permissions=True)

	previous_status = amb.operational_status
	amb.current_paramedic = None
	amb.current_shift = None
	amb.assignment_start = None
	update_location(amb, latitude, longitude)
	recompute_availability(amb)  # will resolve to Unavailable / No Active Driver (BR-11)
	amb.operational_status = "Unavailable"
	amb.save(ignore_permissions=True)

	log_activity(
		activity_type="Shift Ended",
		ambulance=shift_doc.ambulance,
		shift=shift_doc.name,
		paramedic=shift_doc.paramedic,
		latitude=latitude,
		longitude=longitude,
		previous_status=previous_status,
		new_status=amb.operational_status,
		remarks=end_check_result,
	)

	frappe.db.commit()
	return shift_doc.name
