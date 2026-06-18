"""
Nuerix Site Context Builder
============================
Builds a compact, pre-computed knowledge snapshot of the current Frappe site.
Saved to {site}/private/files/brain_context.json.

This is loaded into the system prompt so Nuerix answers with full company
awareness without needing to fetch data on every query.

Call build_and_save() to rebuild. Safe to enqueue.
"""
import json
import os

import frappe
import frappe.utils


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_and_save() -> dict:
    """Build the full context and save it. Returns the context dict."""
    frappe.db.set_single_value("Brain Settings", "context_status", "Building…")

    try:
        ctx = _build()
        _save(ctx)
        frappe.db.set_single_value("Brain Settings", "context_status", "Ready")
        frappe.db.set_single_value(
            "Brain Settings", "context_built_at", frappe.utils.now_datetime()
        )
        frappe.db.commit()
        return ctx
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Brain Context Build Failed")
        frappe.db.set_single_value("Brain Settings", "context_status", "Error — check log")
        frappe.db.commit()
        return {}


def load() -> str:
    """Return pre-built context as a formatted string for the system prompt. Empty if not built."""
    path = _context_path()
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r") as f:
            ctx = json.load(f)
        return _format_for_prompt(ctx)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def _build() -> dict:
    ctx = {}

    ctx["company"] = _get_company_info()
    ctx["modules"] = _get_module_stats()
    ctx["masters"] = _get_key_masters()
    ctx["recent_activity"] = _get_recent_activity()
    ctx["custom"] = _get_custom_context()
    ctx["built_at"] = str(frappe.utils.now_datetime())
    ctx["site"] = frappe.local.site

    return ctx


def _get_company_info() -> dict:
    try:
        companies = frappe.get_all(
            "Company",
            fields=["name", "country", "default_currency", "fiscal_year_start_date",
                    "abbr", "phone_no", "email", "website"],
            limit=5,
        )
        # Get active fiscal year
        fy = frappe.db.get_value(
            "Fiscal Year",
            {"disabled": 0},
            ["year", "year_start_date", "year_end_date"],
            as_dict=True,
        ) or {}
        return {"companies": companies, "fiscal_year": fy}
    except Exception:
        return {}


def _get_module_stats() -> dict:
    """Record counts for major DocTypes across all modules."""
    doctypes_to_check = [
        # Finance
        ("Sales Invoice", "grand_total"),
        ("Purchase Invoice", "grand_total"),
        ("Payment Entry", "paid_amount"),
        ("Journal Entry", None),
        # Sales / CRM
        ("Customer", None),
        ("Sales Order", "grand_total"),
        ("Quotation", None),
        ("CRM Lead", None),
        ("CRM Deal", None),
        # Purchase
        ("Supplier", None),
        ("Purchase Order", "grand_total"),
        # Inventory
        ("Item", None),
        ("Stock Entry", None),
        ("Warehouse", None),
        # HR
        ("Employee", None),
        ("Leave Application", None),
        ("Attendance", None),
        ("Salary Slip", "net_pay"),
        ("Expense Claim", "total_claimed_amount"),
        # Projects
        ("Project", None),
        ("Task", None),
    ]

    stats = {}
    for dt, amount_field in doctypes_to_check:
        try:
            if not frappe.db.table_exists(f"tab{dt}"):
                continue
            count = frappe.db.count(dt)
            entry = {"count": count}
            if amount_field and count > 0:
                total = frappe.db.sql(
                    f"SELECT SUM(`{amount_field}`) FROM `tab{dt}` WHERE docstatus=1",
                )[0][0] or 0
                entry["total_submitted_amount"] = round(float(total), 2)
            stats[dt] = entry
        except Exception:
            pass

    return stats


def _get_key_masters() -> dict:
    masters = {}

    # Top 10 customers by total invoiced
    try:
        if frappe.db.table_exists("tabSales Invoice"):
            top_customers = frappe.db.sql("""
                SELECT customer, SUM(grand_total) as total
                FROM `tabSales Invoice`
                WHERE docstatus = 1
                GROUP BY customer
                ORDER BY total DESC
                LIMIT 10
            """, as_dict=True)
            masters["top_customers"] = [
                {"name": r.customer, "total": round(float(r.total or 0), 2)}
                for r in top_customers
            ]
    except Exception:
        pass

    # Top 10 suppliers by total purchase invoiced
    try:
        if frappe.db.table_exists("tabPurchase Invoice"):
            top_suppliers = frappe.db.sql("""
                SELECT supplier, SUM(grand_total) as total
                FROM `tabPurchase Invoice`
                WHERE docstatus = 1
                GROUP BY supplier
                ORDER BY total DESC
                LIMIT 10
            """, as_dict=True)
            masters["top_suppliers"] = [
                {"name": r.supplier, "total": round(float(r.total or 0), 2)}
                for r in top_suppliers
            ]
    except Exception:
        pass

    # Item groups
    try:
        item_groups = frappe.get_all("Item Group", fields=["name"], filters={"is_group": 0}, limit=30)
        masters["item_groups"] = [g.name for g in item_groups]
    except Exception:
        pass

    # Departments
    try:
        depts = frappe.get_all("Department", pluck="name", limit=20)
        masters["departments"] = depts
    except Exception:
        pass

    # Warehouses
    try:
        wh = frappe.get_all("Warehouse", fields=["name", "warehouse_type"], limit=15)
        masters["warehouses"] = [{"name": w.name, "type": w.warehouse_type} for w in wh]
    except Exception:
        pass

    # Currencies used
    try:
        currencies = frappe.db.sql(
            "SELECT DISTINCT default_currency FROM `tabCompany` WHERE default_currency IS NOT NULL",
            as_list=True,
        )
        masters["currencies"] = [c[0] for c in currencies if c[0]]
    except Exception:
        pass

    return masters


def _get_recent_activity() -> dict:
    """Last 30 days activity summary."""
    recent = {}
    thirty_days_ago = frappe.utils.add_days(frappe.utils.today(), -30)

    checks = [
        ("Sales Invoice", "posting_date", "grand_total"),
        ("Purchase Invoice", "posting_date", "grand_total"),
        ("Sales Order", "transaction_date", "grand_total"),
        ("Employee Checkin", "time", None),
        ("Leave Application", "from_date", None),
    ]

    for dt, date_field, amount_field in checks:
        try:
            if not frappe.db.table_exists(f"tab{dt}"):
                continue
            count = frappe.db.count(dt, {date_field: [">=", thirty_days_ago]})
            entry = {"last_30_days_count": count}
            if amount_field and count > 0:
                total = frappe.db.sql(
                    f"SELECT SUM(`{amount_field}`) FROM `tab{dt}` WHERE `{date_field}` >= %s AND docstatus=1",
                    (thirty_days_ago,),
                )[0][0] or 0
                entry["last_30_days_amount"] = round(float(total), 2)
            recent[dt] = entry
        except Exception:
            pass

    return recent


def _get_custom_context() -> str:
    try:
        return frappe.db.get_single_value("Brain Settings", "custom_context") or ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Save / Load helpers
# ---------------------------------------------------------------------------

def _context_path() -> str:
    return frappe.get_site_path("private", "files", "brain_context.json")


def _save(ctx: dict):
    path = _context_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(ctx, f, indent=2, default=str)


def _format_for_prompt(ctx: dict) -> str:
    lines = ["\n## Company Knowledge Base (Pre-Built — Nuerix Site Context)"]

    # Company info
    company_info = ctx.get("company", {})
    companies = company_info.get("companies", [])
    if companies:
        c = companies[0]
        lines.append(f"- **Company**: {c.get('name', '')} ({c.get('abbr', '')})")
        lines.append(f"- **Country**: {c.get('country', '')} | **Currency**: {c.get('default_currency', '')}")
        fy = company_info.get("fiscal_year", {})
        if fy:
            lines.append(f"- **Fiscal Year**: {fy.get('year', '')} ({fy.get('year_start_date','')} → {fy.get('year_end_date','')})")

    # Module stats
    stats = ctx.get("modules", {})
    if stats:
        lines.append("\n### Record Counts")
        for dt, info in stats.items():
            count = info.get("count", 0)
            amount = info.get("total_submitted_amount")
            if count > 0:
                line = f"- {dt}: **{count:,}** records"
                if amount:
                    line += f" | submitted total: {amount:,.2f}"
                lines.append(line)

    # Key masters
    masters = ctx.get("masters", {})
    if masters.get("top_customers"):
        lines.append("\n### Top Customers (by Revenue)")
        for c in masters["top_customers"][:5]:
            lines.append(f"- {c['name']}: {c['total']:,.2f}")

    if masters.get("top_suppliers"):
        lines.append("\n### Top Suppliers (by Purchase)")
        for s in masters["top_suppliers"][:5]:
            lines.append(f"- {s['name']}: {s['total']:,.2f}")

    if masters.get("item_groups"):
        lines.append(f"\n### Item Groups: {', '.join(masters['item_groups'][:15])}")

    if masters.get("departments"):
        lines.append(f"### Departments: {', '.join(masters['departments'][:10])}")

    if masters.get("warehouses"):
        wh_names = [w["name"] for w in masters["warehouses"]]
        lines.append(f"### Warehouses: {', '.join(wh_names[:10])}")

    # Recent activity
    recent = ctx.get("recent_activity", {})
    if recent:
        lines.append("\n### Last 30 Days Activity")
        for dt, info in recent.items():
            c = info.get("last_30_days_count", 0)
            a = info.get("last_30_days_amount")
            if c > 0:
                line = f"- {dt}: {c} recent"
                if a:
                    line += f" | {a:,.2f}"
                lines.append(line)

    # Custom context (admin-defined)
    custom = ctx.get("custom", "").strip()
    if custom:
        lines.append(f"\n### Additional Company Context (Admin-Defined)\n{custom}")

    built_at = ctx.get("built_at", "")
    if built_at:
        lines.append(f"\n*Context snapshot built at: {built_at}*")

    return "\n".join(lines)
