import frappe

from stylo_fleet.utils.auth import require_role, PARAMEDIC_ROLE, OPERATIONS_ROLE, ADMIN_ROLE


@frappe.whitelist()
def create_assignment(ambulance, paramedic, assignment_date, shift_slot, notes=None):
	"""Roster a paramedic onto an ambulance for a future date/slot. Separate
	from Ambulance Shift, which only exists once someone actually taps Start
	Shift — this is the plan, that is the execution.
	"""
	require_role(OPERATIONS_ROLE, ADMIN_ROLE)

	existing = frappe.db.exists("Shift Assignment", {
		"ambulance": ambulance, "assignment_date": assignment_date,
		"shift_slot": shift_slot, "status": "Scheduled",
	})
	if existing:
		frappe.throw(f"Ambulance {ambulance} already has a scheduled assignment for {assignment_date} ({shift_slot}).")

	doc = frappe.new_doc("Shift Assignment")
	doc.ambulance = ambulance
	doc.paramedic = paramedic
	doc.assignment_date = assignment_date
	doc.shift_slot = shift_slot
	doc.status = "Scheduled"
	doc.notes = notes
	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.commit()
	return doc.name


@frappe.whitelist()
def get_my_schedule():
	"""Upcoming scheduled assignments for the calling paramedic."""
	require_role(PARAMEDIC_ROLE, OPERATIONS_ROLE, ADMIN_ROLE)
	paramedic = frappe.db.get_value("Paramedic", {"user": frappe.session.user}, "name")
	if not paramedic:
		return []
	return frappe.get_all(
		"Shift Assignment",
		filters={"paramedic": paramedic, "status": "Scheduled"},
		fields=["name", "ambulance", "assignment_date", "shift_slot"],
		order_by="assignment_date asc",
	)


def reconcile_assignment(ambulance, paramedic, shift_name, assignment_date):
	"""Called from start_shift(): if there's a Scheduled assignment matching
	today's Start Shift, mark it Completed and link the actual shift. Silent
	no-op if there's no matching assignment — scheduling is optional, not
	required to start a shift.
	"""
	assignment = frappe.db.get_value(
		"Shift Assignment",
		{"ambulance": ambulance, "paramedic": paramedic, "assignment_date": assignment_date, "status": "Scheduled"},
		"name",
	)
	if not assignment:
		return
	doc = frappe.get_doc("Shift Assignment", assignment)
	doc.status = "Completed"
	doc.actual_shift = shift_name
	doc.save(ignore_permissions=True)
