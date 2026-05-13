"""
install_icons.py — restores Stylo workspace icon configuration after every migrate.

What it does:
  1. Sets logo_url on every Desktop Icon to the Stylo PNG served from stylo_core assets
  2. Clears parent_icon so all workspaces appear at top level (not buried inside folders)
  3. Unhides any workspace that was accidentally hidden

Run with:
  bench --site <site> execute stylo_core.install_icons.run
"""

import frappe

BASE = "/assets/stylo_core/images/workspace_icons"

# Workspace label → PNG filename (without extension)
ICON_MAP = {
    "Accounting":        "accounting",
    "Accounts Setup":    "accounts-setup",
    "Assets":            "assets",
    "Automation":        "automation",
    "Banking":           "banking",
    "Budget":            "budget",
    "Build":             "build",
    "Buying":            "buying",
    "CRM":               "crm",
    "Data":              "data",
    "Email":             "email",
    "Expenses":          "accounting",
    "Financial Reports": "financial-reports",
    "Frappe CRM":        "crm",
    "GST":               "taxes",
    "GST India":         "taxes",
    "Helpdesk":          "support",
    "Home":              "desktop",
    "HR Setup":          "setup",
    "HRMS":              "hrms",
    "Income Tax India":  "accounting",
    "India Compliance":  "settings",
    "Integrations":      "integrations",
    "Invoicing":         "invoicing",
    "Learning":          "documents",
    "Leaves":            "documents",
    "LMS":               "documents",
    "Manufacturing":     "manufacturing",
    "My Workspaces":     "workspaces",
    "Organization":      "organization",
    "Payments":          "payments",
    "Payroll":           "payroll",
    "Performance":       "reports",
    "Printing":          "printing",
    "Projects":          "projects",
    "Quality":           "quality",
    "Recruitment":       "leads",
    "Selling":           "selling",
    "Share Management":  "share-management",
    "Shift & Attendance":"maintenance",
    "Stock":             "stock",
    "Stylo":             "settings",
    "Stylo CRM":         "crm",
    "StyloBMS":          "erp-core",
    "StyloBMS Settings": "erp-settings",
    "Subcontracting":    "subcontracting",
    "Subscription":      "subscription",
    "Support":           "support",
    "System":            "system",
    "Tax & Benefits":    "taxes",
    "Taxes":             "taxes",
    "Tenure":            "workspaces",
    "Users":             "users",
    "Website":           "website",
}

# These should remain hidden — internal / duplicate icons
KEEP_HIDDEN = {"Home", "CRM", "Support", "Frappe CRM"}


def run():
    updated = 0

    all_icons = frappe.db.get_all(
        "Desktop Icon",
        fields=["name", "label", "hidden", "parent_icon", "logo_url"],
    )

    for icon in all_icons:
        label = icon.label
        changes = {}

        # 1. Set logo_url from Stylo PNG map
        if label in ICON_MAP:
            url = f"{BASE}/{ICON_MAP[label]}.png"
            if icon.logo_url != url:
                changes["logo_url"] = url

        # 2. Flatten to top level — clear parent_icon so workspace shows on home screen
        if icon.parent_icon and label not in KEEP_HIDDEN:
            changes["parent_icon"] = ""

        # 3. Unhide if accidentally hidden (unless it's in our keep-hidden list)
        if icon.hidden and label not in KEEP_HIDDEN:
            changes["hidden"] = 0

        if changes:
            frappe.db.set_value("Desktop Icon", icon.name, changes, update_modified=False)
            updated += 1

    frappe.db.commit()

    # Clear per-user desktop icons cache so every user sees fresh data
    frappe.cache.delete_key("desktop_icons")

    print(f"Stylo icons restored: {updated} Desktop Icon records updated.")
