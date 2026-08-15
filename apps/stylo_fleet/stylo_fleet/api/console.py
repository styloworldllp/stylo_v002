import frappe

from stylo_fleet.utils.auth import require_role, PARAMEDIC_ROLE, OPERATIONS_ROLE, ADMIN_ROLE


def _my_paramedic():
	paramedic = frappe.db.get_value(
		"Paramedic", {"user": frappe.session.user}, ["name", "paramedic_name", "user", "base_station", "active"],
		as_dict=True,
	)
	if not paramedic:
		frappe.throw("No Paramedic profile is linked to your user account. Contact Operations.")
	if not paramedic.active:
		frappe.throw("Your Paramedic profile is inactive. Contact Operations.")
	return paramedic


@frappe.whitelist()
def get_my_console():
	"""Everything the Ambulance Console page needs in one call: the acting
	paramedic's profile, their currently assigned ambulance (if any), any
	pending refill for it, and today's activity log (the "daily log").
	"""
	require_role(PARAMEDIC_ROLE, OPERATIONS_ROLE, ADMIN_ROLE)
	paramedic = _my_paramedic()

	ambulance_name = frappe.db.get_value("Ambulance", {"current_paramedic": paramedic.name}, "name")
	ambulance = frappe.get_doc("Ambulance", ambulance_name).as_dict() if ambulance_name else None

	pending_refill = None
	if ambulance_name:
		pending_refill = frappe.db.get_value(
			"Ambulance Refill", {"ambulance": ambulance_name, "status": "Pending"}, "name"
		)

	today_activity = []
	if ambulance_name:
		today_activity = frappe.get_all(
			"Ambulance Activity",
			filters={"ambulance": ambulance_name, "event_datetime": [">=", frappe.utils.today()]},
			fields=[
				"activity_type", "event_datetime", "remarks",
				"kit_balance_before", "kit_balance_after", "previous_status", "new_status",
			],
			order_by="event_datetime desc",
		)

	return {
		"paramedic": paramedic,
		"ambulance": ambulance,
		"pending_refill": pending_refill,
		"today_activity": today_activity,
	}


@frappe.whitelist()
def get_selectable_ambulances():
	"""Ambulances the current paramedic could Start Shift on: active, unassigned,
	preferring their home base station but not restricted to it (spec doesn't
	forbid covering another station).
	"""
	require_role(PARAMEDIC_ROLE, OPERATIONS_ROLE, ADMIN_ROLE)
	paramedic = _my_paramedic()

	filters = {"active": 1, "current_paramedic": ""}
	fields = ["name", "vehicle_number", "base_station", "operational_status"]
	ambulances = frappe.get_all(
		"Ambulance", filters=filters, fields=fields, order_by="base_station, name"
	)

	if paramedic.base_station:
		ambulances.sort(key=lambda a: a.base_station != paramedic.base_station)

	return ambulances


@frappe.whitelist()
def get_my_stats():
	"""Personal performance stats for the paramedic console — lifetime totals,
	not just today, so a new paramedic isn't stuck looking at zeroes all day.
	"""
	require_role(PARAMEDIC_ROLE, OPERATIONS_ROLE, ADMIN_ROLE)
	paramedic = _my_paramedic()

	total_shifts = frappe.db.count("Ambulance Shift", {"paramedic": paramedic.name})
	total_calls = frappe.db.count(
		"Ambulance Activity", {"paramedic": paramedic.name, "activity_type": "Call Completed"}
	)
	kits_consumed = frappe.db.sql(
		"""
		select coalesce(sum(kit_balance_before - kit_balance_after), 0)
		from `tabAmbulance Activity`
		where paramedic = %s and activity_type = 'Call Completed'
		""",
		(paramedic.name,),
	)[0][0]
	issues_reported = frappe.db.count("Ambulance Issue", {"reported_by": paramedic.user})

	return {
		"total_shifts": total_shifts,
		"total_calls": total_calls,
		"kits_consumed": int(kits_consumed or 0),
		"issues_reported": issues_reported,
	}
