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


STANDARD_PERMS = [
    {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
    {"role": "Fleet Admin", "read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
    {"role": "Fleet Operations", "read": 1, "write": 1, "create": 1},
    {"role": "Fleet Station", "read": 1, "create": 1},
    {"role": "Fleet Paramedic", "read": 1, "create": 1},
]


def run():
    # -----------------------------------------------------------------
    # Shift Assignment (Transaction, submittable) — advance roster/schedule,
    # separate from Ambulance Shift (the actual clock-in/out record created
    # by Start Shift). Scheduled -> Completed/No-Show/Cancelled.
    # -----------------------------------------------------------------
    _make_doctype(
        "Shift Assignment",
        fields=[
            {"fieldname": "ambulance", "label": "Ambulance", "fieldtype": "Link", "options": "Ambulance",
             "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "paramedic", "label": "Paramedic", "fieldtype": "Link", "options": "Paramedic",
             "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "assignment_date", "label": "Date", "fieldtype": "Date", "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "shift_slot", "label": "Shift Slot", "fieldtype": "Select",
             "options": "Morning (06:00-14:00)\nEvening (14:00-22:00)\nNight (22:00-06:00)",
             "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "column_break_assign_1", "fieldtype": "Column Break"},
            {"fieldname": "status", "label": "Status", "fieldtype": "Select",
             "options": "Scheduled\nCompleted\nNo-Show\nCancelled", "default": "Scheduled",
             "reqd": 1, "read_only": 1, "allow_on_submit": 1, "in_list_view": 1},
            {"fieldname": "actual_shift", "label": "Actual Shift", "fieldtype": "Link", "options": "Ambulance Shift",
             "read_only": 1, "allow_on_submit": 1},
            {"fieldname": "notes", "label": "Notes", "fieldtype": "Small Text", "read_only": 1, "allow_on_submit": 1},
        ],
        is_submittable=1,
        autoname="format:ASSIGN-{YYYY}-{#####}",
        permissions=STANDARD_PERMS,
    )

    # -----------------------------------------------------------------
    # Ticket (Transaction, submittable) — general operational/admin ticketing,
    # separate from Ambulance Issue (which stays specific to cleaning/
    # mechanical vehicle defects). Open -> Closed via a Ticket Closing record.
    # -----------------------------------------------------------------
    _make_doctype(
        "Ticket",
        fields=[
            {"fieldname": "subject", "label": "Subject", "fieldtype": "Data", "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "category", "label": "Category", "fieldtype": "Select",
             "options": "HR\nComplaint\nEquipment\nFacility\nIT\nGeneral\nOther",
             "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "priority", "label": "Priority", "fieldtype": "Select",
             "options": "Low\nMedium\nHigh\nUrgent", "default": "Medium", "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "status", "label": "Status", "fieldtype": "Select",
             "options": "Open\nIn Progress\nClosed", "default": "Open", "reqd": 1,
             "read_only": 1, "allow_on_submit": 1, "in_list_view": 1},
            {"fieldname": "section_break_ticket_1", "label": "Details", "fieldtype": "Section Break"},
            {"fieldname": "description", "label": "Description", "fieldtype": "Small Text", "read_only": 1},
            {"fieldname": "related_ambulance", "label": "Related Ambulance", "fieldtype": "Link", "options": "Ambulance", "read_only": 1},
            {"fieldname": "related_station", "label": "Related Station", "fieldtype": "Link", "options": "Ambulance Station", "read_only": 1},
            {"fieldname": "column_break_ticket_1", "fieldtype": "Column Break"},
            {"fieldname": "raised_by", "label": "Raised By", "fieldtype": "Link", "options": "User", "reqd": 1, "read_only": 1},
            {"fieldname": "raised_at", "label": "Raised At", "fieldtype": "Datetime", "reqd": 1, "read_only": 1},
        ],
        is_submittable=1,
        autoname="format:TICKET-{YYYY}-{#####}",
        permissions=STANDARD_PERMS,
    )

    # -----------------------------------------------------------------
    # Ticket Closing (Transaction, submittable) — the resolution record,
    # separate doctype rather than fields on Ticket, per user request.
    # -----------------------------------------------------------------
    _make_doctype(
        "Ticket Closing",
        fields=[
            {"fieldname": "ticket", "label": "Ticket", "fieldtype": "Link", "options": "Ticket",
             "reqd": 1, "unique": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "closed_by", "label": "Closed By", "fieldtype": "Link", "options": "User", "reqd": 1, "read_only": 1},
            {"fieldname": "closed_at", "label": "Closed At", "fieldtype": "Datetime", "reqd": 1, "read_only": 1, "in_list_view": 1},
            {"fieldname": "root_cause", "label": "Root Cause", "fieldtype": "Select",
             "options": "\nUser Error\nEquipment Failure\nProcess Gap\nExternal\nOther", "read_only": 1},
            {"fieldname": "resolution_summary", "label": "Resolution Summary", "fieldtype": "Small Text", "reqd": 1, "read_only": 1},
        ],
        is_submittable=1,
        autoname="format:CLOSE-{YYYY}-{#####}",
        permissions=[
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1},
            {"role": "Fleet Admin", "read": 1, "create": 1, "submit": 1, "cancel": 1},
            {"role": "Fleet Operations", "read": 1, "create": 1},
            {"role": "Fleet Station", "read": 1},
            {"role": "Fleet Paramedic", "read": 1},
        ],
    )

    frappe.db.commit()
    print("Step 12 (Shift Assignment + Ticket + Ticket Closing) done.")
