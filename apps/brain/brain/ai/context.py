"""
Builds runtime context about the current Frappe state to include in the system prompt.
Called fresh on every chat request.
"""
import frappe


def get_page_context(route: list = None, doctype: str = None, doc_name: str = None) -> dict:
	"""
	Called by the frontend with the current route info.
	Returns a context dict that's embedded into the system prompt.
	"""
	ctx = {
		"current_route": route or [],
		"current_doctype": doctype,
		"current_doc": doc_name,
	}

	# Current user profile
	try:
		user = frappe.get_doc("User", frappe.session.user)
		ctx["user_full_name"] = user.full_name
		ctx["user_email"] = frappe.session.user
		ctx["user_roles"] = frappe.get_roles(frappe.session.user)
	except Exception:
		ctx["user_full_name"] = frappe.session.user
		ctx["user_roles"] = []

	# Company & currency
	try:
		defaults = frappe.db.get_value(
			"Global Defaults", None,
			["default_company", "default_currency"],
			as_dict=True,
		) or {}
		ctx["company"] = defaults.get("default_company", "")
		ctx["currency"] = defaults.get("default_currency", "")
	except Exception:
		ctx["company"] = ""
		ctx["currency"] = ""

	# If viewing a specific form, summarise the document
	if doctype and doc_name:
		try:
			if frappe.has_permission(doctype, "read", doc=doc_name):
				doc = frappe.get_doc(doctype, doc_name)
				ctx["current_doc_summary"] = _summarise_doc(doc)
		except Exception:
			pass

	return ctx


def get_accessible_doctypes() -> list[str]:
	"""Return doctypes the current user can at least read."""
	try:
		all_dts = [d.name for d in frappe.get_all("DocType", filters={"istable": 0, "issingle": 0}, fields=["name"])]
		accessible = [dt for dt in all_dts if frappe.has_permission(dt, "read")]
		return sorted(accessible)
	except Exception:
		return []


def _summarise_doc(doc) -> dict:
	"""Pull key fields for context (skip large/binary content)."""
	skip_types = {"Text", "Text Editor", "HTML", "Attach", "Attach Image", "Long Text"}
	summary = {"doctype": doc.doctype, "name": doc.name}
	for f in doc.meta.fields[:20]:  # First 20 fields
		if f.fieldtype not in skip_types and hasattr(doc, f.fieldname):
			val = doc.get(f.fieldname)
			if val is not None and val != "":
				summary[f.fieldname] = str(val)
	return summary
