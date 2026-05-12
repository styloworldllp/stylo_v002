# ─────────────────────────────────────────────────────────────────────────────
# stylo_core/license.py
#
# Domain-level license enforcement — runs as a Frappe before_request hook on
# every HTTP request to the bench.
#
# License key format:
#   "{domain}:{YYYY-MM-DD}:{hmac-sha256-signature}"
#
#   • domain    — exact domain or wildcard (e.g. "*.styloworld.io")
#   • expiry    — ISO date; requests after this date are blocked
#   • signature — HMAC-SHA256 of "{domain}:{expiry}" using STYLO_BUILD_SECRET
#
# The secret (STYLO_BUILD_SECRET) is baked into the Docker image at build time
# via a --build-arg.  Keys are generated offline with tools/generate_license.py.
#
# Flow:
#   1. Request comes in → validate_license() is called
#   2. Exempt paths (assets, files, ping) are skipped
#   3. License key is read from site_config.json (set by docker-entrypoint.sh)
#   4. Key is parsed, expiry checked, domain matched, HMAC verified
#   5. On failure → HTTP 403 + license_expired.html template
# ─────────────────────────────────────────────────────────────────────────────
import hashlib
import hmac
import os
from datetime import date, datetime

import frappe

# Baked in at image build time via STYLO_BUILD_SECRET build arg.
# When not set (local dev), license enforcement is skipped entirely.
_SECRET = os.environ.get("STYLO_BUILD_SECRET", "")


def validate_license():
    """before_request hook — blocks requests if the license key is invalid or expired."""
    # No secret = local dev environment; skip all checks
    if not _SECRET:
        return

    # Skip check for static assets, ping, and health endpoints
    path = frappe.request.path if frappe.request else ""
    if _is_exempt_path(path):
        return

    key = (
        frappe.conf.get("stylo_license_key")
        or os.environ.get("STYLO_LICENSE_KEY", "")
    )
    site = frappe.local.site or ""

    if not _is_valid(key, site):
        frappe.local.response.http_status_code = 403
        frappe.local.response.type = "page"
        frappe.local.response.template = "license_expired.html"
        raise frappe.PermissionError("Invalid or expired Stylo license.")


def _is_exempt_path(path: str) -> bool:
    exempt_prefixes = (
        "/assets/",
        "/files/",
        "/private/files/",
        "/api/method/ping",
        "/favicon",
    )
    return any(path.startswith(p) for p in exempt_prefixes)


def _is_valid(key: str, site: str) -> bool:
    if not key or not site or not _SECRET:
        return False

    # Key format: "{domain}:{YYYY-MM-DD}:{hmac_signature}"
    parts = key.split(":")
    if len(parts) != 3:
        return False

    domain, expiry_str, signature = parts

    # Check expiry
    try:
        expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
    except ValueError:
        return False
    if expiry < date.today():
        return False

    # Check domain — supports exact match or wildcard prefix (*.)
    bare_domain = domain.lstrip("*.")
    if not (site == domain or site.endswith("." + bare_domain) or site.startswith(bare_domain)):
        return False

    # Verify HMAC signature
    expected = hmac.new(
        _SECRET.encode(),
        f"{domain}:{expiry_str}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
