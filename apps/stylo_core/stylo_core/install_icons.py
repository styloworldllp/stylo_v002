"""
install_icons.py — sets logo_url on every Desktop Icon record to point to
the Stylo PNG icons served from stylo_core assets.

Run with:
  bench --site <site> execute stylo_core.install_icons.run
"""

import frappe

BASE = "/assets/stylo_core/images/workspace_icons"

# Workspace label → PNG filename (without extension)
ICON_MAP = {
    "Accounting":       "accounting",
    "Accounts Setup":   "accounts-setup",
    "Assets":           "assets",
    "Automation":       "automation",
    "Banking":          "banking",
    "Budget":           "budget",
    "Build":            "build",
    "Buying":           "buying",
    "CRM":              "crm",
    "Data":             "data",
    "Email":            "email",
    "Expenses":         "accounting",
    "Financial Reports":"financial-reports",
    "Frappe CRM":       "crm",
    "GST":              "taxes",
    "GST India":        "taxes",
    "Helpdesk":         "support",
    "Home":             "desktop",
    "HR Setup":         "setup",
    "HRMS":             "hrms",
    "Income Tax India": "accounting",
    "India Compliance": "settings",
    "Integrations":     "integrations",
    "Invoicing":        "invoicing",
    "Learning":         "documents",
    "Leaves":           "documents",
    "LMS":              "documents",
    "Manufacturing":    "manufacturing",
    "My Workspaces":    "workspaces",
    "Organization":     "organization",
    "Payments":         "payments",
    "Payroll":          "payroll",
    "Performance":      "reports",
    "Printing":         "printing",
    "Projects":         "projects",
    "Quality":          "quality",
    "Recruitment":      "leads",
    "Selling":          "selling",
    "Share Management": "share-management",
    "Shift & Attendance":"maintenance",
    "Stock":            "stock",
    "Stylo":            "settings",
    "Stylo CRM":        "crm",
    "StyloBMS":         "erp-core",
    "StyloBMS Settings":"erp-settings",
    "Subcontracting":   "subcontracting",
    "Subscription":     "subscription",
    "Support":          "support",
    "System":           "system",
    "Tax & Benefits":   "taxes",
    "Taxes":            "taxes",
    "Tenure":           "workspaces",
    "Users":            "users",
    "Website":          "website",
}


def run():
    updated = 0
    for label, icon_file in ICON_MAP.items():
        url = f"{BASE}/{icon_file}.png"
        rows = frappe.db.get_all("Desktop Icon", filters={"label": label}, fields=["name"])
        for row in rows:
            frappe.db.set_value("Desktop Icon", row.name, "logo_url", url, update_modified=False)
            updated += 1

    frappe.db.commit()
    frappe.cache.delete_key("desktop_icons")
    frappe.cache.delete_value("desktop_icons")
    print(f"Updated {updated} Desktop Icon records → {BASE}/*.png")
