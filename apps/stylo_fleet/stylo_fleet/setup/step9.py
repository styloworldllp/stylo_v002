import frappe

MODULE = "Stylo Fleet"


def _make_report(name, ref_doctype, query):
    if frappe.db.exists("Report", name):
        print(f"Skip (exists): Report {name}")
        return
    doc = frappe.new_doc("Report")
    doc.report_name = name
    doc.ref_doctype = ref_doctype
    doc.report_type = "Query Report"
    doc.module = MODULE
    doc.is_standard = "Yes"
    doc.query = query
    doc.insert(ignore_permissions=True)
    print(f"Created: Report {name}")


def run():
    _make_report(
        "Current Ambulance Status",
        ref_doctype="Ambulance",
        query="""
            SELECT
                a.name AS "Ambulance:Link/Ambulance:120",
                a.vehicle_number AS "Vehicle Number::100",
                a.operational_status AS "Operational Status::120",
                a.availability_status AS "Availability::100",
                a.availability_reason AS "Reason::140",
                a.current_paramedic AS "Paramedic:Link/Paramedic:120",
                CONCAT(a.available_kits, '/', a.kit_capacity) AS "Kits::80",
                a.kit_status AS "Kit Status::100",
                a.cleanliness_status AS "Cleanliness::100",
                a.mechanical_status AS "Mechanical::120",
                a.gps_status AS "GPS Status::80",
                a.last_location_at AS "Last Location Update::160"
            FROM `tabAmbulance` a
            WHERE a.active = 1
            ORDER BY a.name
        """.strip(),
    )

    _make_report(
        "Ambulance Refill Report",
        ref_doctype="Ambulance Refill",
        query="""
            SELECT
                r.name AS "Refill:Link/Ambulance Refill:120",
                r.ambulance AS "Ambulance:Link/Ambulance:120",
                r.station AS "Station:Link/Ambulance Station:120",
                r.status AS "Status::100",
                r.balance_before_refill AS "Balance Before::100",
                r.expected_load_quantity AS "Expected Load::100",
                r.actual_loaded_quantity AS "Actual Loaded::100",
                r.balance_after_refill AS "Balance After::100",
                r.exception_reason AS "Exception Reason::200",
                r.requested_at AS "Requested At::150",
                r.completed_at AS "Completed At::150"
            FROM `tabAmbulance Refill` r
            ORDER BY r.requested_at DESC
        """.strip(),
    )

    frappe.db.commit()
    print("Step 9 (Dashboards) reports done.")
