"""
Auto-fix logic.
For every required field missing from a mapped row, fill a safe default.
All fixes are recorded so the Migration Log shows what was changed.
"""
import frappe
from .schema_map import REQUIRED_DEFAULTS

# Fields that are internal Frappe meta — always strip before insert
_FRAPPE_META_FIELDS = {
    "doctype", "idx", "creation", "owner", "modified_by",
    "__islocal", "__unsaved", "__run_link_triggers",
}

# Fields to always preserve (never strip)
_PRESERVE_FIELDS = {"name", "modified", "docstatus"}


def resolve_default(val):
    """If val is callable, call it; otherwise return as-is."""
    return val() if callable(val) else val


def _v16_required_fields(doctype: str) -> list[str]:
    """Return list of fieldnames marked reqd=1 in v16's DocType meta."""
    try:
        meta = frappe.get_meta(doctype)
        return [f.fieldname for f in meta.fields if f.reqd and f.fieldtype not in
                ("Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Button")]
    except Exception:
        return []


def _link_exists(doctype: str, name: str) -> bool:
    """Check if a linked record already exists in v16."""
    if not name:
        return False
    try:
        return frappe.db.exists(doctype, name)
    except Exception:
        return False


def apply_fixup(doctype: str, row: dict) -> tuple[dict, list[str]]:
    """
    Given a mapped row, auto-fill missing required fields.
    Returns (fixed_row, list_of_fix_notes).
    """
    fixes = []
    result = {k: v for k, v in row.items() if k not in _FRAPPE_META_FIELDS}

    known_defaults = REQUIRED_DEFAULTS.get(doctype, {})
    required = _v16_required_fields(doctype)

    for fieldname in required:
        val = result.get(fieldname)
        if val is not None and val != "":
            continue  # already has a value

        # 1. Use explicitly configured default
        if fieldname in known_defaults:
            default = resolve_default(known_defaults[fieldname])
            result[fieldname] = default
            fixes.append(f"{fieldname}={default!r} (configured default)")
            continue

        # 2. Infer from field type
        try:
            meta = frappe.get_meta(doctype)
            field = meta.get_field(fieldname)
            if not field:
                continue

            if field.fieldtype == "Link":
                # Try to find any existing record in the linked doctype
                linked_dt = field.options
                if linked_dt:
                    existing = frappe.db.get_value(linked_dt, {}, "name")
                    if existing:
                        result[fieldname] = existing
                        fixes.append(f"{fieldname}={existing!r} (first available {linked_dt})")
                    else:
                        result[fieldname] = None
                        fixes.append(f"{fieldname}=None (no {linked_dt} found)")
            elif field.fieldtype == "Select" and field.options:
                first_opt = [o for o in field.options.split("\n") if o.strip()]
                if first_opt:
                    result[fieldname] = first_opt[0]
                    fixes.append(f"{fieldname}={first_opt[0]!r} (first select option)")
            elif field.fieldtype == "Date":
                result[fieldname] = frappe.utils.today()
                fixes.append(f"{fieldname}=today (date default)")
            elif field.fieldtype in ("Int", "Float", "Currency", "Percent"):
                result[fieldname] = 0
                fixes.append(f"{fieldname}=0 (numeric default)")
            elif field.fieldtype in ("Data", "Small Text", "Text", "Long Text"):
                result[fieldname] = ""
                fixes.append(f"{fieldname}='' (text default)")
            elif field.fieldtype == "Check":
                result[fieldname] = 0
                fixes.append(f"{fieldname}=0 (check default)")
        except Exception:
            pass

    # Validate existing Link field values — null out broken links
    try:
        meta = frappe.get_meta(doctype)
        for field in meta.fields:
            if field.fieldtype != "Link" or not field.options:
                continue
            val = result.get(field.fieldname)
            if val and not _link_exists(field.options, val):
                result[field.fieldname] = None
                fixes.append(f"{field.fieldname}: link '{val}' → None (not found in v16)")
    except Exception:
        pass

    return result, fixes
