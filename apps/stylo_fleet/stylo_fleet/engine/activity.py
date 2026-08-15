import frappe
from frappe.utils import now_datetime


def log_activity(
	activity_type,
	ambulance,
	shift=None,
	paramedic=None,
	latitude=None,
	longitude=None,
	previous_status=None,
	new_status=None,
	kit_balance_before=None,
	kit_balance_after=None,
	remarks=None,
	reference_doctype=None,
	reference_transaction=None,
):
	"""Create and submit an immutable Ambulance Activity record.

	This is the only path allowed to write to the activity log — every
	state-changing action in stylo_fleet must go through here rather than
	inserting an Ambulance Activity directly, so the audit trail stays complete.
	"""
	activity = frappe.new_doc("Ambulance Activity")
	activity.activity_type = activity_type
	activity.ambulance = ambulance
	activity.shift = shift
	activity.paramedic = paramedic
	activity.event_datetime = now_datetime()
	activity.latitude = latitude
	activity.longitude = longitude
	activity.previous_status = previous_status
	activity.new_status = new_status
	activity.kit_balance_before = kit_balance_before
	activity.kit_balance_after = kit_balance_after
	activity.remarks = remarks
	activity.reference_doctype = reference_doctype
	activity.reference_transaction = reference_transaction
	activity.insert(ignore_permissions=True)
	activity.submit()

	# update_modified=False: this is informational business data, not a real
	# revision — bumping `modified` here would desync any in-memory Ambulance
	# doc a caller still holds and later saves (TimestampMismatchError).
	frappe.db.set_value(
		"Ambulance", ambulance, "last_activity_at", activity.event_datetime, update_modified=False
	)

	return activity.name
