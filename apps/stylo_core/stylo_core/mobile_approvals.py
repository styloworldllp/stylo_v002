"""
Generic, workflow-aware approvals engine for the Stylo mobile app.

Two paths per doctype:
  1. A real Frappe Workflow is configured for it (frappe.model.workflow.get_workflow_name)
     — drive it via Frappe's own engine (apply_workflow / bulk_workflow_approval). This is
     how a customer's own customized approval chain (multi-level, custom states, whatever
     they built in Stylo BMS) gets picked up automatically, with zero app-side changes.
  2. No Workflow configured — fall back to the simple status-field + approver-role pattern
     HRMS ships out of the box (Leave Application, Expense Claim, Shift Request). This is
     the same fallback hrms.api.get_filters() already uses server-side; SIMPLE_APPROVAL_DOCTYPES
     below just makes it drivable generically from one doctype-agnostic endpoint instead of
     needing a bespoke API call per doctype.

get_pending_approvals() / submit_approval_action() merge both paths so the app never needs
to know which one a given doctype is on — and adding a new approvable doctype later (from
any module) is a config entry here, not new client code.
"""

import frappe
from frappe.model.workflow import apply_workflow, bulk_workflow_approval, get_workflow_name

# doctype -> { status_field, approver_field, pending_value, approved_value, rejected_value,
#              needs_submit, title_field, subtitle_fields }
SIMPLE_APPROVAL_DOCTYPES = {
	"Leave Application": {
		"status_field": "status",
		"approver_field": "leave_approver",
		"pending_value": "Open",
		"approved_value": "Approved",
		"rejected_value": "Rejected",
		"needs_submit": True,
		"title_field": "employee_name",
		"subtitle_fields": ["leave_type", "from_date", "to_date"],
	},
	"Expense Claim": {
		"status_field": "approval_status",
		"approver_field": "expense_approver",
		"pending_value": "Draft",
		"approved_value": "Approved",
		"rejected_value": "Rejected",
		"needs_submit": True,
		"title_field": "employee_name",
		"subtitle_fields": ["total_claimed_amount"],
	},
	"Shift Request": {
		"status_field": "status",
		"approver_field": "approver",
		"pending_value": "Draft",
		"approved_value": "Approved",
		"rejected_value": "Rejected",
		"needs_submit": True,
		"title_field": "employee_name",
		"subtitle_fields": ["shift_type", "from_date"],
	},
}


def _get_workflow_pending_for_user(user: str) -> list[dict]:
	# Field names here deliberately mirror the shape the mobile app already renders
	# (ApprovalCard.tsx reads reference_doctype/reference_name/workflow_state/subject) so
	# both sources merge into one list the UI doesn't need to branch on.
	rows = frappe.get_all(
		"Workflow Action",
		filters={"status": "Open", "user": user},
		fields=["name", "reference_doctype", "reference_name", "workflow_state", "creation"],
	)
	return [
		{
			"name": r.name,
			"reference_doctype": r.reference_doctype,
			"reference_name": r.reference_name,
			"workflow_state": r.workflow_state,
			"subject": r.reference_name,
			"creation": str(r.creation),
		}
		for r in rows
	]


def _get_simple_pending_for_user(user: str) -> list[dict]:
	out = []
	for doctype, cfg in SIMPLE_APPROVAL_DOCTYPES.items():
		# A doctype with a real Workflow configured on this site is already covered by
		# _get_workflow_pending_for_user — skip it here to avoid double-listing.
		if get_workflow_name(doctype):
			continue

		rows = frappe.get_all(
			doctype,
			filters={
				cfg["status_field"]: cfg["pending_value"],
				cfg["approver_field"]: user,
				"docstatus": 0,
			},
			fields=["name", "creation", cfg["title_field"], *cfg["subtitle_fields"]],
		)
		for r in rows:
			subject = " · ".join(str(r.get(f)) for f in cfg["subtitle_fields"] if r.get(f))
			out.append(
				{
					"name": f"{doctype}::{r.name}",
					"reference_doctype": doctype,
					"reference_name": r.name,
					"workflow_state": cfg["pending_value"],
					"subject": f"{r.get(cfg['title_field']) or r.name} — {subject}" if subject else r.get(cfg["title_field"]) or r.name,
					"creation": str(r.creation),
				}
			)
	return out


@frappe.whitelist()
def get_pending_approvals():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw("Not logged in", frappe.AuthenticationError)
	return _get_workflow_pending_for_user(user) + _get_simple_pending_for_user(user)


def _apply_simple_action(doctype: str, docname: str, action: str):
	cfg = SIMPLE_APPROVAL_DOCTYPES.get(doctype)
	if not cfg:
		frappe.throw(f"{doctype} is not configured for mobile approvals")

	doc = frappe.get_doc(doctype, docname)
	is_approver = doc.get(cfg["approver_field"]) == frappe.session.user
	if not is_approver and "System Manager" not in frappe.get_roles():
		frappe.throw("You are not the approver for this document", frappe.PermissionError)

	new_value = cfg["approved_value"] if action == "Approve" else cfg["rejected_value"]
	doc.set(cfg["status_field"], new_value)
	# ignore_permissions is safe here: approver identity was just checked explicitly above,
	# and the status field itself is permlevel-gated in the doctype's own JSON (System
	# Manager/approver roles only) — this call isn't widening who can reach this function.
	doc.save(ignore_permissions=True)
	if cfg["needs_submit"] and doc.docstatus == 0:
		doc.submit()


@frappe.whitelist()
def submit_approval_action(doctype: str, docname: str, action: str):
	"""action is 'Approve'/'Reject' for the simple path, or a real Workflow's own action
	label (whatever the customer's Workflow calls its transitions) for the workflow path."""
	if get_workflow_name(doctype):
		doc = frappe.get_doc(doctype, docname)
		apply_workflow(doc, action)
	else:
		_apply_simple_action(doctype, docname, action)
	return {"ok": True}


@frappe.whitelist()
def bulk_approval_action(doctype: str, docnames, action: str):
	if isinstance(docnames, str):
		docnames = frappe.parse_json(docnames)

	if get_workflow_name(doctype):
		# bulk_workflow_approval does its own json.loads(docnames) internally — it wants a
		# JSON string, not a list, even though every other call in this module takes a list.
		bulk_workflow_approval(frappe.as_json(docnames), doctype, action)
		return {"ok": True}

	errors = []
	for docname in docnames:
		try:
			_apply_simple_action(doctype, docname, action)
		except Exception as e:
			errors.append({"docname": docname, "error": str(e)})
	return {"ok": not errors, "errors": errors}
