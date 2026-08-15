import frappe


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
    # Ambulance.current_call_activity — tracks the open "Call Started"
    # Ambulance Activity while On Call, so Complete Call knows which call
    # it's closing without needing a separate Call transaction doctype.
    # -----------------------------------------------------------------
    _add_field_to_doctype(
        "Ambulance",
        {
            "fieldname": "current_call_activity",
            "label": "Current Call Activity",
            "fieldtype": "Link",
            "options": "Ambulance Activity",
            "read_only": 1,
        },
    )

    frappe.db.commit()
    print("Step 4 (Call workflow) field additions done.")
