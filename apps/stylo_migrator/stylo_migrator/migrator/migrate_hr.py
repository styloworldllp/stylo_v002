"""
HR / Payroll special handling.

The main changes from v14 → v15/v16:
- Payroll Entry, Salary Slip, Salary Structure moved to the 'hrms' app
- Employee fields like salary_currency, ctc removed (handled by schema_map DROPPED_FIELDS)
- Leave Policy Assignment is a new DocType in v16 (was just a field on Employee in v14)
"""
import frappe

HRMS_DOCTYPES = {
    "Salary Component",
    "Salary Structure",
    "Salary Structure Assignment",
    "Salary Slip",
    "Payroll Entry",
    "Employee Benefit Application",
    "Employee Benefit Claim",
    "Additional Salary",
    "Employee Tax Exemption Declaration",
    "Employee Tax Exemption Proof Submission",
    "Full and Final Statement",
    "Gratuity",
    "Income Tax Slab",
    "Payroll Period",
}


def hrms_installed() -> bool:
    """Check if the hrms app is installed on this site."""
    try:
        return "hrms" in frappe.get_installed_apps()
    except Exception:
        return False


def should_skip(doctype: str) -> tuple[bool, str]:
    """Return (skip, reason) for HR doctypes that require hrms."""
    if doctype in HRMS_DOCTYPES and not hrms_installed():
        return True, "hrms app not installed — skipping payroll DocType"
    return False, ""


def patch_employee_row(row: dict) -> dict:
    """
    Clean up an Employee row for v16.
    - Ensure date_of_birth and date_of_joining are valid
    - Map old status values
    """
    row = dict(row)

    # Status mapping
    status_map = {"Left": "Left", "Active": "Active", "Suspended": "Active", "Notice Period": "Active"}
    if row.get("status") and row["status"] not in ("Active", "Left", "On Leave"):
        row["status"] = status_map.get(row["status"], "Active")

    # If no date_of_joining set a safe fallback
    if not row.get("date_of_joining"):
        row["date_of_joining"] = frappe.utils.today()

    return row


def patch_salary_structure_row(row: dict) -> dict:
    """Ensure Salary Structure has is_active and currency."""
    row = dict(row)
    if not row.get("is_active"):
        row["is_active"] = "Yes"
    if not row.get("currency"):
        row["currency"] = frappe.defaults.get_global_default("currency") or "INR"
    return row


def patch_salary_slip_row(row: dict) -> dict:
    """Ensure Salary Slip has start/end date and posting_date."""
    row = dict(row)
    today = frappe.utils.today()
    if not row.get("posting_date"):
        row["posting_date"] = today
    if not row.get("start_date"):
        row["start_date"] = today
    if not row.get("end_date"):
        row["end_date"] = today
    return row


# Registry: called by engine.py before fixup for HR doctypes
HR_PATCHERS = {
    "Employee": patch_employee_row,
    "Salary Structure": patch_salary_structure_row,
    "Salary Slip": patch_salary_slip_row,
}


def apply_hr_patch(doctype: str, row: dict) -> dict:
    patcher = HR_PATCHERS.get(doctype)
    return patcher(row) if patcher else row
