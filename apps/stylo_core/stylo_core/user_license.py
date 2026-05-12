import os

import frappe
import requests

CONTROL_CENTER_URL = os.environ.get("STYLO_CONTROL_URL", "")
SITE_API_KEY = os.environ.get("STYLO_SITE_API_KEY", "")

# Cache key → {email: [license_keys]}
# e.g. {"john@co.com": ["bms", "crm"], "admin@co.com": ["pro"]}
CACHE_KEY = "stylo:user_licenses"
CACHE_TTL = 900  # 15 minutes


def refresh_licensed_users():
    """Scheduled task: pull per-user module licenses from Control Panel every 5 min."""
    if not CONTROL_CENTER_URL or not SITE_API_KEY:
        return

    site_name = frappe.local.site
    try:
        resp = requests.get(
            f"{CONTROL_CENTER_URL}/api/sync/{site_name}/users",
            headers={"X-Site-Api-Key": SITE_API_KEY},
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            # data["users"] = {"email": ["bms", "crm"], ...}
            frappe.cache.set_value(CACHE_KEY, data.get("users", {}), expires_in_sec=CACHE_TTL)
    except Exception:
        pass  # Silently fail — cached list remains active until TTL expires


def _get_all_licenses() -> dict:
    """Return the cached {email: [modules]} dict, refreshing on cache miss."""
    cached = frappe.cache.get_value(CACHE_KEY)
    if cached is None:
        refresh_licensed_users()
        cached = frappe.cache.get_value(CACHE_KEY) or {}
    return cached


def get_user_licenses(email: str) -> list[str]:
    """Return the list of license keys held by this user, e.g. ["bms", "crm"]."""
    return _get_all_licenses().get(email, [])


def has_license(email: str, license_key: str) -> bool:
    """Return True if the user holds the given license key or a Pro license."""
    licenses = get_user_licenses(email)
    return "pro" in licenses or license_key in licenses


@frappe.whitelist()
def get_current_user_licenses():
    """Whitelisted — returns the license list for the logged-in user (for JS gate)."""
    return get_user_licenses(frappe.session.user)


def check_user_license_on_login(login_manager=None):
    """on_login hook: block users with no licenses at all."""
    if not CONTROL_CENTER_URL:
        return

    user = login_manager.user if login_manager else frappe.session.user
    if user in ("Administrator", "Guest"):
        return

    # A user needs at least one license to log in at all
    if not get_user_licenses(user):
        if login_manager:
            login_manager.logout()
        frappe.throw(
            "Your license is not active for this site. Contact your administrator.",
            frappe.AuthenticationError,
        )
