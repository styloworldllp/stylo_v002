import frappe
from frappe.utils import now_datetime

from stylo_fleet.utils.auth import require_role, PARAMEDIC_ROLE, STATION_ROLE, OPERATIONS_ROLE, ADMIN_ROLE

ANY_ROLE = (PARAMEDIC_ROLE, STATION_ROLE, OPERATIONS_ROLE, ADMIN_ROLE)


@frappe.whitelist()
def create_ticket(subject, category, priority="Medium", description=None, related_ambulance=None, related_station=None):
	"""General operational/admin ticket — anyone can raise one. Kept
	separate from Ambulance Issue, which stays specific to cleaning/
	mechanical vehicle defects reported through the call workflow.
	"""
	require_role(*ANY_ROLE)
	doc = frappe.new_doc("Ticket")
	doc.subject = subject
	doc.category = category
	doc.priority = priority
	doc.description = description
	doc.raised_by = frappe.session.user
	doc.raised_at = now_datetime()
	doc.status = "Open"
	doc.related_ambulance = related_ambulance
	doc.related_station = related_station
	doc.insert(ignore_permissions=True)
	doc.submit()
	frappe.db.commit()
	return doc.name


@frappe.whitelist()
def close_ticket(ticket, resolution_summary, root_cause=None):
	"""Service-desk closing action — Operations/Admin only."""
	require_role(OPERATIONS_ROLE, ADMIN_ROLE)
	ticket_doc = frappe.get_doc("Ticket", ticket)
	if ticket_doc.status == "Closed":
		frappe.throw(f"Ticket {ticket} is already closed.")

	closing = frappe.new_doc("Ticket Closing")
	closing.ticket = ticket
	closing.closed_by = frappe.session.user
	closing.closed_at = now_datetime()
	closing.resolution_summary = resolution_summary
	closing.root_cause = root_cause
	closing.insert(ignore_permissions=True)
	closing.submit()

	ticket_doc.status = "Closed"
	ticket_doc.save(ignore_permissions=True)

	frappe.db.commit()
	return closing.name


@frappe.whitelist()
def get_my_tickets():
	require_role(*ANY_ROLE)
	return frappe.get_all(
		"Ticket", filters={"raised_by": frappe.session.user},
		fields=["name", "subject", "category", "priority", "status", "raised_at"],
		order_by="raised_at desc",
	)


@frappe.whitelist()
def get_open_tickets():
	require_role(OPERATIONS_ROLE, ADMIN_ROLE)
	return frappe.get_all(
		"Ticket", filters={"status": ["!=", "Closed"]},
		fields=["name", "subject", "category", "priority", "status", "raised_by", "raised_at"],
		order_by="raised_at desc",
	)
