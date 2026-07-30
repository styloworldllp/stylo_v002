"""
Mobile API — authentication and data helpers for the Stylo mobile app.

Auth flow:
  1. POST /api/method/login  (standard Frappe, sets session)
  2. GET  stylo_core.mobile_auth.check_mobile_access  — confirm permission
  3. GET  stylo_core.mobile_auth.get_api_keys          — get token pair
  4. From then on: Authorization: token {api_key}:{api_secret}

All subsequent data calls use standard Frappe REST or the helpers below.
"""

import frappe
import secrets


# ─── Permission ────────────────────────────────────────────────────────────────

MOBILE_ROLE = "Mobile App User"


@frappe.whitelist()
def check_mobile_access():
    """
    Return whether the calling user has mobile app access.
    Administrators always have access. Everyone else needs the Mobile App User role.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Not logged in", frappe.AuthenticationError)

    if user == "Administrator":
        return {"has_access": True, "reason": "Administrator"}

    has_role = frappe.db.exists("Has Role", {
        "parent": user,
        "role": MOBILE_ROLE,
        "parenttype": "User",
    })

    return {
        "has_access": bool(has_role),
        "reason": MOBILE_ROLE if has_role else "Role not assigned",
    }


# ─── Keys ──────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_api_keys():
    """
    Generate (or retrieve existing) API key + secret for the calling user.
    Any authenticated user can call this for themselves.
    Returns { api_key, api_secret }.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Not logged in", frappe.AuthenticationError)

    user_doc = frappe.get_doc("User", user)

    if not user_doc.api_key:
        user_doc.api_key = frappe.generate_hash(length=15)

    api_secret = secrets.token_hex(16)
    user_doc.api_secret = api_secret
    user_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "api_key":    user_doc.api_key,
        "api_secret": api_secret,
    }


# ─── Profile ───────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_user_profile():
    """
    Return the calling user's profile, roles, and employee linkage.
    Used by the mobile app after login to populate the auth store.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Not logged in", frappe.AuthenticationError)

    user_doc = frappe.get_doc("User", user)
    roles = [r.role for r in user_doc.get("roles", [])]

    # Find linked employee
    employee = None
    try:
        emp = frappe.db.get_value(
            "Employee",
            {"user_id": user, "status": "Active"},
            ["name", "employee_name", "designation", "department"],
            as_dict=True,
        )
        if emp:
            employee = emp
    except Exception:
        pass

    return {
        "name":        user_doc.name,
        "full_name":   user_doc.full_name,
        "email":       user_doc.email,
        "user_image":  user_doc.user_image or "",
        "roles":       roles,
        "employee":    employee,
        "has_mobile_access": (
            user == "Administrator"
            or frappe.db.exists("Has Role", {
                "parent": user,
                "role": MOBILE_ROLE,
                "parenttype": "User",
            }) is not None
        ),
    }


# ─── Modules ───────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_user_modules():
    """
    Return the list of Frappe workspaces (modules) the user can access,
    with name, icon URL, and route — for the mobile app home screen.
    """
    user = frappe.session.user

    # Fetch all public workspaces
    workspaces = frappe.get_all(
        "Workspace",
        filters={"public": 1, "for_user": ""},
        fields=["name", "title", "icon", "module", "sequence_id"],
        order_by="sequence_id asc",
    )

    result = []
    for ws in workspaces:
        # Permission: check if user has any doctype in this module
        if not _user_can_see_workspace(ws.name, user):
            continue

        icon_url = _get_workspace_icon(ws.name)
        result.append({
            "name":     ws.name,
            "title":    ws.title,
            "icon_url": icon_url,
            "route":    f"/{ws.name.lower().replace(' ', '-')}",
        })

    return result


def _user_can_see_workspace(workspace_name: str, user: str) -> bool:
    """Return True if the user has permission to view at least one link in the workspace."""
    if user == "Administrator":
        return True
    try:
        links = frappe.get_all(
            "Workspace Link",
            filters={"parent": workspace_name, "type": "DocType"},
            fields=["link_to"],
            limit=5,
        )
        for link in links:
            if frappe.has_permission(link.link_to, user=user):
                return True
    except Exception:
        pass
    return False


def _get_workspace_icon(workspace_name: str) -> str:
    """Return the best available icon URL for a workspace."""
    # Check for custom logo in stylo_core desktop_icon fixture
    try:
        icon_row = frappe.db.get_value(
            "Desktop Icon",
            {"label": workspace_name},
            ["logo_url"],
            as_dict=True,
        )
        if icon_row and icon_row.logo_url:
            return icon_row.logo_url
    except Exception:
        pass

    # Fallback: use the Frappe icon name (mobile app maps these to bundled images)
    ws = frappe.db.get_value("Workspace", workspace_name, ["icon"], as_dict=True)
    return ws.icon if ws else ""


# ─── Home Stats ────────────────────────────────────────────────────────────────

@frappe.whitelist()
def get_home_stats():
    """
    Return quick stats for the mobile home screen:
    pending approvals, open CRM leads, today's attendance status.
    """
    user = frappe.session.user
    stats = {}

    # Pending Leave Approvals
    try:
        stats["pending_leaves"] = frappe.db.count("Leave Application", {
            "leave_approver": user,
            "status": "Open",
            "docstatus": 1,
        })
    except Exception:
        stats["pending_leaves"] = 0

    # Pending Expense Approvals
    try:
        stats["pending_expenses"] = frappe.db.count("Expense Claim", {
            "expense_approver": user,
            "approval_status": "Submitted",
            "docstatus": 1,
        })
    except Exception:
        stats["pending_expenses"] = 0

    stats["total_pending_approvals"] = stats["pending_leaves"] + stats["pending_expenses"]

    # Open CRM Leads
    try:
        stats["open_leads"] = frappe.db.count("CRM Lead", {
            "status": ["not in", ["Qualified", "Junk", "Lost"]],
        })
    except Exception:
        stats["open_leads"] = 0

    # Today's attendance
    try:
        emp_id = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
        if emp_id:
            att = frappe.db.get_value(
                "Attendance",
                {"employee": emp_id, "attendance_date": frappe.utils.today()},
                "status",
            )
            stats["attendance_today"] = att or "Not Marked"
        else:
            stats["attendance_today"] = None
    except Exception:
        stats["attendance_today"] = None

    return stats


# ─── Admin: list mobile users ──────────────────────────────────────────────────

@frappe.whitelist()
def get_mobile_users():
    """Return all users with the Mobile App User role (for admin panel)."""
    frappe.only_for("System Manager")

    users = frappe.get_all(
        "User",
        filters={"enabled": 1},
        fields=["name", "full_name", "email", "user_image", "last_login"],
    )

    mobile_users = set(
        r.parent
        for r in frappe.get_all(
            "Has Role",
            filters={"role": MOBILE_ROLE, "parenttype": "User"},
            fields=["parent"],
        )
    )

    return [
        {**u, "has_mobile_access": u.name in mobile_users}
        for u in users
        if u.name not in ["Guest", "Administrator"] or u.name == "Administrator"
    ]


@frappe.whitelist()
def set_mobile_access(user: str, grant: bool):
    """Grant or revoke mobile app access for a user. System Manager only."""
    frappe.only_for("System Manager")

    user_doc = frappe.get_doc("User", user)
    has_role = any(r.role == MOBILE_ROLE for r in user_doc.get("roles", []))

    if grant and not has_role:
        user_doc.append("roles", {"role": MOBILE_ROLE})
        user_doc.save(ignore_permissions=True)
        frappe.db.commit()
    elif not grant and has_role:
        user_doc.set("roles", [r for r in user_doc.get("roles", []) if r.role != MOBILE_ROLE])
        user_doc.save(ignore_permissions=True)
        frappe.db.commit()

    return {"success": True, "has_access": grant}
