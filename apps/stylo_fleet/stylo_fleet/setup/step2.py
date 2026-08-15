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


def _add_field_to_doctype(doctype, field):
    dt = frappe.get_doc("DocType", doctype)
    if any(f.fieldname == field["fieldname"] for f in dt.fields):
        print(f"Skip (field exists): {doctype}.{field['fieldname']}")
        return
    dt.append("fields", field)
    dt.save(ignore_permissions=True)
    print(f"Added field: {doctype}.{field['fieldname']}")


def run():
    # -----------------------------------------------------------------
    # 1. Ambulance Shift (Transaction, submittable)
    # -----------------------------------------------------------------
    _make_doctype(
        "Ambulance Shift",
        fields=[
            {"fieldname": "ambulance", "label": "Ambulance", "fieldtype": "Link", "options": "Ambulance", "reqd": 1},
            {"fieldname": "paramedic", "label": "Paramedic", "fieldtype": "Link", "options": "Paramedic", "reqd": 1},
            {"fieldname": "status", "label": "Status", "fieldtype": "Select",
             "options": "Open\nClosed\nException", "default": "Open", "reqd": 1, "allow_on_submit": 1},
            {"fieldname": "column_break_shift_1", "fieldtype": "Column Break"},
            {"fieldname": "start_datetime", "label": "Start Date-Time", "fieldtype": "Datetime", "reqd": 1, "read_only": 1},
            {"fieldname": "start_latitude", "label": "Start Latitude", "fieldtype": "Float", "precision": "8", "read_only": 1},
            {"fieldname": "start_longitude", "label": "Start Longitude", "fieldtype": "Float", "precision": "8", "read_only": 1},
            {"fieldname": "start_check_result", "label": "Start Check Result", "fieldtype": "Small Text", "read_only": 1},

            {"fieldname": "section_break_shift_end", "label": "End of Shift", "fieldtype": "Section Break"},
            {"fieldname": "end_datetime", "label": "End Date-Time", "fieldtype": "Datetime", "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "end_latitude", "label": "End Latitude", "fieldtype": "Float", "precision": "8", "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "end_longitude", "label": "End Longitude", "fieldtype": "Float", "precision": "8", "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "column_break_shift_2", "fieldtype": "Column Break"},
            {"fieldname": "end_check_result", "label": "End Check Result", "fieldtype": "Small Text", "read_only": 1, "allow_on_submit": 1},
        ],
        is_submittable=1,
        autoname="format:SHIFT-{YYYY}-{#####}",
    )

    # -----------------------------------------------------------------
    # 2. Ambulance.current_shift — deferred from Step 1, added now that
    #    Ambulance Shift exists.
    # -----------------------------------------------------------------
    _add_field_to_doctype(
        "Ambulance",
        {
            "fieldname": "current_shift",
            "label": "Current Shift",
            "fieldtype": "Link",
            "options": "Ambulance Shift",
            "read_only": 1,
        },
    )

    frappe.db.commit()
    print("Step 2 (Shift) doctypes done.")
