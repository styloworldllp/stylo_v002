"""
v14 → v16 schema differences.

FIELD_RENAMES   : {doctype: {old_fieldname: new_fieldname}}
DROPPED_FIELDS  : {doctype: [fieldname, ...]}   — removed in v16, just skip
REQUIRED_DEFAULTS: {doctype: {fieldname: value_or_callable}}
CHILD_MOVES     : fields that moved from parent to a child table
"""

import frappe

# ── Field renames ──────────────────────────────────────────────────────────────
FIELD_RENAMES = {
    "Journal Entry": {
        "cheque_no":   "reference_no",
        "cheque_date": "reference_date",
    },
    "Purchase Invoice": {
        "supplier_address": "supplier_address",   # same name, kept for explicitness
    },
    "Sales Invoice": {
        "c_form_applicable": None,  # dropped — map to None means drop
    },
    "Employee": {
        "employee_name": "employee_name",   # unchanged
        "company_email": "prefered_email",
    },
    "Payment Entry": {
        "remarks": "remarks",
    },
}

# ── Fields removed in v16 — silently drop ─────────────────────────────────────
DROPPED_FIELDS = {
    "Item": [
        "default_supplier",     # moved to Item Default child table
    ],
    "Employee": [
        "salary_currency",      # moved to hrms
        "ctc",
        "employee_grade",       # now separate DocType, still linked but field type changed
    ],
    "Sales Invoice": [
        "c_form_applicable",
        "c_form_no",
    ],
    "Customer": [
        "lead_name",            # removed in v16
    ],
    "Supplier": [
        "supp_master_name",
    ],
    "Purchase Order": [
        "supplied_items_qty",
    ],
}

# ── Required field defaults (value or zero-arg callable) ─────────────────────
def _today():
    return frappe.utils.today()


REQUIRED_DEFAULTS = {
    "Item": {
        "item_group": "All Item Groups",
        "stock_uom":  "Nos",
    },
    "Customer": {
        "customer_group": "All Customer Groups",
        "territory":      "All Territories",
        "customer_type":  "Company",
    },
    "Supplier": {
        "supplier_group": "All Supplier Groups",
        "supplier_type":  "Company",
        "country":        None,
    },
    "Employee": {
        "status":         "Active",
        "gender":         "Male",
        "date_of_joining": _today,
        "company":        lambda: frappe.defaults.get_global_default("company"),
    },
    "Sales Invoice": {
        "posting_date": _today,
        "due_date":     _today,
        "company":      lambda: frappe.defaults.get_global_default("company"),
    },
    "Purchase Invoice": {
        "posting_date": _today,
        "bill_date":    _today,
        "company":      lambda: frappe.defaults.get_global_default("company"),
    },
    "Sales Order": {
        "transaction_date": _today,
        "delivery_date":    _today,
        "company":          lambda: frappe.defaults.get_global_default("company"),
    },
    "Purchase Order": {
        "transaction_date": _today,
        "schedule_date":    _today,
        "company":          lambda: frappe.defaults.get_global_default("company"),
    },
    "Journal Entry": {
        "posting_date": _today,
        "company":      lambda: frappe.defaults.get_global_default("company"),
    },
    "Payment Entry": {
        "posting_date": _today,
        "company":      lambda: frappe.defaults.get_global_default("company"),
    },
    "Stock Entry": {
        "posting_date": _today,
        "company":      lambda: frappe.defaults.get_global_default("company"),
    },
    "BOM": {
        "company": lambda: frappe.defaults.get_global_default("company"),
    },
    "Work Order": {
        "planned_start_date": _today,
        "company":            lambda: frappe.defaults.get_global_default("company"),
    },
    "Salary Slip": {
        "posting_date": _today,
        "company":      lambda: frappe.defaults.get_global_default("company"),
    },
    "Leave Application": {
        "posting_date": _today,
        "company":      lambda: frappe.defaults.get_global_default("company"),
    },
    "Attendance": {
        "attendance_date": _today,
        "company":         lambda: frappe.defaults.get_global_default("company"),
    },
}

# ── Fields that moved to child tables in v16 ─────────────────────────────────
# These are dropped from the parent row during mapping; migrate_hr.py / engine
# handles building the child rows separately where needed.
CHILD_MOVES = {
    "Item": {
        "default_supplier": ("Item Default", "default_supplier"),
    },
}


def apply_schema_map(doctype: str, row: dict) -> dict:
    """
    Apply field renames and drop removed fields.
    Merges static rules with any AI-generated overrides cached from the schema analysis step.
    Returns a new dict safe to pass to fixup / insert.
    """
    # Merge static rules with AI-generated overrides (AI wins on conflicts)
    try:
        from .ai_helper import get_ai_schema_override
        ai = get_ai_schema_override(doctype)
    except Exception:
        ai = {}

    renames = {**FIELD_RENAMES.get(doctype, {}), **ai.get("renames", {})}
    dropped = set(DROPPED_FIELDS.get(doctype, [])) | set(ai.get("dropped", []))

    result = {}
    for k, v in row.items():
        if k in dropped:
            continue
        new_key = renames.get(k)
        if new_key is None and k in renames:
            # Explicitly mapped to None → drop
            continue
        result[new_key if new_key else k] = v

    # Inject AI-suggested required defaults (only for missing fields)
    for fieldname, default_val in ai.get("required_defaults", {}).items():
        if fieldname not in result or result[fieldname] in (None, ""):
            result[fieldname] = default_val

    return result
