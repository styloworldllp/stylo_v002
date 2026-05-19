"""
Custom DocType migration.
1. Reads custom DocType definitions from v14
2. Recreates them in v16 (if not already present)
3. Migrates all records
"""
import frappe
from .connection import list_custom_doctypes, get_doctype_fields_from_v14, read_batch, table_exists
from .submitted_docs import insert_record, record_exists


# Frappe fieldtypes that exist in both v14 and v16 — safe to copy as-is
_SAFE_FIELDTYPES = {
    "Data", "Int", "Float", "Currency", "Percent", "Check",
    "Small Text", "Long Text", "Text", "Text Editor",
    "Date", "Datetime", "Time",
    "Link", "Dynamic Link", "Select",
    "Attach", "Attach Image",
    "Section Break", "Column Break", "Tab Break",
    "HTML", "Heading", "Button",
    "Table", "Table MultiSelect",
    "Rating", "Color", "Icon",
    "Phone", "Email",
}


def recreate_custom_doctype(conn, doctype: str):
    """Create (or skip if exists) a custom DocType in v16 based on v14 definition."""
    if frappe.db.exists("DocType", doctype):
        return  # already there

    fields = get_doctype_fields_from_v14(conn, doctype)
    if not fields:
        return

    field_rows = []
    for f in fields:
        ft = f.get("fieldtype", "Data")
        if ft not in _SAFE_FIELDTYPES:
            ft = "Data"  # safe fallback for unknown types
        field_rows.append({
            "doctype": "DocField",
            "fieldname":  f.get("fieldname") or f.get("label", "").lower().replace(" ", "_"),
            "label":      f.get("label", ""),
            "fieldtype":  ft,
            "options":    f.get("options", ""),
            "reqd":       int(f.get("reqd") or 0),
            "default":    f.get("default", ""),
            "hidden":     int(f.get("hidden") or 0),
        })

    dt_doc = frappe.get_doc({
        "doctype":    "DocType",
        "name":       doctype,
        "module":     "Custom",
        "custom":     1,
        "fields":     field_rows,
        "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}],
    })
    dt_doc.flags.ignore_permissions = True
    dt_doc.insert()
    frappe.db.commit()


def migrate_custom_records(conn, doctype: str, job_name: str, log_fn):
    """Migrate all records for a custom DocType."""
    if not table_exists(conn, doctype):
        return 0, 0

    migrated = failed = 0
    offset = 0

    while True:
        rows = read_batch(conn, doctype, offset)
        if not rows:
            break

        for row in rows:
            try:
                if record_exists(doctype, row.get("name")):
                    migrated += 1
                    continue
                insert_record(doctype, dict(row))
                migrated += 1
                frappe.db.commit()
            except Exception as e:
                failed += 1
                log_fn(job_name, doctype, row.get("name"), str(e), "")

        offset += len(rows)

    return migrated, failed


def run_custom_phase(conn, job_name: str, log_fn, publish_fn):
    """Phase 9: detect and migrate all custom doctypes from v14."""
    custom_dts = list_custom_doctypes(conn)
    total_migrated = total_failed = 0

    for doctype in custom_dts:
        publish_fn(job_name, "Phase 9 — Custom DocTypes", doctype, 0)
        try:
            recreate_custom_doctype(conn, doctype)
        except Exception as e:
            log_fn(job_name, doctype, "__schema__", f"Could not recreate schema: {e}", "")
            continue

        m, f = migrate_custom_records(conn, doctype, job_name, log_fn)
        total_migrated += m
        total_failed += f
        publish_fn(job_name, "Phase 9 — Custom DocTypes", doctype, m)

    return total_migrated, total_failed
