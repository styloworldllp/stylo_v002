import frappe
from frappe.utils import now_datetime, cint

from stylo_fleet.engine.activity import log_activity
from stylo_fleet.engine.availability import recompute_availability
from stylo_fleet.engine.kits import refill_kits
from stylo_fleet.engine.location import update_location
from stylo_fleet.utils.auth import require_role, PARAMEDIC_ROLE, STATION_ROLE, OPERATIONS_ROLE, ADMIN_ROLE

REFILL_TRIGGER_STATUSES = {"Refill Due", "Insufficient", "No Kits"}


def create_refill_request(ambulance):
	"""Create a Pending Ambulance Refill for this ambulance, unless one is already open.

	Per spec §21: prevent duplicate open refill records for the same ambulance.
	Called automatically from complete_call() when kit_status warrants it, but can
	also be called directly (e.g. manually flagged by operations).
	"""
	existing = frappe.db.exists("Ambulance Refill", {"ambulance": ambulance, "status": "Pending"})
	if existing:
		return existing

	amb = frappe.get_doc("Ambulance", ambulance)
	balance_before = amb.available_kits or 0
	required_to_full = (amb.kit_capacity or 0) - balance_before

	refill = frappe.new_doc("Ambulance Refill")
	refill.ambulance = ambulance
	refill.station = amb.base_station
	refill.status = "Pending"
	refill.requested_at = now_datetime()
	refill.balance_before_refill = balance_before
	refill.required_to_full = required_to_full
	refill.expected_load_quantity = required_to_full  # default refill target = full capacity
	refill.insert(ignore_permissions=True)
	refill.submit()

	log_activity(
		activity_type="Refill Requested",
		ambulance=ambulance,
		shift=amb.current_shift,
		paramedic=amb.current_paramedic,
		kit_balance_before=balance_before,
		kit_balance_after=balance_before,
		reference_doctype="Ambulance Refill",
		reference_transaction=refill.name,
	)

	frappe.db.commit()
	return refill.name


@frappe.whitelist()
def proceed_to_refill(ambulance, latitude=None, longitude=None):
	"""Paramedic taps Proceed to Refill Station: ambulance starts travelling to the station."""
	require_role(PARAMEDIC_ROLE, OPERATIONS_ROLE)
	amb = frappe.get_doc("Ambulance", ambulance)

	pending_refill = frappe.db.exists("Ambulance Refill", {"ambulance": ambulance, "status": "Pending"})
	if not pending_refill:
		frappe.throw(f"Ambulance {ambulance} has no pending refill request.")
	if amb.operational_status == "On Call":
		frappe.throw(f"Ambulance {ambulance} is On Call and cannot proceed to refill.")

	amb.operational_status = "Going for Refill"
	update_location(amb, latitude, longitude)
	amb.save(ignore_permissions=True)
	frappe.db.commit()
	return pending_refill


@frappe.whitelist()
def confirm_refill(refill, actual_loaded_quantity=None, exception_reason=None, station=None):
	"""Station operator confirms kits physically loaded. Per spec §8.5/§7.1:
	defaults to the expected quantity; only alter for a shortage, which then
	requires a mandatory exception reason.
	"""
	require_role(STATION_ROLE, OPERATIONS_ROLE)
	refill_doc = frappe.get_doc("Ambulance Refill", refill)
	if refill_doc.status != "Pending":
		frappe.throw(f"Refill {refill} is not pending.")

	# Station-scoping: a plain Station Operator may only confirm refills for
	# their own station (per user decision — Station console is scoped to
	# their assigned station). Operations/Admin/System Manager act fleet-wide.
	user_roles = set(frappe.get_roles())
	if not user_roles.intersection({OPERATIONS_ROLE, ADMIN_ROLE, "System Manager"}):
		operator_station = frappe.db.get_value("Station Operator", {"user": frappe.session.user}, "station")
		if not operator_station or operator_station != refill_doc.station:
			frappe.throw(f"You can only confirm refills for your own station ({operator_station or 'none assigned'}).")

	if actual_loaded_quantity is None:
		actual_loaded_quantity = refill_doc.expected_load_quantity
	actual_loaded_quantity = cint(actual_loaded_quantity)

	if actual_loaded_quantity < refill_doc.expected_load_quantity and not exception_reason:
		frappe.throw("Exception reason is mandatory when actual loaded quantity is less than expected.")

	amb = frappe.get_doc("Ambulance", refill_doc.ambulance)
	balance_before, balance_after = refill_kits(amb, actual_loaded_quantity)

	refill_doc.station = station or refill_doc.station
	refill_doc.actual_loaded_quantity = actual_loaded_quantity
	refill_doc.balance_after_refill = balance_after
	refill_doc.exception_reason = exception_reason
	refill_doc.completed_by = frappe.session.user
	refill_doc.completed_at = now_datetime()
	refill_doc.status = "Completed"
	refill_doc.save(ignore_permissions=True)

	if amb.operational_status in ("Going for Refill", "At Refill Station"):
		recompute_availability(amb)
		amb.operational_status = "Available" if amb.availability_status in ("Available", "Warning") else "Unavailable"
	amb.save(ignore_permissions=True)

	log_activity(
		activity_type="Refill Completed",
		ambulance=refill_doc.ambulance,
		shift=amb.current_shift,
		paramedic=amb.current_paramedic,
		new_status=amb.operational_status,
		kit_balance_before=balance_before,
		kit_balance_after=balance_after,
		remarks=exception_reason,
		reference_doctype="Ambulance Refill",
		reference_transaction=refill_doc.name,
	)

	frappe.db.commit()
	return refill_doc.name
