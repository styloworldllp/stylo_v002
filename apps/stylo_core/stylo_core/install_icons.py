"""
install_icons.py — white-labels Frappe/ERPNext Desktop Icons to Stylo
branding and applies Stylo PNG icons.

Run with:
  bench --site <site> execute stylo_core.install_icons.run
"""

import frappe

BASE = "/assets/stylo_core/images/workspace_icons"

# Old Frappe/ERPNext name → new Stylo brand name
RENAME = {
    "Framework":        "Stylo",
    "Frappe HR":        "HRMS",
    "Frappe Learning":  "LMS",
    "Frappe CRM":       "CRM",
    "ERPNext":          "BMS",
    "ERPNext Settings": "BMS Settings",
}

# Child icons that may still reference old parent names → fix to new names
PARENT_FIX = {
    "Framework": "Stylo",
    "ERPNext":   "BMS",
    "Frappe HR": "HRMS",
}

# Icons that need explicit workspace link + visibility fix.
# These are created as empty Folder types (no children) and need to be
# converted to Link types pointing to the correct workspace.
# Format: name → {link_to, hidden, parent_icon}
LINK_FIX = {
    "CRM": {
        "link":        "/crm",        # Standalone Stylo CRM app
        "link_to":     "",
        "icon_type":   "Link",
        "link_type":   "External",
        "hidden":      0,
        "parent_icon": "",
    },
    "LMS": {
        "link":        "/lms",        # Standalone Stylo LMS app
        "link_to":     "",
        "icon_type":   "Link",
        "link_type":   "External",
        "hidden":      0,
        "parent_icon": "",
    },
    "BMS Settings": {
        "link":        "/desk/bms-settings",  # Direct URL — avoids sidebar-item lookup bug
        "link_to":     "",
        "icon_type":   "Link",
        "link_type":   "External",
        "hidden":      0,
        "parent_icon": "",
    },
    "Drive": {
        "link":        "/drive",      # Standalone Stylo Drive Vue app
        "link_to":     "",
        "icon_type":   "Link",
        "link_type":   "External",
        "hidden":      0,
        "parent_icon": "",
    },
    "Insights": {
        "link":        "/insights",   # Standalone Stylo Insights Vue app
        "link_to":     "",
        "icon_type":   "Link",
        "link_type":   "External",
        "hidden":      0,
        "parent_icon": "",
    },
    "Mint": {
        "link":        "/reco",       # Standalone Stylo Reco bank reconciliation app
        "link_to":     "",
        "icon_type":   "App",
        "link_type":   "External",
        "hidden":      0,
        "parent_icon": "",
    },
    "Stylo Reco": {
        "link":        "/reco",
        "link_to":     "",
        "icon_type":   "App",
        "link_type":   "External",
        "hidden":      0,
        "parent_icon": "",
    },
    "brAIn": {
        "link":        "/app/brain-settings",
        "link_to":     "",
        "icon_type":   "App",
        "link_type":   "External",
        "hidden":      0,
        "parent_icon": "",
    },
}

# Label (after renaming) → PNG filename in workspace_icons/
ICON_MAP = {
    # ── Top-level folders ─────────────────────────────────────────────────
    "Stylo":             "stylo-logo",    # Framework → Stylo ring logo
    "HRMS":              "hrms",
    "LMS":               "documents",
    "CRM":               "crm",
    "BMS":               "erp-core",     # hidden — children show flat
    "BMS Settings":      "erp-settings",
    "India Compliance":        "settings",
    "My Workspaces":           "workspaces",
    "Organization":            "organization",
    "Subcontracting":          "subcontracting",
    "Accounting":              "accounting",
    # ── Stylo (Framework) children ────────────────────────────────────────
    "Automation":              "automation",
    "Build":                   "build",
    "Data":                    "data",
    "Email":                   "email",
    "Integrations":            "integrations",
    "Printing":                "printing",
    "System":                  "system",
    "Users":                   "users",
    "Website":                 "website",
    # ── BMS (ERPNext) children ────────────────────────────────────────────
    "Assets":                  "assets",
    "Buying":                  "buying",
    "Manufacturing":           "manufacturing",
    "Projects":                "projects",
    "Quality":                 "quality",
    "Selling":                 "selling",
    "Stock":                   "stock",
    "Support":                 "support",
    # ── Accounting children ───────────────────────────────────────────────
    "Accounts Setup":          "accounts-setup",
    "Banking":                 "banking",
    "Budget":                  "budget",
    "Financial Reports":       "financial-reports",
    "Invoicing":               "invoicing",
    "Payments":                "payments",
    "Share Management":        "share-management",
    "Subscription":            "subscription",
    "Taxes":                   "taxes",
    # ── India Compliance children ─────────────────────────────────────────
    "GST India":               "taxes",
    "Income Tax India":        "accounting",
    # ── HRMS children ────────────────────────────────────────────────────
    "Expenses":                "accounting",
    "HR Setup":                "setup",
    "Leaves":                  "documents",
    "Payroll":                 "payroll",
    "Performance":             "reports",
    "Recruitment":             "leads",
    "Shift & Attendance":      "maintenance",
    "Tax & Benefits":          "taxes",
    "Tenure":                  "workspaces",
    # ── New Stylo apps ────────────────────────────────────────────────────
    "Lending":                 "stylo-lending",  # Stylo Lending
    "Drive":                   "stylo-drive",    # Stylo Drive
    "Insights":                "stylo-insights", # Stylo Insights
    "Mint":                    "stylo-reco",     # Stylo Reco — bank reconciliation
    "Stylo Lending":           "stylo-lending",
    "Stylo Drive":             "stylo-drive",
    "Stylo Insights":          "stylo-insights",
    "Stylo Reco":              "stylo-reco",
    # ── Misc ──────────────────────────────────────────────────────────────
    "Home":                    "desktop",
}


# Apps that use add_to_apps_screen (no Desktop Icon auto-created by Frappe).
# We create their Desktop Icons here so they appear on the home screen.
# Format: icon_name → {label, link, logo_file (from ICON_MAP)}
DESKTOP_CREATE = {
    "Stylo Drive": {
        "label":       "Stylo Drive",
        "link":        "/drive",
        "logo_file":   "stylo-drive",
        "app":         "drive",
    },
    "Stylo Insights": {
        "label":       "Stylo Insights",
        "link":        "/insights",
        "logo_file":   "stylo-insights",
        "app":         "insights",
    },
    "Stylo Lending": {
        "label":       "Stylo Lending",
        "link":        "/app/lending",
        "logo_file":   "stylo-lending",
        "app":         "lending",
    },
    "Stylo Reco": {
        "label":       "Stylo Reco",
        "link":        "/reco",
        "logo_file":   "stylo-reco",
        "app":         "mint",
    },
    "Gameplan": {
        "label":       "Gameplan",
        "link":        "/g",
        "logo_file":   "projects",
        "app":         "gameplan",
    },
    "Helpdesk": {
        "label":       "Helpdesk",
        "link":        "/helpdesk",
        "logo_file":   "support",
        "app":         "helpdesk",
    },
    "brAIn": {
        "label":       "brAIn",
        "link":        "/app/brain-settings",
        "logo_file":   "ai-assistant",
        "app":         "brain",
    },
}


def run():
    renamed = 0
    fixed = 0
    updated = 0

    # ── Step 0: Create Desktop Icons for apps that don't auto-create them ──
    created = 0
    for icon_name, cfg in DESKTOP_CREATE.items():
        # Only create if the app is installed and icon doesn't exist yet
        if not frappe.db.exists("Module Def", cfg["app"].replace("_", " ").title()) and \
           not frappe.db.exists("Module Def", cfg["app"]):
            # Try by app name in installed apps list
            if cfg["app"] not in frappe.get_installed_apps():
                continue
        if frappe.db.exists("Desktop Icon", icon_name):
            continue
        logo_url = f"{BASE}/{cfg['logo_file']}.png"
        doc = frappe.get_doc({
            "doctype":    "Desktop Icon",
            "name":       icon_name,
            "label":      cfg["label"],
            "icon_type":  "App",      # "App" bypasses workspace_sidebar_item check in is_permitted
            "link_type":  "External",
            "link":       cfg["link"],
            "link_to":    "",
            "logo_url":   logo_url,
            "icon_image": "",
            "hidden":     0,
            "standard":   1,          # must be 1 to show on the desktop home screen
            "parent_icon": "",
            "app":        cfg["app"],
        })
        try:
            doc.insert(ignore_permissions=True)
            created += 1
        except Exception:
            pass
    frappe.db.commit()

    # ── Step 1: Rename parent icons using rename_doc ──────────────────────
    # rename_doc cascades all Link references (parent_icon on children).
    for old_label, new_label in RENAME.items():
        if frappe.db.exists("Desktop Icon", old_label) and \
           not frappe.db.exists("Desktop Icon", new_label):
            frappe.rename_doc("Desktop Icon", old_label, new_label, force=True)
            renamed += 1
    frappe.db.commit()

    # ── Step 2: Fix child icons whose parent_icon still uses old names ────
    # Needed when JSON import was skipped due to DB timestamp being newer.
    for old_parent, new_parent in PARENT_FIX.items():
        rows = frappe.db.get_all(
            "Desktop Icon",
            filters={"parent_icon": old_parent},
            fields=["name"],
        )
        for row in rows:
            frappe.db.set_value("Desktop Icon", row.name, "parent_icon", new_parent, update_modified=False)
            fixed += 1
    frappe.db.commit()

    # ── Step 3: Apply Stylo PNG logo_url ──────────────────────────────────
    for label, icon_file in ICON_MAP.items():
        url = f"{BASE}/{icon_file}.png"
        rows = frappe.db.get_all(
            "Desktop Icon",
            filters={"label": label},
            fields=["name", "logo_url", "icon_image"],
        )
        for row in rows:
            # Always force-set logo_url and clear icon_image (SVG data overrides PNG logo)
            frappe.db.set_value("Desktop Icon", row.name, {
                "logo_url":   url,
                "icon_image": "",
            }, update_modified=False)
            updated += 1

    # ── Step 4: Fix icons that need explicit workspace link / visibility ──
    link_fixed = 0
    for icon_name, props in LINK_FIX.items():
        if frappe.db.exists("Desktop Icon", icon_name):
            frappe.db.set_value("Desktop Icon", icon_name, props, update_modified=False)
            link_fixed += 1

    # ── Step 5: Fix CRM and LMS app brand names ───────────────────────────
    brand_fixed = 0
    if frappe.db.exists("DocType", "FCRM Settings"):
        current = frappe.db.get_single_value("FCRM Settings", "brand_name")
        if current != "Stylo CRM":
            frappe.db.set_single_value("FCRM Settings", "brand_name", "Stylo CRM")
            brand_fixed += 1

    # ── Step 6: White-label new app icon labels ────────────────────────────
    LABEL_RENAME = {
        "Drive":    "Stylo Drive",
        "Insights": "Stylo Insights",
        "Lending":  "Stylo Lending",
        "Mint":     "Stylo Reco",
        "Frappe Drive": "Stylo Drive",
    }
    for old_label, new_label in LABEL_RENAME.items():
        rows = frappe.db.get_all("Desktop Icon", filters={"label": old_label}, fields=["name"])
        for row in rows:
            frappe.db.set_value("Desktop Icon", row.name, "label", new_label, update_modified=False)
            brand_fixed += 1
    # Update ICON_MAP entries for renamed labels
    for old_label, new_label in LABEL_RENAME.items():
        if old_label in ICON_MAP:
            ICON_MAP[new_label] = ICON_MAP.pop(old_label)
    # Re-apply logos for the renamed entries
    for label, icon_file in ICON_MAP.items():
        if label in (LABEL_RENAME.values()):
            url = f"{BASE}/{icon_file}.png"
            rows = frappe.db.get_all("Desktop Icon", filters={"label": label}, fields=["name", "logo_url"])
            for row in rows:
                if row.logo_url != url:
                    frappe.db.set_value("Desktop Icon", row.name, "logo_url", url, update_modified=False)

    frappe.db.commit()
    frappe.cache.delete_key("desktop_icons")
    frappe.cache.delete_value("desktop_icons")
    print(f"Stylo icons: {created} created, {renamed} renamed, {fixed} parent_icon fixed, {link_fixed} links fixed, {updated} logos updated, {brand_fixed} app brands fixed.")
