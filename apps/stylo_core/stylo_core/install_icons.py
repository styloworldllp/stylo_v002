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
    "India Compliance": {
        "link":        "/desk/gst-india",
        "link_to":     "",
        "icon_type":   "Link",
        "link_type":   "External",
        "hidden":      0,
        "parent_icon": "",
        "bg_color":    "",
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
    "Stylo App Store":         "integrations",
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
    "Stylo App Store": {
        "label":       "Stylo App Store",
        "link":        "/app/stylo-marketplace",
        "logo_file":   "integrations",
        "app":         "stylo_core",
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
            fields=["name", "logo_url", "icon_image", "icon"],
        )
        for row in rows:
            updates = {
                "logo_url":   url,
                "icon_image": "",
            }
            # If icon is NULL the desk won't render logo_url — set a fallback icon name
            if not row.get("icon"):
                updates["icon"] = icon_file.split("/")[-1]  # use filename as icon slug
            frappe.db.set_value("Desktop Icon", row.name, updates, update_modified=False)
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

    # ── Step 7: Clean up stale-branded Workspace Sidebar records ──────────────
    # Apps recreate their own sidebars on every migrate/install via fixtures.
    # This step deletes the stale Frappe-branded ones so only Stylo names remain.
    sidebar_fixed = 0

    # CRM app recreates "Frappe CRM" sidebar on every migrate — delete it.
    # The correct sidebar is "Stylo CRM" (also created by the CRM app, module=FCRM).
    if frappe.db.exists("Workspace Sidebar", "Frappe CRM"):
        frappe.delete_doc("Workspace Sidebar", "Frappe CRM", ignore_permissions=True, force=True)
        sidebar_fixed += 1

    # ERPNext creates "ERPNext Settings" sidebar — "BMS Settings" already exists.
    if frappe.db.exists("Workspace Sidebar", "ERPNext Settings") and \
       frappe.db.exists("Workspace Sidebar", "BMS Settings"):
        frappe.delete_doc("Workspace Sidebar", "ERPNext Settings", ignore_permissions=True, force=True)
        sidebar_fixed += 1

    # Mint app creates a "Mint" sidebar — rename to "Stylo Reco".
    if frappe.db.exists("Workspace Sidebar", "Mint") and \
       not frappe.db.exists("Workspace Sidebar", "Stylo Reco"):
        frappe.db.sql("UPDATE `tabWorkspace Sidebar` SET name=%s, title=%s WHERE name=%s",
                      ("Stylo Reco", "Stylo Reco", "Mint"))
        frappe.db.sql("UPDATE `tabWorkspace Sidebar Item` SET parent=%s WHERE parent=%s",
                      ("Stylo Reco", "Mint"))
        frappe.db.sql(
            "UPDATE `tabWorkspace Sidebar Item` SET link_to=%s "
            "WHERE parent=%s AND link_to=%s AND link_type=%s",
            ("Stylo Reco", "Stylo Reco", "Mint", "Workspace")
        )
        sidebar_fixed += 1
    elif frappe.db.exists("Workspace Sidebar", "Mint"):
        frappe.db.set_value("Workspace Sidebar", "Mint", "title", "Stylo Reco", update_modified=False)
        sidebar_fixed += 1

    # Set app_name in System Settings and Website Settings to "Stylo"
    for doctype in ("System Settings", "Website Settings"):
        if frappe.db.exists("DocType", doctype):
            current = frappe.db.get_single_value(doctype, "app_name")
            if current != "Stylo":
                frappe.db.set_single_value(doctype, "app_name", "Stylo")
                sidebar_fixed += 1

    # ── Step 8: Ensure Stylo App Store page exists in DB ─────────────────────
    # Pages require developer_mode to create via ORM, so use SQL directly.
    if not frappe.db.exists("Page", "stylo-marketplace"):
        frappe.db.sql("""
            INSERT IGNORE INTO `tabPage`
              (name, page_name, title, module, standard, docstatus, creation, modified, modified_by, owner)
            VALUES (%s, %s, %s, %s, %s, 0, NOW(), NOW(), %s, %s)
        """, ("stylo-marketplace", "stylo-marketplace", "Stylo App Store",
              "Stylo Core", "Yes", "Administrator", "Administrator"))
        sidebar_fixed += 1

    frappe.db.commit()
    frappe.cache.delete_key("desktop_icons")
    frappe.cache.delete_value("desktop_icons")
    print(f"Stylo icons: {created} created, {renamed} renamed, {fixed} parent_icon fixed, "
          f"{link_fixed} links fixed, {updated} logos updated, {brand_fixed} app brands fixed, "
          f"{sidebar_fixed} sidebars/settings cleaned.")
