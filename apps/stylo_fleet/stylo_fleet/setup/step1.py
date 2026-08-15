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
    # 1. Ambulance Settings (Single)
    # -----------------------------------------------------------------
    _make_doctype(
        "Ambulance Settings",
        fields=[
            {"fieldname": "default_kit_capacity", "label": "Default Kit Capacity", "fieldtype": "Int", "default": "10", "reqd": 1},
            {"fieldname": "default_minimum_operational_kits", "label": "Default Minimum Operational Kits", "fieldtype": "Int", "default": "3", "reqd": 1},
            {"fieldname": "default_refill_threshold", "label": "Default Refill Threshold", "fieldtype": "Int", "default": "5", "reqd": 1},
            {"fieldname": "column_break_settings_1", "fieldtype": "Column Break"},
            {"fieldname": "location_stale_after_minutes", "label": "Location Stale After (minutes)", "fieldtype": "Int", "default": "15", "reqd": 1},
            {"fieldname": "allow_emergency_override", "label": "Allow Emergency Override", "fieldtype": "Check", "default": "0"},
        ],
        issingle=1,
    )

    # -----------------------------------------------------------------
    # 2. Ambulance Station (Master)
    # -----------------------------------------------------------------
    _make_doctype(
        "Ambulance Station",
        fields=[
            {"fieldname": "station_name", "label": "Station Name", "fieldtype": "Data", "reqd": 1, "unique": 1},
            {"fieldname": "station_type", "label": "Station Type", "fieldtype": "Select",
             "options": "Base\nRefill\nCleaning\nService\nMulti-purpose", "reqd": 1},
            {"fieldname": "active", "label": "Active", "fieldtype": "Check", "default": "1"},
            {"fieldname": "column_break_station_1", "fieldtype": "Column Break"},
            {"fieldname": "address", "label": "Address", "fieldtype": "Small Text"},
            {"fieldname": "latitude", "label": "Latitude", "fieldtype": "Float", "precision": "8"},
            {"fieldname": "longitude", "label": "Longitude", "fieldtype": "Float", "precision": "8"},
        ],
        autoname="field:station_name",
    )

    # -----------------------------------------------------------------
    # 3. Paramedic (Master, linked to User)
    # -----------------------------------------------------------------
    _make_doctype(
        "Paramedic",
        fields=[
            {"fieldname": "paramedic_name", "label": "Paramedic Name", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "user", "label": "User", "fieldtype": "Link", "options": "User", "reqd": 1, "unique": 1},
            {"fieldname": "base_station", "label": "Base Station", "fieldtype": "Link", "options": "Ambulance Station"},
            {"fieldname": "column_break_paramedic_1", "fieldtype": "Column Break"},
            {"fieldname": "eligible", "label": "Eligible for Shift Assignment", "fieldtype": "Check", "default": "1"},
            {"fieldname": "active", "label": "Active", "fieldtype": "Check", "default": "1"},
        ],
        autoname="field:paramedic_name",
    )

    # -----------------------------------------------------------------
    # 4. Ambulance (Master — current source of truth)
    # -----------------------------------------------------------------
    _make_doctype(
        "Ambulance",
        fields=[
            {"fieldname": "identity_section", "label": "Identity", "fieldtype": "Section Break"},
            {"fieldname": "ambulance_id", "label": "Ambulance ID", "fieldtype": "Data", "reqd": 1, "unique": 1},
            {"fieldname": "vehicle_number", "label": "Vehicle Number", "fieldtype": "Data", "reqd": 1},
            {"fieldname": "vehicle_type", "label": "Vehicle Type", "fieldtype": "Data"},
            {"fieldname": "column_break_amb_1", "fieldtype": "Column Break"},
            {"fieldname": "base_station", "label": "Base Station", "fieldtype": "Link", "options": "Ambulance Station"},
            {"fieldname": "active", "label": "Active", "fieldtype": "Check", "default": "1"},

            {"fieldname": "assignment_section", "label": "Assignment", "fieldtype": "Section Break"},
            {"fieldname": "current_paramedic", "label": "Current Paramedic", "fieldtype": "Link", "options": "Paramedic", "read_only": 1},
            {"fieldname": "column_break_amb_2", "fieldtype": "Column Break"},
            {"fieldname": "assignment_start", "label": "Assignment Start", "fieldtype": "Datetime", "read_only": 1},

            {"fieldname": "operational_section", "label": "Operational", "fieldtype": "Section Break"},
            {"fieldname": "operational_status", "label": "Operational Status", "fieldtype": "Select",
             "options": "Available\nOn Call\nReturning / Transit\nGoing for Refill\nAt Refill Station\n"
                        "Under Cleaning\nUnder Maintenance\nBreakdown\nUnavailable\nInactive",
             "default": "Inactive", "read_only": 1},
            {"fieldname": "availability_status", "label": "Availability Status", "fieldtype": "Select",
             "options": "Available\nWarning\nUnavailable", "default": "Unavailable", "read_only": 1},
            {"fieldname": "availability_reason", "label": "Availability Reason", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "column_break_amb_3", "fieldtype": "Column Break"},
            {"fieldname": "last_activity_at", "label": "Last Activity At", "fieldtype": "Datetime", "read_only": 1},

            {"fieldname": "kits_section", "label": "Kits", "fieldtype": "Section Break"},
            {"fieldname": "kit_capacity", "label": "Kit Capacity", "fieldtype": "Int", "reqd": 1},
            {"fieldname": "available_kits", "label": "Available Kits", "fieldtype": "Int", "read_only": 1},
            {"fieldname": "column_break_amb_4", "fieldtype": "Column Break"},
            {"fieldname": "minimum_operational_kits", "label": "Minimum Operational Kits", "fieldtype": "Int", "reqd": 1},
            {"fieldname": "refill_threshold", "label": "Refill Threshold", "fieldtype": "Int", "reqd": 1},
            {"fieldname": "kit_status", "label": "Kit Status", "fieldtype": "Select",
             "options": "Ready\nRefill Due\nInsufficient\nNo Kits", "default": "Ready", "read_only": 1},

            {"fieldname": "readiness_section", "label": "Readiness", "fieldtype": "Section Break"},
            {"fieldname": "cleanliness_status", "label": "Cleanliness Status", "fieldtype": "Select",
             "options": "Clean\nCleaning Required\nUnder Cleaning", "default": "Clean"},
            {"fieldname": "column_break_amb_5", "fieldtype": "Column Break"},
            {"fieldname": "mechanical_status", "label": "Mechanical Status", "fieldtype": "Select",
             "options": "Fit\nObservation\nMaintenance Required\nBreakdown", "default": "Fit"},

            {"fieldname": "location_section", "label": "Location", "fieldtype": "Section Break"},
            {"fieldname": "latitude", "label": "Latitude", "fieldtype": "Float", "precision": "8", "read_only": 1},
            {"fieldname": "longitude", "label": "Longitude", "fieldtype": "Float", "precision": "8", "read_only": 1},
            {"fieldname": "column_break_amb_6", "fieldtype": "Column Break"},
            {"fieldname": "location_label", "label": "Location Label", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "last_location_at", "label": "Last Location At", "fieldtype": "Datetime", "read_only": 1},
            {"fieldname": "gps_status", "label": "GPS Status", "fieldtype": "Select",
             "options": "Online\nStale\nOffline\nManual", "default": "Offline", "read_only": 1},
        ],
        autoname="field:ambulance_id",
    )

    frappe.db.commit()
    print("Step 1 (Foundation) doctypes done.")
