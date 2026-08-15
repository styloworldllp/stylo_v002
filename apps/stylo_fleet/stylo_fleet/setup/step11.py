import frappe

MODULE = "Stylo Fleet"


def _make_doctype(name, fields, permissions=None, **kwargs):
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
    for p in (permissions or []):
        doc.append("permissions", p)
    doc.insert(ignore_permissions=True)
    print(f"Created: {name}")


def run():
    # -----------------------------------------------------------------
    # Station Operator (Master) — mirrors Paramedic, links a User to the
    # Ambulance Station they operate, so the Station Console can be scoped
    # to their own station's refill queue.
    # -----------------------------------------------------------------
    _make_doctype(
        "Station Operator",
        fields=[
            {"fieldname": "operator_name", "label": "Operator Name", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "user", "label": "User", "fieldtype": "Link", "options": "User", "reqd": 1, "unique": 1},
            {"fieldname": "station", "label": "Station", "fieldtype": "Link", "options": "Ambulance Station", "reqd": 1},
            {"fieldname": "column_break_stationop_1", "fieldtype": "Column Break"},
            {"fieldname": "active", "label": "Active", "fieldtype": "Check", "default": "1"},
        ],
        autoname="field:operator_name",
        permissions=[
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Fleet Admin", "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Fleet Operations", "read": 1, "write": 1},
            {"role": "Fleet Station", "read": 1},
            {"role": "Fleet Paramedic", "read": 1},
        ],
    )

    frappe.db.commit()
    print("Step 11 (Role consoles: Station Operator doctype) done.")
