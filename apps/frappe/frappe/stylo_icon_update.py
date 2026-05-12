import frappe

ICON_MAP = {
    # ERPNext / StyloBMS
    "StyloBMS": "erp-core.svg",
    "StyloBMS Settings": "erp-settings.svg",
    "Accounting": "accounting.svg",
    "Accounts Setup": "accounts-setup.svg",
    "Assets": "assets.svg",
    "Banking": "banking.svg",
    "Budget": "budget.svg",
    "Buying": "buying.svg",
    "Financial Reports": "financial-reports.svg",
    "Home": "desktop.svg",
    "Invoicing": "invoicing.svg",
    "Manufacturing": "manufacturing.svg",
    "Organization": "organization.svg",
    "Payments": "payments.svg",
    "Projects": "projects.svg",
    "Quality": "quality.svg",
    "Selling": "selling.svg",
    "Share Management": "share-management.svg",
    "Stock": "stock.svg",
    "Subcontracting": "subcontracting.svg",
    "Subscription": "subscription.svg",
    "Support": "support.svg",
    "Taxes": "taxes.svg",
    # HRMS
    "HRMS": "hrms.svg",
    "Expenses": "accounting.svg",
    "HR Setup": "setup.svg",
    "Leaves": "documents.svg",
    "Payroll": "payroll.svg",
    "Performance": "reports.svg",
    "Recruitment": "leads.svg",
    "Shift & Attendance": "maintenance.svg",
    "Tax & Benefits": "taxes.svg",
    "Tenure": "workspaces.svg",
    # Frappe / Stylo
    "Stylo": "settings.svg",
    "Automation": "automation.svg",
    "Build": "build.svg",
    "Data": "data.svg",
    "Email": "email.svg",
    "Integrations": "integrations.svg",
    "My Workspaces": "workspaces.svg",
    "Printing": "printing.svg",
    "System": "system.svg",
    "Users": "users.svg",
    "Website": "website.svg",
    # Other apps
    "Frappe CRM": "crm.svg",
    "LMS": "documents.svg",
    "GST India": "taxes.svg",
    "Income Tax India": "accounting.svg",
    "India Compliance": "settings.svg",
    "Helpdesk": "support.svg",
}

def run():
    BASE = "/assets/frappe/icons/desktop_icons/stylo"
    updated = 0
    for label, png in ICON_MAP.items():
        rows = frappe.db.sql(
            "UPDATE `tabDesktop Icon` SET logo_url=%s WHERE label=%s",
            (f"{BASE}/{png}", label)
        )
        updated += 1
        print(f"  {label} -> {png}")
    frappe.db.commit()
    # Clear both desktop_icons and bootinfo caches for all users
    frappe.cache.delete_key("desktop_icons")
    frappe.cache.delete_key("bootinfo")
    print(f"\nDone: {updated} icons updated. Caches cleared.")
