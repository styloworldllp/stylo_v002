# Workspace/route → module key mapping for Stylo license enforcement.
#
# Module keys — the 7 commercially-countable modules per Stylo Licensing Architecture V1.0,
# plus `brain` (complimentary, never counted, kept here only for workspace-mapping/bypass
# purposes — see stylo_core/user_license.py):
#   bms      — Core ERP: Finance, Buying, Selling, Inventory, Quality, Assets, Manufacturing,
#              Projects & Timesheets, GST/India Compliance, and Reco (bank reconciliation) —
#              all bundled into BMS, none separately licensable (V1.0 decision)
#   hr       — HRMS: Payroll, Leave, Attendance, Appraisals, Recruitment
#   crm      — CRM: Leads, Deals, Pipeline
#   lms      — Learning: Courses, Certifications, Batches
#   desk     — Helpdesk: Tickets, SLA, Knowledge Base
#   insights — BI Dashboards & Analytics ("Stylo Analytics")
#   lending  — Loan & lending management
#   brain    — brAIn AI Assistant (complimentary with every Active Stylo User License)
#   pro      — wildcard, grants all modules

WORKSPACE_LICENSE_MAP: dict[str, str] = {
    # ── BMS (Core ERP) ────────────────────────────────────────────────────────
    "Accounting":           "bms",
    "Accounts Setup":       "bms",
    "Assets":               "bms",
    "Banking":              "bms",
    "Budget":               "bms",
    "Buying":               "bms",
    "Financial Reports":    "bms",
    "Invoicing":            "bms",
    "Payments":             "bms",
    "Quality":              "bms",
    "Selling":              "bms",
    "Share Management":     "bms",
    "Stock":                "bms",
    "Subcontracting":       "bms",
    "Subscription":         "bms",
    "Taxes":                "bms",
    "StyloBMS":             "bms",
    "BMS Settings":         "bms",
    "BMS CRM":              "bms",
    "Accounting":           "bms",

    # ── Manufacturing, Projects, GST/India Compliance — bundled into BMS, not
    #    separately licensable (V1.0 decision) ──────────────────────────────────
    "Manufacturing":        "bms",
    "Projects":             "bms",
    "GST India":            "bms",
    "Income Tax India":     "bms",
    "India Compliance":     "bms",

    # ── HRMS ───────────────────────────────────────────────────────────────────
    "HRMS":                 "hr",
    "HR Setup":             "hr",
    "Leaves":               "hr",
    "Payroll":              "hr",
    "Performance":          "hr",
    "Recruitment":          "hr",
    "Shift & Attendance":   "hr",
    "Tax & Benefits":       "hr",
    "Tenure":               "hr",
    "Expenses":             "hr",

    # ── CRM ────────────────────────────────────────────────────────────────────
    "Stylo CRM":            "crm",
    "CRM":                  "crm",

    # ── LMS ────────────────────────────────────────────────────────────────────
    "Learning":             "lms",

    # ── Desk (Helpdesk) ────────────────────────────────────────────────────────
    "Helpdesk":             "desk",

    # ── Lending ────────────────────────────────────────────────────────────────
    "Lending":              "lending",
}

# URL route prefix → module key.
ROUTE_LICENSE_MAP: dict[str, str] = {
    "/crm":       "crm",
    "/lms":       "lms",
    "/helpdesk":  "desk",
    "/insights":  "insights",
    "/reco":      "bms",      # Bank reconciliation — part of BMS Finance
}

# Workspaces always accessible — no license required.
UNLICENSED_WORKSPACES: set[str] = {
    "My Workspaces",
    "Automation",
    "Build",
    "Data",
    "Email",
    "System",
    "Users",
    "Website",
    "Integrations",
    "Organization",
    "Printing",
    "Home",
    "Stylo",
}

# All module keys used for workspace/route mapping. `brain` is complimentary and never
# commercially counted — see COMMERCIAL_MODULE_KEYS below for the 7 that actually are.
ALL_MODULE_KEYS: list[str] = [
    "bms",
    "hr",
    "crm",
    "lms",
    "desk",
    "brain",
    "insights",
    "lending",
]

# The 7 commercially-countable modules per Stylo Licensing Architecture V1.0 — used as the
# Select options on Stylo License Module / Stylo User License Module. `brain` and `core` are
# deliberately excluded: brain is complimentary, core is mandatory infra, neither is ever an
# entitlement/assignment row.
COMMERCIAL_MODULE_KEYS: list[str] = [
    "bms",
    "hr",
    "crm",
    "lms",
    "desk",
    "insights",
    "lending",
]

# Human-readable names for display in UI / License Requests
MODULE_DISPLAY_NAMES: dict[str, str] = {
    "bms":      "StyloBMS",
    "hr":       "StyloHR",
    "crm":      "StyloCRM",
    "lms":      "StyloLMS",
    "desk":     "StyloDesk",
    "brain":    "brAIn",
    "insights": "Stylo Analytics",
    "lending":  "Stylo Lending",
    "pro":      "All Modules",
}
