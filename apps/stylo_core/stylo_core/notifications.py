import json
import frappe
import requests


EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def get_expo_tokens_for_user(user: str) -> list[str]:
    return frappe.db.get_all(
        "Stylo Push Token",
        filters={"user": user, "is_active": 1},
        pluck="expo_push_token",
    )


def send_expo_push(tokens: list[str], title: str, body: str, data: dict | None = None) -> None:
    if not tokens:
        return

    messages = [
        {
            "to": token,
            "sound": "default",
            "title": title,
            "body": body,
            "data": data or {},
        }
        for token in tokens
    ]

    try:
        requests.post(
            EXPO_PUSH_URL,
            json=messages,
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Expo Push Notification Failed")


def push_workflow_notification(doc, method=None):
    """
    Fired via doc_events on Workflow Action after_insert.
    Sends a push notification to the assigned approver.
    """
    if doc.status != "Open" or not doc.user:
        return

    tokens = get_expo_tokens_for_user(doc.user)
    if not tokens:
        return

    doctype = doc.reference_doctype
    docname = doc.reference_name

    send_expo_push(
        tokens,
        title=f"Approval Required — {doctype}",
        body=f"{docname} is waiting for your approval.",
        data={
            "doctype": doctype,
            "docname": docname,
            "workflow_action": doc.name,
        },
    )
