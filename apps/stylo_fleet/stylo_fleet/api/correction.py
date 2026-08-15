import frappe
from frappe.utils import cint

from stylo_fleet.engine.activity import log_activity
from stylo_fleet.engine.availability import recompute_availability
from stylo_fleet.utils.auth import require_role, OPERATIONS_ROLE

INT_FIELDS = {"available_kits", "minimum_operational_kits", "refill_threshold", "kit_capacity"}
CORRECTABLE_FIELDS = INT_FIELDS | {"cleanliness_status", "mechanical_status", "operational_status"}


@frappe.whitelist()
def manual_correction(ambulance, field, new_value, reason):
	"""Manually correct a system-derived Ambulance field. Per BR-12/spec §16:
	requires an authorised role, a mandatory reason, and always produces an
	audit entry — this is the only sanctioned way to hand-edit a field that
	every other part of stylo_fleet treats as system-derived.
	"""
	require_role(OPERATIONS_ROLE)

	if field not in CORRECTABLE_FIELDS:
		frappe.throw(f"Field '{field}' cannot be manually corrected via this endpoint.")
	if not reason or not reason.strip():
		frappe.throw("A reason is mandatory for any manual correction.")

	amb = frappe.get_doc("Ambulance", ambulance)
	old_value = amb.get(field)

	if field in INT_FIELDS:
		new_value = cint(new_value)
		if new_value < 0:
			frappe.throw(f"{field} cannot be negative.")

	if str(old_value) == str(new_value):
		frappe.throw("New value is the same as the current value — nothing to correct.")

	amb.set(field, new_value)
	recompute_availability(amb)
	amb.save(ignore_permissions=True)

	activity_name = log_activity(
		activity_type="Manual Correction",
		ambulance=ambulance,
		shift=amb.current_shift,
		paramedic=amb.current_paramedic,
		previous_status=f"{field}={old_value}",
		new_status=f"{field}={new_value}",
		remarks=f"{reason} (corrected by {frappe.session.user})",
	)

	frappe.db.commit()
	return activity_name
