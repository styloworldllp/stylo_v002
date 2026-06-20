"""
Mobile API — authentication helpers for the Stylo mobile app.

These methods are intentionally minimal and safe:
- get_api_keys: generates and returns the calling user's own api_key:api_secret
- get_user_profile: returns name, full_name, email, user_image, and roles
"""

import frappe
import secrets


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

    # Generate new key pair if not already set
    if not user_doc.api_key:
        user_doc.api_key = frappe.generate_hash(length=15)

    # api_secret is stored hashed — regenerate a plaintext secret and save
    api_secret = secrets.token_hex(16)
    user_doc.api_secret = api_secret
    user_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "api_key":    user_doc.api_key,
        "api_secret": api_secret,
    }


@frappe.whitelist()
def get_user_profile():
    """
    Return the calling user's profile and roles.
    Used by the mobile app immediately after login to populate the auth store.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("Not logged in", frappe.AuthenticationError)

    user_doc = frappe.get_doc("User", user)
    roles = [r.role for r in user_doc.get("roles", [])]

    return {
        "name":       user_doc.name,
        "full_name":  user_doc.full_name,
        "email":      user_doc.email,
        "user_image": user_doc.user_image or "",
        "roles":      roles,
    }
