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
    # Ambulance Refill (Transaction, submittable) — Pending -> Completed,
    # mirroring the Ambulance Shift Open -> Closed pattern: created +
    # submitted immediately as Pending, station operator confirms by
    # updating allow_on_submit fields.
    # -----------------------------------------------------------------
    _make_doctype(
        "Ambulance Refill",
        fields=[
            {"fieldname": "ambulance", "label": "Ambulance", "fieldtype": "Link", "options": "Ambulance",
             "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "station", "label": "Station", "fieldtype": "Link", "options": "Ambulance Station",
             "allow_on_submit": 1, "in_list_view": 1},
            {"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Pending\nCompleted",
             "default": "Pending", "reqd": 1, "read_only": 1, "allow_on_submit": 1, "in_list_view": 1},
            {"fieldname": "column_break_refill_1", "fieldtype": "Column Break"},
            {"fieldname": "requested_at", "label": "Requested At", "fieldtype": "Datetime", "reqd": 1, "read_only": 1},
            {"fieldname": "balance_before_refill", "label": "Balance Before Refill", "fieldtype": "Int", "read_only": 1},
            {"fieldname": "required_to_full", "label": "Required To Full", "fieldtype": "Int", "read_only": 1},
            {"fieldname": "expected_load_quantity", "label": "Expected Load Quantity", "fieldtype": "Int", "read_only": 1},

            {"fieldname": "section_break_refill_confirm", "label": "Confirmation", "fieldtype": "Section Break"},
            {"fieldname": "actual_loaded_quantity", "label": "Actual Loaded Quantity", "fieldtype": "Int",
             "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "balance_after_refill", "label": "Balance After Refill", "fieldtype": "Int",
             "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "exception_reason", "label": "Exception Reason", "fieldtype": "Small Text",
             "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "column_break_refill_2", "fieldtype": "Column Break"},
            {"fieldname": "completed_by", "label": "Completed By", "fieldtype": "Link", "options": "User",
             "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "completed_at", "label": "Completed At", "fieldtype": "Datetime",
             "read_only": 1, "allow_on_submit": 1},
        ],
        is_submittable=1,
        autoname="format:REFILL-{YYYY}-{#####}",
    )

    frappe.db.commit()
    print("Step 6 (Refill) doctype done.")
