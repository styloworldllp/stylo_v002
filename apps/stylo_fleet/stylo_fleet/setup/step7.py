import frappe

MODULE = "Stylo Fleet"


def _make_doctype(name, fields, **kwargs):
    if frappe.db.exists("DocType", name):
        print(f"Skip (exists): {name}")
        return
    doc = frappe.new_doc("DocType")
    doc.name = name
    doc.module = MODULE
    doc.custom = 0
    doc.istable = 0
    doc.editable_grid = 1
    for k, v in kwargs.items():
        setattr(doc, k, v)
    for f in fields:
        doc.append("fields", f)
    doc.insert(ignore_permissions=True)
    print(f"Created: {name}")


def run():
    # -----------------------------------------------------------------
    # Ambulance Issue (Transaction, submittable) — Open -> Resolved,
    # same pattern as Ambulance Shift/Refill.
    # -----------------------------------------------------------------
    _make_doctype(
        "Ambulance Issue",
        fields=[
            {"fieldname": "ambulance", "label": "Ambulance", "fieldtype": "Link", "options": "Ambulance",
             "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "issue_type", "label": "Issue Type", "fieldtype": "Select",
             "options": "Cleaning\nMechanical", "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "severity", "label": "Severity", "fieldtype": "Select",
             "options": "\nObservation\nAttention Required\nBreakdown", "read_only": 1},
            {"fieldname": "column_break_issue_1", "fieldtype": "Column Break"},
            {"fieldname": "category", "label": "Category", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Open\nResolved",
             "default": "Open", "reqd": 1, "read_only": 1, "allow_on_submit": 1, "in_list_view": 1},

            {"fieldname": "section_break_issue_details", "label": "Details", "fieldtype": "Section Break"},
            {"fieldname": "description", "label": "Description", "fieldtype": "Small Text", "read_only": 1},
            {"fieldname": "photo", "label": "Photo", "fieldtype": "Attach Image", "read_only": 1},
            {"fieldname": "column_break_issue_2", "fieldtype": "Column Break"},
            {"fieldname": "reported_by", "label": "Reported By", "fieldtype": "Link", "options": "User",
             "reqd": 1, "read_only": 1},
            {"fieldname": "reported_at", "label": "Reported At", "fieldtype": "Datetime", "reqd": 1, "read_only": 1},

            {"fieldname": "section_break_issue_resolution", "label": "Resolution", "fieldtype": "Section Break"},
            {"fieldname": "resolved_by", "label": "Resolved By", "fieldtype": "Link", "options": "User",
             "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "resolved_at", "label": "Resolved At", "fieldtype": "Datetime",
             "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "resolution_remarks", "label": "Resolution Remarks", "fieldtype": "Small Text",
             "read_only": 1, "allow_on_submit": 1},
        ],
        is_submittable=1,
        autoname="format:ISSUE-{YYYY}-{#####}",
    )

    frappe.db.commit()
    print("Step 7 (Readiness) doctype done.")
