import frappe
from frappe.utils import now_datetime

from stylo_fleet.engine.activity import log_activity
from stylo_fleet.engine.availability import recompute_availability
from stylo_fleet.engine.readiness import (
	apply_cleaning_issue,
	apply_mechanical_issue,
	resolve_cleaning,
	resolve_mechanical,
)
from stylo_fleet.engine.location import update_location
from stylo_fleet.utils.auth import require_role, PARAMEDIC_ROLE, STATION_ROLE, OPERATIONS_ROLE

ISSUE_ACTIVITY_TYPE = {"Cleaning": "Cleaning Required", "Mechanical": "Mechanical Issue"}
RESOLVE_ACTIVITY_TYPE = {"Cleaning": "Cleaning Completed", "Mechanical": "Maintenance Completed"}


def create_issue(ambulance_doc, issue_type, category=None, severity=None, description=None, photo=None):
	"""Create + submit an Ambulance Issue and apply its effect to the given
	(already loaded) Ambulance document, in memory only — caller saves the
	ambulance document. Used both by the standalone report_issue() endpoint and
	by complete_call(), so cleaning/mechanical reporting always goes through one
	audited path instead of Complete Call silently writing status fields.
	"""
	issue = frappe.new_doc("Ambulance Issue")
	issue.ambulance = ambulance_doc.name
	issue.issue_type = issue_type
	issue.category = category
	issue.severity = severity
	issue.description = description
	issue.photo = photo
	issue.reported_by = frappe.session.user
	issue.reported_at = now_datetime()
	issue.status = "Open"
	issue.insert(ignore_permissions=True)
	issue.submit()

	if issue_type == "Cleaning":
		apply_cleaning_issue(ambulance_doc)
	else:
		apply_mechanical_issue(ambulance_doc, severity)

	log_activity(
		activity_type=ISSUE_ACTIVITY_TYPE[issue_type],
		ambulance=ambulance_doc.name,
		shift=ambulance_doc.current_shift,
		paramedic=ambulance_doc.current_paramedic,
		remarks=description,
		reference_doctype="Ambulance Issue",
		reference_transaction=issue.name,
	)
	return issue.name


@frappe.whitelist()
def report_issue(ambulance, issue_type, category=None, severity=None, description=None, photo=None, latitude=None, longitude=None):
	"""Standalone Report Issue action — spec allows reporting during a shift,
	not only at Complete Call.
	"""
	require_role(PARAMEDIC_ROLE, STATION_ROLE, OPERATIONS_ROLE)
	amb = frappe.get_doc("Ambulance", ambulance)
	issue_name = create_issue(amb, issue_type, category, severity, description, photo)

	update_location(amb, latitude, longitude)
	if amb.operational_status != "On Call":
		recompute_availability(amb)
		amb.operational_status = "Available" if amb.availability_status in ("Available", "Warning") else "Unavailable"
	amb.save(ignore_permissions=True)

	frappe.db.commit()
	return issue_name


@frappe.whitelist()
def resolve_issue(issue, resolution_remarks=None):
	require_role(STATION_ROLE, OPERATIONS_ROLE)
	issue_doc = frappe.get_doc("Ambulance Issue", issue)
	if issue_doc.status != "Open":
		frappe.throw(f"Issue {issue} is not open.")

	amb = frappe.get_doc("Ambulance", issue_doc.ambulance)

	if issue_doc.issue_type == "Cleaning":
		resolve_cleaning(amb)
	else:
		resolve_mechanical(amb)

	issue_doc.status = "Resolved"
	issue_doc.resolved_by = frappe.session.user
	issue_doc.resolved_at = now_datetime()
	issue_doc.resolution_remarks = resolution_remarks
	issue_doc.save(ignore_permissions=True)

	if amb.operational_status != "On Call":
		recompute_availability(amb)
		amb.operational_status = "Available" if amb.availability_status in ("Available", "Warning") else "Unavailable"
	amb.save(ignore_permissions=True)

	log_activity(
		activity_type=RESOLVE_ACTIVITY_TYPE[issue_doc.issue_type],
		ambulance=amb.name,
		shift=amb.current_shift,
		paramedic=amb.current_paramedic,
		new_status=amb.operational_status,
		remarks=resolution_remarks,
		reference_doctype="Ambulance Issue",
		reference_transaction=issue_doc.name,
	)

	frappe.db.commit()
	return issue_doc.name
