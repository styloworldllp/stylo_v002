"""
21 CFR Part 11 compliant audit log writer for brAIn.

Every event is written as an immutable Brain Audit Log record with SHA-256
hash chaining — each entry's hash incorporates the previous entry's hash,
making any tampering detectable by a chain-verification scan.

Usage:
    from brain.ai.audit import write_audit_log

    write_audit_log(
        event_type="user_message",
        session=session_name,
        detail={"message_id": msg_name, "char_count": len(content)},
    )
"""
import hashlib
import json

import frappe


def _get_previous_hash(site: str) -> str:
    """Return the entry_hash of the most recent audit log for this site."""
    result = frappe.db.sql(
        """
        SELECT entry_hash FROM `tabBrain Audit Log`
        WHERE site_name = %s
        ORDER BY timestamp DESC, creation DESC
        LIMIT 1
        """,
        (site,),
        as_dict=False,
    )
    return result[0][0] if result else "0" * 64


def _compute_hash(timestamp: str, event_type: str, actor: str, detail_json: str, previous_hash: str) -> str:
    raw = f"{timestamp}|{event_type}|{actor}|{detail_json}|{previous_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()


def write_audit_log(
    event_type: str,
    detail: dict,
    session: str = None,
    actor: str = None,
) -> str:
    """
    Write a single audit log entry. Returns the new entry's name (UUID).

    Args:
        event_type: One of the Select options in Brain Audit Log doctype.
        detail: Arbitrary dict — stored as JSON in event_detail.
        session: Name of the Brain Chat Session (optional for settings_change events).
        actor: Frappe user ID. Defaults to frappe.session.user.
    """
    try:
        s = frappe.db.get_singles_dict("Brain Settings")
        if not frappe.utils.cint(s.get("enable_audit_trail", 1)):
            return ""
    except Exception:
        return ""

    site = frappe.local.site
    actor = actor or frappe.session.user
    now = frappe.utils.now_datetime()
    now_str = str(now)
    detail_json = json.dumps(detail, default=str)

    previous_hash = _get_previous_hash(site)
    entry_hash = _compute_hash(now_str, event_type, actor, detail_json, previous_hash)

    try:
        log = frappe.get_doc({
            "doctype": "Brain Audit Log",
            "session": session,
            "event_type": event_type,
            "actor": actor,
            "timestamp": now,
            "site_name": site,
            "data_classification": s.get("data_classification") or "Regulated (21 CFR)",
            "ip_address": _get_ip(),
            "event_detail": detail_json,
            "previous_hash": previous_hash,
            "entry_hash": entry_hash,
        })
        # Bypass on_update guard — this is the initial insert, not an edit
        log.flags.ignore_on_update = True
        log.insert(ignore_permissions=True)
        frappe.db.commit()
        return log.name
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Brain Audit Log write failed")
        return ""


def _get_ip() -> str:
    try:
        return frappe.local.request.environ.get("REMOTE_ADDR", "")
    except Exception:
        return ""


def verify_chain(limit: int = 1000) -> dict:
    """
    Walk the audit log chain (oldest-first) and verify every hash.
    Returns {ok: bool, broken_at: name|None, checked: int}.
    """
    site = frappe.local.site
    entries = frappe.db.sql(
        """
        SELECT name, timestamp, event_type, actor, event_detail, previous_hash, entry_hash
        FROM `tabBrain Audit Log`
        WHERE site_name = %s
        ORDER BY timestamp ASC, creation ASC
        LIMIT %s
        """,
        (site, limit),
        as_dict=True,
    )

    expected_prev = "0" * 64
    for entry in entries:
        expected = _compute_hash(
            str(entry.timestamp),
            entry.event_type,
            entry.actor,
            entry.event_detail or "{}",
            expected_prev,
        )
        if expected != entry.entry_hash:
            return {"ok": False, "broken_at": entry.name, "checked": entries.index(entry) + 1}
        expected_prev = entry.entry_hash

    return {"ok": True, "broken_at": None, "checked": len(entries)}
