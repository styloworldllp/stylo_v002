import frappe
from frappe.utils import today

from stylo_fleet.utils.auth import require_role, OPERATIONS_ROLE

BLOCKING_MECHANICAL_STATUSES = {"Maintenance Required", "Breakdown"}


def _count_by(doctype, fieldname, filters=None):
	rows = frappe.get_all(
		doctype, filters=filters or {}, fields=[fieldname, {"COUNT": "name", "as": "count"}], group_by=fieldname
	)
	return {row[fieldname]: row["count"] for row in rows if row[fieldname]}


@frappe.whitelist()
def get_dashboard_data():
	"""Everything the Fleet Analytics dashboard needs, in one call."""
	require_role(OPERATIONS_ROLE)

	ambulances = frappe.get_all(
		"Ambulance",
		filters={"active": 1},
		fields=[
			"name", "base_station", "operational_status", "availability_status",
			"kit_status", "cleanliness_status", "mechanical_status", "current_paramedic",
			"gps_status",
		],
	)
	total_active = len(ambulances)
	available_now = sum(1 for a in ambulances if a.availability_status == "Available")
	on_call = sum(1 for a in ambulances if a.operational_status == "On Call")
	refill_due_or_insufficient = sum(1 for a in ambulances if a.kit_status in ("Refill Due", "Insufficient", "No Kits"))
	maintenance_or_breakdown = sum(1 for a in ambulances if a.mechanical_status in BLOCKING_MECHANICAL_STATUSES)

	open_issues = frappe.get_all(
		"Ambulance Issue",
		filters={"status": "Open"},
		fields=["name", "ambulance", "issue_type", "severity", "description", "reported_at"],
		order_by="reported_at desc",
	)

	pending_refills = frappe.get_all(
		"Ambulance Refill",
		filters={"status": "Pending"},
		fields=["name", "ambulance", "station", "balance_before_refill", "expected_load_quantity", "requested_at"],
		order_by="requested_at asc",
	)

	shifts_today = frappe.db.count("Ambulance Shift", {"start_datetime": [">=", today()]})

	kits_consumed_today = frappe.db.sql(
		"""
		select coalesce(sum(kit_balance_before - kit_balance_after), 0)
		from `tabAmbulance Activity`
		where activity_type = 'Call Completed' and event_datetime >= %s
		""",
		(today(),),
	)[0][0]

	status_breakdown = _count_by("Ambulance", "operational_status", {"active": 1})
	kit_breakdown = _count_by("Ambulance", "kit_status", {"active": 1})
	station_breakdown = _count_by("Ambulance", "base_station", {"active": 1})
	activity_today_breakdown = _count_by(
		"Ambulance Activity", "activity_type", {"event_datetime": [">=", today()]}
	)

	recent_activity = frappe.get_all(
		"Ambulance Activity",
		fields=["activity_type", "ambulance", "event_datetime", "remarks", "previous_status", "new_status"],
		order_by="event_datetime desc",
		limit_page_length=12,
	)

	return {
		"kpis": {
			"total_active": total_active,
			"available_now": available_now,
			"on_call": on_call,
			"refill_due_or_insufficient": refill_due_or_insufficient,
			"maintenance_or_breakdown": maintenance_or_breakdown,
			"open_issues": len(open_issues),
			"shifts_today": shifts_today,
			"kits_consumed_today": int(kits_consumed_today or 0),
		},
		"status_breakdown": status_breakdown,
		"kit_breakdown": kit_breakdown,
		"station_breakdown": station_breakdown,
		"activity_today_breakdown": activity_today_breakdown,
		"open_issues": open_issues,
		"pending_refills": pending_refills,
		"recent_activity": recent_activity,
	}
