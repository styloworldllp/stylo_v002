import frappe
from frappe.utils import today

from stylo_fleet.utils.auth import require_role, STATION_ROLE, OPERATIONS_ROLE, ADMIN_ROLE


def my_station_operator():
	return frappe.db.get_value(
		"Station Operator", {"user": frappe.session.user},
		["name", "operator_name", "station", "active"], as_dict=True,
	)


@frappe.whitelist()
def get_my_station_console():
	"""Refill queue scoped to the caller's own station (per their Station
	Operator profile). Operations/Admin without such a profile see every
	station's queue — they aren't scoped, per spec §15 (Operations = Optional
	on refill confirmation, i.e. can act fleet-wide).
	"""
	require_role(STATION_ROLE, OPERATIONS_ROLE, ADMIN_ROLE)
	operator = my_station_operator()

	station_filter = {"station": operator.station} if operator else {}

	pending = frappe.get_all(
		"Ambulance Refill",
		filters={**station_filter, "status": "Pending"},
		fields=["name", "ambulance", "station", "balance_before_refill", "required_to_full", "expected_load_quantity", "requested_at"],
		order_by="requested_at asc",
	)
	completed_today = frappe.get_all(
		"Ambulance Refill",
		filters={**station_filter, "status": "Completed", "completed_at": [">=", today()]},
		fields=["name", "ambulance", "actual_loaded_quantity", "exception_reason", "completed_at"],
		order_by="completed_at desc",
	)

	return {
		"operator": operator,
		"station": operator.station if operator else None,
		"pending": pending,
		"completed_today": completed_today,
		"kits_loaded_today": sum(r.actual_loaded_quantity or 0 for r in completed_today),
	}
