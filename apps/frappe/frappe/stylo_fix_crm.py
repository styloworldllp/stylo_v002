import frappe

def run():
    BASE = "/assets/frappe/icons/stylobms/light"

    # Desktop Icon: CRM (App) → Frappe CRM
    frappe.db.sql(
        "UPDATE `tabDesktop Icon` SET label='Frappe CRM', logo_url=%s WHERE label='CRM' AND icon_type='App'",
        (f"{BASE}/crm.png",)
    )
    print("  Desktop Icon: CRM → Frappe CRM")

    # Workspace: CRM → Frappe CRM
    count = frappe.db.sql("SELECT COUNT(*) FROM `tabWorkspace` WHERE name='CRM'")[0][0]
    if count:
        frappe.db.sql(
            "UPDATE `tabWorkspace` SET name='Frappe CRM', title='Frappe CRM' WHERE name='CRM'"
        )
        print("  Workspace: CRM → Frappe CRM")
    else:
        print("  Workspace CRM not found")

    frappe.db.commit()
    print("\nDone.")
