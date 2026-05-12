import frappe

from stylo_core.license_map import ROUTE_LICENSE_MAP
from stylo_core.user_license import CONTROL_CENTER_URL, has_license

# Paths that are always allowed (assets, auth, API infra)
_ALWAYS_ALLOWED_PREFIXES = (
    "/assets/",
    "/api/method/login",
    "/api/method/logout",
    "/api/method/frappe.auth",
    "/api/method/frappe.client.get_value",
    "/api/method/frappe.boot",
    "/api/method/frappe.utils.boot",
    "/api/method/stylo_core",
    "/favicon.ico",
    "/robots.txt",
)


def check_module_license():
    """before_request hook: block API/page requests for unlicensed route prefixes."""
    if not CONTROL_CENTER_URL:
        return

    user = frappe.session.user if frappe.session else None
    if not user or user in ("Administrator", "Guest"):
        return

    path = frappe.request.path if frappe.request else ""

    # Skip infra paths
    for prefix in _ALWAYS_ALLOWED_PREFIXES:
        if path.startswith(prefix):
            return

    # Check route-level license requirement
    for route_prefix, license_key in ROUTE_LICENSE_MAP.items():
        if path.startswith(route_prefix):
            if not has_license(user, license_key):
                frappe.throw(
                    f"You need a {license_key.upper()} license to access this module. "
                    "Please contact your administrator to upgrade.",
                    frappe.PermissionError,
                )
            return
