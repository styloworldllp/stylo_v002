"""
Insert a record into v16, optionally in Submitted state.
Uses ignore flags to bypass validation that would fail on historical data.
"""
import frappe


def insert_record(doctype: str, values: dict) -> str:
    """
    Insert a row into v16. Returns the inserted document name.
    If docstatus=1 in values, the record is inserted as Draft then
    flagged Submitted directly in the DB (avoids running submit hooks
    on historical data that may lack current mandatory validations).
    """
    values = dict(values)  # shallow copy
    docstatus = int(values.pop("docstatus", 0) or 0)

    # Strip fields that Frappe manages internally
    for f in ("creation", "modified", "owner", "modified_by", "__islocal"):
        values.pop(f, None)

    # Preserve original name / naming
    name = values.get("name")

    doc = frappe.get_doc({"doctype": doctype, **values})
    doc.flags.ignore_permissions   = True
    doc.flags.ignore_validate      = True
    doc.flags.ignore_mandatory     = True
    doc.flags.ignore_links         = True
    doc.flags.ignore_version       = True

    # If the record already exists (same name), skip it
    if name and frappe.db.exists(doctype, name):
        return name

    doc.insert(ignore_permissions=True)

    if docstatus == 1:
        # Set submitted state directly — bypass submit hooks for historical docs
        frappe.db.set_value(doctype, doc.name, "docstatus", 1)

    return doc.name


def record_exists(doctype: str, name: str) -> bool:
    return bool(frappe.db.exists(doctype, name))
