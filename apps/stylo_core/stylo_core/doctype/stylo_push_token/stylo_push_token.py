import frappe
from frappe.model.document import Document


class StyloPushToken(Document):
    pass


@frappe.whitelist()
def register_push_token(expo_push_token: str, platform: str = "android") -> None:
    """Called by the mobile app on login to store/update the device push token."""
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("Not authenticated")

    existing = frappe.db.get_value(
        "Stylo Push Token",
        {"user": user, "expo_push_token": expo_push_token},
        "name",
    )
    if existing:
        frappe.db.set_value(
            "Stylo Push Token",
            existing,
            {"last_seen": frappe.utils.now(), "is_active": 1},
        )
    else:
        frappe.get_doc(
            {
                "doctype": "Stylo Push Token",
                "user": user,
                "expo_push_token": expo_push_token,
                "device_platform": platform,
                "last_seen": frappe.utils.now(),
                "is_active": 1,
            }
        ).insert(ignore_permissions=True)

    frappe.db.commit()
