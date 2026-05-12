import frappe

def run():
    # 1. Fix Frappe CRM app icon → CRM (delete old CRM workspace link, rename the App icon)
    # Delete the workspace "CRM" link (app=erpnext, icon_type=Link) — it's a child of ERPNext
    frappe.db.sql("DELETE FROM `tabDesktop Icon` WHERE label='CRM' AND icon_type='Link'")

    # Rename the App icon
    frappe.db.sql("UPDATE `tabDesktop Icon` SET label='CRM' WHERE label='Frappe CRM' AND icon_type='App'")

    # 2. ERPNext Settings → StyloBMS Settings
    frappe.db.sql("UPDATE `tabDesktop Icon` SET label='StyloBMS Settings' WHERE label='ERPNext Settings'")

    # 3. Fix parent_icon references: anything pointing to old "ERPNext" now points to "StyloBMS"
    frappe.db.sql("UPDATE `tabDesktop Icon` SET parent_icon='StyloBMS' WHERE parent_icon='ERPNext'")

    # 4. Update logo_url for renamed icons
    BASE = "/assets/frappe/icons/stylobms/light"
    updates = [
        ("StyloBMS Settings", "erp-settings.png"),
        ("CRM",               "crm.png"),
    ]
    for label, png in updates:
        frappe.db.sql(
            "UPDATE `tabDesktop Icon` SET logo_url=%s WHERE label=%s",
            (f"{BASE}/{png}", label)
        )

    frappe.db.commit()

    # 5. Verify
    rows = frappe.db.sql(
        "SELECT label, app, icon_type, parent_icon FROM `tabDesktop Icon` ORDER BY label",
        as_dict=True
    )
    print("\nAll Desktop Icons after rebrand:")
    for r in rows:
        print(f"  {r.label:<30} app={r.app:<20} type={r.icon_type}  parent={r.parent_icon or '-'}")
