import frappe

def run():
    rows = frappe.db.sql(
        "SELECT label, app, icon_type, parent_icon, logo_url FROM `tabDesktop Icon` ORDER BY label",
        as_dict=True
    )
    print("\nAll Desktop Icons:")
    for r in rows:
        print(f"  {r.label:<35} app={r.app:<20} type={r.icon_type:<10} parent={r.parent_icon or '-':<20} logo={'YES' if r.logo_url else 'NO'}")
