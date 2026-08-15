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
    # Ambulance Activity — immutable audit trail. Every field is
    # read-only in the UI; the only writer is
    # stylo_fleet.engine.activity.log_activity(). No allow_on_submit
    # fields at all, so once submitted a record can never change.
    # -----------------------------------------------------------------
    _make_doctype(
        "Ambulance Activity",
        fields=[
            {"fieldname": "activity_type", "label": "Activity Type", "fieldtype": "Select",
             "options": "Shift Started\nShift Ended\nCall Started\nCall Completed\n"
                        "Refill Requested\nRefill Completed\nCleaning Required\nCleaning Completed\n"
                        "Mechanical Issue\nMaintenance Completed\nManual Correction",
             "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "ambulance", "label": "Ambulance", "fieldtype": "Link", "options": "Ambulance",
             "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "shift", "label": "Shift", "fieldtype": "Link", "options": "Ambulance Shift", "read_only": 1},
            {"fieldname": "paramedic", "label": "Paramedic", "fieldtype": "Link", "options": "Paramedic", "read_only": 1},
            {"fieldname": "column_break_activity_1", "fieldtype": "Column Break"},
            {"fieldname": "event_datetime", "label": "Event Date-Time", "fieldtype": "Datetime",
             "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "latitude", "label": "Latitude", "fieldtype": "Float", "precision": "8", "read_only": 1},
            {"fieldname": "longitude", "label": "Longitude", "fieldtype": "Float", "precision": "8", "read_only": 1},

            {"fieldname": "section_break_activity_status", "label": "Status Change", "fieldtype": "Section Break"},
            {"fieldname": "previous_status", "label": "Previous Status", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "new_status", "label": "New Status", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "column_break_activity_2", "fieldtype": "Column Break"},
            {"fieldname": "kit_balance_before", "label": "Kit Balance Before", "fieldtype": "Int", "read_only": 1},
            {"fieldname": "kit_balance_after", "label": "Kit Balance After", "fieldtype": "Int", "read_only": 1},

            {"fieldname": "section_break_activity_ref", "label": "Details", "fieldtype": "Section Break"},
            {"fieldname": "remarks", "label": "Remarks", "fieldtype": "Small Text", "read_only": 1},
            {"fieldname": "reference_doctype", "label": "Reference Document Type", "fieldtype": "Select",
             "options": "\nAmbulance Refill\nAmbulance Issue", "read_only": 1},
            {"fieldname": "reference_transaction", "label": "Reference Transaction", "fieldtype": "Dynamic Link",
             "options": "reference_doctype", "read_only": 1},
        ],
        is_submittable=1,
        autoname="hash",
        sort_field="event_datetime",
        sort_order="DESC",
    )

    frappe.db.commit()
    print("Step 3 (Activity engine) doctype done.")
