import frappe

def run():
    # Rename ERPNext Settings → StyloBMS Settings
    count = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabWorkspace` WHERE name='ERPNext Settings'"
    )[0][0]
    if count:
        existing = frappe.db.sql(
            "SELECT COUNT(*) FROM `tabWorkspace` WHERE name='StyloBMS Settings'"
        )[0][0]
        if existing:
            # Delete the old one since new one already exists
            frappe.db.sql("DELETE FROM `tabWorkspace` WHERE name='ERPNext Settings'")
            print("  Deleted: ERPNext Settings (StyloBMS Settings already exists)")
        else:
            frappe.db.sql(
                "UPDATE `tabWorkspace` SET name='StyloBMS Settings', title='StyloBMS Settings' WHERE name='ERPNext Settings'"
            )
            print("  Renamed: ERPNext Settings → StyloBMS Settings")
    else:
        print("  Not found: ERPNext Settings (already renamed)")

    # Delete duplicate Frappe CRM workspace
    count = frappe.db.sql(
        "SELECT COUNT(*) FROM `tabWorkspace` WHERE name='Frappe CRM'"
    )[0][0]
    if count:
        frappe.db.sql("DELETE FROM `tabWorkspace` WHERE name='Frappe CRM'")
        frappe.db.sql("DELETE FROM `tabWorkspace Shortcut` WHERE parent='Frappe CRM'")
        frappe.db.sql("DELETE FROM `tabWorkspace Link` WHERE parent='Frappe CRM'")
        print("  Deleted: Frappe CRM workspace")
    else:
        print("  Not found: Frappe CRM (already removed)")

    frappe.db.commit()

    rows = frappe.db.sql(
        "SELECT name, title FROM `tabWorkspace` WHERE name LIKE '%Frappe%' OR name LIKE '%ERPNext%' ORDER BY name",
        as_dict=True
    )
    if rows:
        print(f"\nStill remaining ({len(rows)}):")
        for r in rows:
            print(f"  {r.name}")
    else:
        print("\nAll workspace names cleaned.")
