"""
GDPR compliance endpoints for brAIn.

Right to Erasure (Art. 17): anonymizes message content without deleting records
  — preserves the audit trail required by 21 CFR Part 11.

Right to Data Portability (Art. 20): exports all sessions and messages for a user.

These are System Manager-only. Users may request erasure through their admin.
"""
import json

import frappe


def _require_system_manager():
    if "System Manager" not in frappe.get_roles():
        frappe.throw("GDPR tools require System Manager role.", frappe.PermissionError)


@frappe.whitelist()
def export_user_data(user: str):
    """
    Export all Brain chat data for a user as a JSON structure.
    Returns {user, exported_at, sessions: [{session, messages: []}]}
    """
    _require_system_manager()

    sessions = frappe.get_all(
        "Brain Chat Session",
        filters={"user": user},
        fields=["name", "session_title", "status", "started_at", "last_active",
                "closed_at", "ip_address", "provider_used", "model_used",
                "message_count", "data_classification"],
        order_by="started_at asc",
    )

    result = []
    for session in sessions:
        messages = frappe.get_all(
            "Brain Chat Message",
            filters={"session": session.name},
            fields=["name", "sequence", "role", "content", "timestamp",
                    "content_hash", "is_anonymized", "anonymized_at"],
            order_by="sequence asc",
        )
        result.append({"session": session, "messages": messages})

    from brain.ai.audit import write_audit_log
    write_audit_log(
        event_type="gdpr_export",
        detail={"target_user": user, "session_count": len(sessions)},
    )
    frappe.db.commit()

    return {
        "user": user,
        "exported_at": str(frappe.utils.now_datetime()),
        "sessions": result,
    }


@frappe.whitelist()
def anonymize_user_data(user: str, reason: str = "GDPR Right to Erasure Request"):
    """
    Anonymize all Brain message content for a user.
    Replaces content with the GDPR erasure marker; record row is preserved for 21 CFR audit integrity.
    Returns {anonymized_message_count: int, sessions_affected: int}
    """
    _require_system_manager()

    sessions = frappe.get_all(
        "Brain Chat Session",
        filters={"user": user},
        pluck="name",
    )

    if not sessions:
        return {"anonymized_message_count": 0, "sessions_affected": 0}

    now = frappe.utils.now_datetime()
    anonymized_count = 0

    for session_name in sessions:
        messages = frappe.get_all(
            "Brain Chat Message",
            filters={"session": session_name, "is_anonymized": 0},
            pluck="name",
        )
        for msg_name in messages:
            frappe.db.set_value(
                "Brain Chat Message",
                msg_name,
                {
                    "content": "[ANONYMIZED BY GDPR REQUEST]",
                    "is_anonymized": 1,
                    "anonymized_at": now,
                    "anonymized_by": frappe.session.user,
                },
                update_modified=False,
            )
            anonymized_count += 1

    from brain.ai.audit import write_audit_log
    write_audit_log(
        event_type="gdpr_anonymize",
        detail={
            "target_user": user,
            "reason": reason,
            "sessions_affected": len(sessions),
            "messages_anonymized": anonymized_count,
        },
    )
    frappe.db.commit()

    return {
        "anonymized_message_count": anonymized_count,
        "sessions_affected": len(sessions),
    }


@frappe.whitelist()
def verify_audit_chain(limit: int = 1000):
    """
    Verify the SHA-256 hash chain of the Brain Audit Log.
    Returns {ok: bool, broken_at: name|None, checked: int}
    """
    _require_system_manager()

    from brain.ai.audit import verify_chain
    return verify_chain(limit=int(limit))
