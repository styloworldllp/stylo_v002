# Workspace/route → module key mapping for Stylo license enforcement.
#
# Module keys (each is a separately purchasable add-on):
#   bms           — Core ERP: Finance, Buying, Selling, Inventory, Quality, Assets
#   manufacturing — Manufacturing: BOM, Work Orders, Job Cards
#   projects      — Projects & Timesheets
#   gst           — India Compliance: GST, Income Tax India
#   hr            — HRMS: Payroll, Leave, Attendance, Appraisals, Recruitment
#   crm           — CRM: Leads, Deals, Pipeline
#   lms           — Learning: Courses, Certifications, Batches
#   desk          — Helpdesk: Tickets, SLA, Knowledge Base
#   brain         — brAIn AI Assistant
#   insights      — BI Dashboards & Analytics
#   pro           — wildcard, grants all modules

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

    # ── Manufacturing ──────────────────────────────────────────────────────────
    "Manufacturing":        "manufacturing",

    # ── Projects ───────────────────────────────────────────────────────────────
    "Projects":             "projects",

    # ── GST / India Compliance ─────────────────────────────────────────────────
    "GST India":            "gst",
    "Income Tax India":     "gst",
    "India Compliance":     "gst",

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

# All purchasable module keys
ALL_MODULE_KEYS: list[str] = [
    "bms",
    "manufacturing",
    "projects",
    "gst",
    "hr",
    "crm",
    "lms",
    "desk",
    "brain",
    "insights",
]

# Human-readable names for display in UI / License Requests
MODULE_DISPLAY_NAMES: dict[str, str] = {
    "bms":           "StyloBMS",
    "manufacturing": "Manufacturing",
    "projects":      "Projects",
    "gst":           "GST & India Compliance",
    "hr":            "StyloHR",
    "crm":           "StyloCRM",
    "lms":           "StyloLMS",
    "desk":          "StyloDesk",
    "brain":         "brAIn",
    "insights":      "Stylo Insights",
    "pro":           "All Modules",
}
