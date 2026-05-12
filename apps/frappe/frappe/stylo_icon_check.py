import frappe

def run():
    icons = frappe.db.sql("""
        SELECT label, logo_url, app
        FROM `tabDesktop Icon`
        WHERE standard = 1 AND hidden = 0
        ORDER BY label
    """, as_dict=True)
    for i in icons:
        print(f"  {i.label:30} | app={str(i.app or 'NULL'):15} | logo_url={'SET' if i.logo_url else 'NULL'}")
    print(f"\nTotal: {len(icons)}")
