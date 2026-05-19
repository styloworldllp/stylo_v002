"""
AI-powered helpers for migration.

Option A — ai_analyze_schema(conn, doctype):
    Compares v14 vs v16 field lists, asks Claude for renames/drops/defaults.
    Results cached in Redis under "migration_ai_schema:<doctype>".

Option B — ai_fix_record(doctype, row, error):
    When a record fails to insert, asks Claude to produce corrected field values.
"""
import json
import frappe


# ── Provider bootstrap ────────────────────────────────────────────────────────

def _get_provider():
    """Reuse brAIn's configured LLM provider (Anthropic/OpenAI/Ollama)."""
    from brain.ai.agent import get_provider, get_settings
    settings = get_settings()
    return get_provider(settings)


def _call_ai(system: str, user_msg: str) -> str:
    """Single-turn call; returns raw text content."""
    provider = _get_provider()
    resp = provider.chat(
        system=system,
        messages=[{"role": "user", "content": user_msg}],
        tools=[],
    )
    return resp.get("content", "")


def _parse_json(text: str) -> dict:
    """Extract first JSON object from a response string."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return {}


# ── Cache helpers ──────────────────────────────────────────────────────────────

_CACHE_KEY = "migration_ai_schema"


def _cache_set(doctype: str, data: dict):
    frappe.cache().hset(_CACHE_KEY, doctype, json.dumps(data))


def _cache_get(doctype: str) -> dict:
    raw = frappe.cache().hget(_CACHE_KEY, doctype)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass
    return {}


def clear_ai_schema_cache():
    frappe.cache().delete_key(_CACHE_KEY)


# ── Option A: Schema analysis ─────────────────────────────────────────────────

def ai_analyze_schema(conn, doctype: str) -> dict:
    """
    Compare v14 vs v16 field lists for doctype and return AI-suggested mapping.
    Result is cached in Redis and returned as:
      {"renames": {old: new}, "dropped": [name,...], "required_defaults": {name: value}}
    """
    from .connection import get_doctype_fields_from_v14

    # Get v14 columns (DB describe)
    try:
        v14_fields = get_doctype_fields_from_v14(conn, doctype)
        v14_names = [f["fieldname"] for f in v14_fields]
    except Exception:
        v14_names = []

    # Get v16 meta
    try:
        meta = frappe.get_meta(doctype)
        v16_fields = [
            {
                "fieldname": f.fieldname,
                "fieldtype": f.fieldtype,
                "label": f.label or "",
                "reqd": bool(f.reqd),
                "options": f.options or "",
            }
            for f in meta.fields
            if f.fieldtype not in (
                "Section Break", "Column Break", "Tab Break",
                "HTML", "Heading", "Button", "Image",
            )
        ]
        v16_names = [f["fieldname"] for f in v16_fields]
    except Exception:
        return {}

    # Only proceed if there are actual differences worth analysing
    only_in_v14 = [n for n in v14_names if n not in v16_names]
    only_in_v16 = [n for n in v16_names if n not in v14_names]
    if not only_in_v14 and not only_in_v16:
        result = {"renames": {}, "dropped": [], "required_defaults": {}}
        _cache_set(doctype, result)
        return result

    system = (
        "You are an ERPNext upgrade expert. "
        "You help migrate data from ERPNext v14 to ERPNext v16. "
        "Return ONLY valid JSON — no prose, no markdown fences."
    )

    prompt = f"""DocType: {doctype}

Fields ONLY in v14 (not in v16):
{json.dumps(only_in_v14)}

Fields ONLY in v16 (not in v14):
{json.dumps(only_in_v16)}

All v16 field definitions:
{json.dumps(v16_fields, indent=2)}

Return a JSON object:
{{
  "renames": {{ "old_v14_fieldname": "new_v16_fieldname" }},
  "dropped": ["v14_fieldname_to_ignore", ...],
  "required_defaults": {{ "v16_fieldname": "safe_default_value" }}
}}

Rules:
- "renames": only include when you are CONFIDENT a v14 field maps to a renamed v16 field (same concept, different name).
- "dropped": v14 fields that have NO equivalent in v16 and should be silently skipped.
- "required_defaults": v16 required fields that v14 records may not have — suggest a safe default value string.
- Do NOT include fields that appear in BOTH v14 and v16 unchanged.
- Do NOT include internal fields like name, docstatus, creation, owner, modified, modified_by, idx."""

    try:
        text = _call_ai(system, prompt)
        result = _parse_json(text)
        # Ensure correct structure
        if not isinstance(result.get("renames"), dict):
            result["renames"] = {}
        if not isinstance(result.get("dropped"), list):
            result["dropped"] = []
        if not isinstance(result.get("required_defaults"), dict):
            result["required_defaults"] = {}
        _cache_set(doctype, result)
        return result
    except Exception as e:
        frappe.log_error(f"AI schema analysis failed for {doctype}: {e}", "Migration AI")
        return {}


def get_ai_schema_override(doctype: str) -> dict:
    """Return cached AI schema map for doctype, or empty dict."""
    return _cache_get(doctype)


# ── Option B: Per-record AI fix ───────────────────────────────────────────────

def ai_fix_record(doctype: str, row: dict, error: str) -> tuple[dict, str]:
    """
    When insert fails, ask AI to patch the record.
    Returns (fixed_row, explanation) — explanation is empty string if AI declined to fix.
    """
    try:
        meta = frappe.get_meta(doctype)
        v16_fields = [
            {
                "fieldname": f.fieldname,
                "fieldtype": f.fieldtype,
                "reqd": bool(f.reqd),
                "options": (f.options or "")[:200],
            }
            for f in meta.fields
            if f.fieldtype not in (
                "Section Break", "Column Break", "Tab Break",
                "HTML", "Heading", "Button", "Image",
            )
        ][:40]  # cap to avoid huge prompt
    except Exception:
        return row, ""

    # Truncate row values so prompt stays manageable
    safe_row = {
        k: (str(v)[:120] if v is not None else None)
        for k, v in list(row.items())[:60]
    }

    system = (
        "You are an ERPNext data migration specialist. "
        "Return ONLY valid JSON — no prose, no markdown fences."
    )

    prompt = f"""DocType: {doctype}
Insert error: {str(error)[:400]}

Record (field values, truncated):
{json.dumps(safe_row, indent=2, default=str)}

v16 field definitions (first 40 fields):
{json.dumps(v16_fields, indent=2)}

The record failed to insert. Return a JSON object:
{{
  "fixes": {{ "fieldname": "corrected_value", ... }},
  "explanation": "one sentence explaining what was wrong and what was changed"
}}

Only include fields that NEED to change to fix the error.
If you cannot determine a safe fix, return {{"fixes": {{}}, "explanation": ""}}."""

    try:
        text = _call_ai(system, prompt)
        result = _parse_json(text)
        fixes = result.get("fixes", {})
        explanation = result.get("explanation", "")
        if fixes and explanation:
            fixed = dict(row)
            fixed.update(fixes)
            return fixed, explanation
    except Exception as e:
        frappe.log_error(f"AI fix failed for {doctype}/{row.get('name')}: {e}", "Migration AI")

    return row, ""
