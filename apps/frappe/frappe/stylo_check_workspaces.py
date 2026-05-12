import frappe

def run():
    rows = frappe.db.sql(
        "SELECT name, title, module FROM `tabWorkspace` WHERE title LIKE '%Frappe%' OR title LIKE '%ERPNext%' OR name LIKE '%Frappe%' OR name LIKE '%ERPNext%' ORDER BY title",
        as_dict=True
    )
    print(f"\nWorkspaces with old brand names ({len(rows)} found):")
    for r in rows:
        print(f"  name={r.name:<40} title={r.title}")

    # Also check getting started sections
    rows2 = frappe.db.sql(
        "SELECT name, title FROM `tabOnboarding` WHERE title LIKE '%Frappe%' OR title LIKE '%ERPNext%' ORDER BY title",
        as_dict=True
    )
    print(f"\nOnboarding with old brand names ({len(rows2)} found):")
    for r in rows2:
        print(f"  {r.name:<40} title={r.title}")
