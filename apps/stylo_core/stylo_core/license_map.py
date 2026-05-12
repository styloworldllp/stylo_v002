# Workspace name → license key mapping.
# Keep granular (workspace/route level) so individual modules can be
# independently licensed without touching this file's consumers.
#
# License keys: bms | crm | hr | lms | pro
# "pro" is a wildcard that grants access to everything.

WORKSPACE_LICENSE_MAP: dict[str, str] = {
    # ── StyloBMS ──────────────────────────────────────────────────
    "Accounting":          "bms",
    "Accounts Setup":      "bms",
    "Assets":              "bms",
    "Banking":             "bms",
    "Budget":              "bms",
    "Buying":              "bms",
    "Financial Reports":   "bms",
    "Home":                "bms",
    "Integrations":        "bms",
    "Invoicing":           "bms",
    "Manufacturing":       "bms",
    "Organization":        "bms",
    "Payments":            "bms",
    "Printing":            "bms",
    "Projects":            "bms",
    "Quality":             "bms",
    "Selling":             "bms",
    "Share Management":    "bms",
    "Stock":               "bms",
    "StyloBMS":            "bms",
    "StyloBMS Settings":   "bms",
    "Subcontracting":      "bms",
    "Subscription":        "bms",
    "Taxes":               "bms",
    "Tax & Benefits":      "bms",
    "GST India":           "bms",
    "Income Tax India":    "bms",
    "India Compliance":    "bms",
    "Helpdesk":            "bms",
    # ── StyloHR ───────────────────────────────────────────────────
    "HRMS":                "hr",
    "HR Setup":            "hr",
    "Leaves":              "hr",
    "Payroll":             "hr",
    "Performance":         "hr",
    "Recruitment":         "hr",
    "Shift & Attendance":  "hr",
    "Tenure":              "hr",
    # ── StyloCRM ──────────────────────────────────────────────────
    "Frappe CRM":          "crm",
    # ── StyloLMS ──────────────────────────────────────────────────
    "LMS":                 "lms",
}

# URL route prefix → license key.
# Checked against frappe.request.path before WORKSPACE_LICENSE_MAP.
ROUTE_LICENSE_MAP: dict[str, str] = {
    "/crm":        "crm",
    "/lms":        "lms",
    "/helpdesk":   "bms",
}

# Workspaces always accessible regardless of license (Stylo infra pages).
UNLICENSED_WORKSPACES: set[str] = {
    "My Workspaces",
    "Automation",
    "Build",
    "Data",
    "Email",
    "System",
    "Users",
    "Website",
}
