"""
Tool executor — maps tool names to Frappe operations.
All operations run under the current frappe.session.user context (permissions enforced).
Tools that need browser-side execution return {"_action": {...}} which the frontend processes.
"""
import json

import frappe


def execute_tool(name: str, inputs: dict) -> dict:
	_map = {
		"search_records": _search_records,
		"get_record": _get_record,
		"get_doctype_meta": _get_doctype_meta,
		"run_report": _run_report,
		"global_search": _global_search,
		"count_records": _count_records,
		"create_record": _create_record,
		"update_record": _update_record,
		"submit_document": _submit_document,
		"cancel_document": _cancel_document,
		"delete_record": _delete_record,
		"navigate_to": _navigate_to,
		"get_value": _get_value,
		"get_system_info": _get_system_info,
	}
	fn = _map.get(name)
	if not fn:
		return {"error": f"Unknown tool: {name}"}
	try:
		return fn(**inputs)
	except frappe.PermissionError as e:
		return {"error": f"Permission denied: {e}"}
	except frappe.DoesNotExistError as e:
		return {"error": f"Record not found: {e}"}
	except Exception as e:
		return {"error": str(e)}


# ── Read ──────────────────────────────────────────────────────────────────────

def _search_records(doctype: str, filters: dict = None, fields: list = None, limit: int = 20, order_by: str = None) -> dict:
	if not frappe.has_permission(doctype, "read"):
		return {"error": f"No read permission on {doctype}"}

	default_fields = ["name", "modified"]
	meta = frappe.get_meta(doctype)
	# Auto-add meaningful display fields
	for fname in ("title", "subject", "customer", "supplier", "employee", "full_name", "status", "grand_total"):
		if meta.has_field(fname) and fname not in default_fields:
			default_fields.append(fname)
			if len(default_fields) >= 6:
				break

	kwargs = {
		"doctype": doctype,
		"filters": filters or [],
		"fields": fields or default_fields,
		"limit": min(int(limit), 100),
	}
	if order_by:
		kwargs["order_by"] = order_by

	records = frappe.get_list(**kwargs)
	return {"doctype": doctype, "count": len(records), "records": records}


def _get_record(doctype: str, name: str) -> dict:
	if not frappe.has_permission(doctype, "read", doc=name):
		return {"error": f"No read permission on {doctype}/{name}"}
	doc = frappe.get_doc(doctype, name)
	# Return as dict, excluding large/binary fields
	data = doc.as_dict()
	# Strip attachment/html noise
	for f in doc.meta.fields:
		if f.fieldtype in ("Attach", "Attach Image", "HTML", "Text Editor") and f.fieldname in data:
			data[f.fieldname] = "[content hidden]"
	return {"doctype": doctype, "name": name, "data": data}


def _get_doctype_meta(doctype: str) -> dict:
	if not frappe.has_permission(doctype, "read"):
		return {"error": f"No read permission on {doctype}"}
	meta = frappe.get_meta(doctype)
	fields = []
	skip_types = {"Section Break", "Column Break", "HTML", "Heading", "Tab Break", "Button"}
	for f in meta.fields:
		if f.fieldtype in skip_types:
			continue
		fields.append({
			"fieldname": f.fieldname,
			"label": f.label,
			"fieldtype": f.fieldtype,
			"required": bool(f.reqd),
			"options": f.options if f.fieldtype in ("Select", "Link", "Table") else None,
		})
	return {
		"doctype": doctype,
		"is_single": bool(meta.issingle),
		"is_submittable": bool(meta.is_submittable),
		"fields": fields,
	}


def _run_report(report_name: str, filters: dict = None) -> dict:
	try:
		from frappe.desk.query_report import run
		result = run(report_name, filters or {})
		return {
			"report": report_name,
			"columns": result.get("columns", []),
			"data": result.get("result", [])[:50],  # Cap rows
			"total_rows": len(result.get("result", [])),
		}
	except Exception as e:
		return {"error": str(e)}


def _global_search(query: str) -> dict:
	try:
		from frappe.utils.global_search import search
		results = search(query, start=0, limit=20)
		return {"query": query, "results": results}
	except Exception as e:
		return {"error": str(e)}


def _count_records(doctype: str, filters: dict = None) -> dict:
	if not frappe.has_permission(doctype, "read"):
		return {"error": f"No read permission on {doctype}"}
	count = frappe.db.count(doctype, filters or [])
	return {"doctype": doctype, "filters": filters, "count": count}


# ── Write ─────────────────────────────────────────────────────────────────────

def _create_record(doctype: str, values: dict) -> dict:
	if not frappe.has_permission(doctype, "create"):
		return {"error": f"No create permission on {doctype}"}
	doc = frappe.new_doc(doctype)
	for k, v in values.items():
		doc.set(k, v)
	doc.insert(ignore_permissions=False)
	frappe.db.commit()
	return {
		"success": True,
		"doctype": doctype,
		"name": doc.name,
		"message": f"Created {doctype}: {doc.name}",
		"_action": {"type": "open_form", "doctype": doctype, "name": doc.name},
	}


def _update_record(doctype: str, name: str, values: dict) -> dict:
	if not frappe.has_permission(doctype, "write", doc=name):
		return {"error": f"No write permission on {doctype}/{name}"}
	doc = frappe.get_doc(doctype, name)
	for k, v in values.items():
		doc.set(k, v)
	doc.save(ignore_permissions=False)
	frappe.db.commit()
	return {
		"success": True,
		"doctype": doctype,
		"name": name,
		"message": f"Updated {doctype}: {name}",
		"_action": {"type": "open_form", "doctype": doctype, "name": name},
	}


def _submit_document(doctype: str, name: str) -> dict:
	if not frappe.has_permission(doctype, "submit", doc=name):
		return {"error": f"No submit permission on {doctype}/{name}"}
	doc = frappe.get_doc(doctype, name)
	doc.submit()
	frappe.db.commit()
	return {
		"success": True,
		"message": f"Submitted {doctype}: {name}",
		"_action": {"type": "open_form", "doctype": doctype, "name": name},
	}


def _cancel_document(doctype: str, name: str) -> dict:
	if not frappe.has_permission(doctype, "cancel", doc=name):
		return {"error": f"No cancel permission on {doctype}/{name}"}
	doc = frappe.get_doc(doctype, name)
	doc.cancel()
	frappe.db.commit()
	return {
		"success": True,
		"message": f"Cancelled {doctype}: {name}",
		"_action": {"type": "open_form", "doctype": doctype, "name": name},
	}


def _delete_record(doctype: str, name: str) -> dict:
	if not frappe.has_permission(doctype, "delete", doc=name):
		return {"error": f"No delete permission on {doctype}/{name}"}
	frappe.delete_doc(doctype, name, ignore_permissions=False)
	frappe.db.commit()
	return {"success": True, "message": f"Deleted {doctype}: {name}"}


# ── Navigation (browser-side) ─────────────────────────────────────────────────

def _navigate_to(type: str, doctype: str = None, name: str = None,
				 workspace: str = None, page: str = None, filters: dict = None) -> dict:
	route_map = {
		"list": ["List", doctype, "List"],
		"form": ["Form", doctype, name],
		"workspace": ["Workspaces", workspace],
		"page": [page],
	}
	route = route_map.get(type, [])
	route = [r for r in route if r]  # strip Nones

	action = {"type": "navigate", "route": route}
	if filters and type == "list":
		action["filters"] = filters

	return {
		"success": True,
		"message": f"Navigating to {' > '.join(str(r) for r in route)}",
		"_action": action,
	}


# ── Utility ───────────────────────────────────────────────────────────────────

def _get_value(doctype: str, name: str, fieldname: str) -> dict:
	if not frappe.has_permission(doctype, "read", doc=name):
		return {"error": "No read permission"}
	value = frappe.db.get_value(doctype, name, fieldname)
	return {"doctype": doctype, "name": name, "fieldname": fieldname, "value": value}


def _get_system_info() -> dict:
	defaults = frappe.db.get_value(
		"Global Defaults", None,
		["default_company", "default_currency"],
		as_dict=True,
	) or {}
	user = frappe.get_doc("User", frappe.session.user)
	return {
		"company": defaults.get("default_company"),
		"currency": defaults.get("default_currency"),
		"user": frappe.session.user,
		"full_name": user.full_name,
		"roles": frappe.get_roles(frappe.session.user),
		"today": frappe.utils.today(),
	}
