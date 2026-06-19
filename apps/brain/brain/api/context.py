import frappe


@frappe.whitelist()
def rebuild():
    """Rebuild the Nuerix site context snapshot. System Manager only."""
    if "System Manager" not in frappe.get_roles():
        frappe.throw("Context rebuild requires System Manager role.", frappe.PermissionError)

    from brain.ai.context_builder import build_and_save
    ctx = build_and_save()
    return {"ok": bool(ctx), "built_at": ctx.get("built_at", "")}


@frappe.whitelist()
def status():
    """Return current context status for display."""
    import os
    path = frappe.get_site_path("private", "files", "brain_context.json")
    exists = os.path.exists(path)
    built_at = frappe.db.get_single_value("Brain Settings", "context_built_at")
    status_val = frappe.db.get_single_value("Brain Settings", "context_status") or "Not Built"
    return {"exists": exists, "built_at": str(built_at or ""), "status": status_val}
