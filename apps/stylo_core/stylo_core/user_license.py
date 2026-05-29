"""
user_license.py — runs on CLIENT sites (not on master).

Two concerns:
1. Per-user module license gating  (via Control Center URL)
2. Site-level license status check (via Stylo Cloud master API)
   — shows grace-period warning or blocks login when expired
"""

import os

import frappe
import requests

# ── Control Center (per-user module gating) ───────────────────────────────

CONTROL_CENTER_URL = os.environ.get("STYLO_CONTROL_URL", "")
SITE_API_KEY = os.environ.get("STYLO_SITE_API_KEY", "")

CACHE_KEY = "stylo:user_licenses"
CACHE_TTL = 900  # 15 minutes

# ── Stylo Cloud master (site-level license) ───────────────────────────────

STYLO_CLOUD_URL = os.environ.get("STYLO_CLOUD_URL", "")
LICENSE_CACHE_KEY = "stylo:site_license_status"
LICENSE_CACHE_TTL = 86400  # 24 hours


# ── Site-level license ────────────────────────────────────────────────────

def _is_demo_or_unconfigured() -> bool:
	"""Returns True if this site is a demo or has no Stylo Cloud URL configured."""
	if not STYLO_CLOUD_URL:
		return True
	try:
		return bool(frappe.db.get_single_value("System Settings", "skip_license_check")
		            or frappe.conf.get("is_demo")
		            or frappe.conf.get("skip_license_check"))
	except Exception:
		return True


def get_site_license_status() -> dict:
	"""
	Call Stylo Cloud master to get this site's license status.
	Result is cached in Redis for 24 hours.
	Fails open (returns active) if master is unreachable — prevents
	false lockouts due to network issues.
	"""
	if _is_demo_or_unconfigured():
		return {"status": "active", "user_limit": 9999}

	cached = frappe.cache.get_value(LICENSE_CACHE_KEY)
	if cached:
		return cached

	if not STYLO_CLOUD_URL:
		# No master configured — development mode, treat as active
		return {"status": "active", "user_limit": 9999}

	try:
		resp = requests.get(
			f"{STYLO_CLOUD_URL}/api/method/stylo_core.license_api.check",
			params={"site": frappe.local.site},
			timeout=5,
		)
		if resp.ok:
			status = resp.json().get("message", {})
			frappe.cache.set_value(LICENSE_CACHE_KEY, status, expires_in_sec=LICENSE_CACHE_TTL)
			return status
	except Exception:
		pass

	# Fail open — use cached value if available, else assume active
	return cached or {"status": "active", "user_limit": 9999}


def invalidate_license_cache():
	"""Call this after a license is released so the site picks it up immediately."""
	frappe.cache.delete_value(LICENSE_CACHE_KEY)


def check_user_license_on_login(login_manager=None):
	"""
	on_login hook — runs on every login.
	1. Checks site-level license (block/warn if expired/grace)
	2. Checks per-user module license (block if no modules)
	"""
	user = login_manager.user if login_manager else frappe.session.user
	if user in ("Administrator", "Guest"):
		return

	if _is_demo_or_unconfigured():
		return  # Demo or unconfigured — no license checks

	# ── Site-level check ──────────────────────────────────────────────────
	site_status = get_site_license_status()
	status = site_status.get("status", "active")

	if status == "expired":
		if login_manager:
			login_manager.logout()
		frappe.throw(
			"Your Stylo license has expired. Please contact your implementation consultant to renew.",
			frappe.AuthenticationError,
		)

	if status == "suspended":
		if login_manager:
			login_manager.logout()
		frappe.throw(
			"This site has been suspended. Please contact your Stylo consultant.",
			frappe.AuthenticationError,
		)

	if status == "grace_period":
		end_date = site_status.get("end_date", "")
		grace_end = site_status.get("grace_end_date", "")
		frappe.msgprint(
			f"⚠ Your Stylo license expired on {end_date}. "
			f"Grace period ends {grace_end}. "
			"Please contact your consultant to renew and avoid a site lock.",
			alert=True,
			indicator="orange",
		)

	# ── Per-user module check (Control Center) ────────────────────────────
	if not CONTROL_CENTER_URL:
		return

	if not get_user_licenses(user):
		if login_manager:
			login_manager.logout()
		frappe.throw(
			"Your license is not active for this site. Contact your administrator.",
			frappe.AuthenticationError,
		)


# ── Per-user module gating ────────────────────────────────────────────────

def refresh_licensed_users():
	"""Scheduled task: pull per-user module licenses from Control Center every 5 min."""
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
			frappe.cache.set_value(CACHE_KEY, data.get("users", {}), expires_in_sec=CACHE_TTL)
	except Exception:
		pass


def _get_all_licenses() -> dict:
	cached = frappe.cache.get_value(CACHE_KEY)
	if cached is None:
		refresh_licensed_users()
		cached = frappe.cache.get_value(CACHE_KEY) or {}
	return cached


_ALL_LICENSES = ["pro", "bms", "crm", "hr", "lms"]


def get_user_licenses(email: str) -> list[str]:
	if email in ("Administrator", "administrator"):
		return _ALL_LICENSES
	return _get_all_licenses().get(email, [])


def has_license(email: str, license_key: str) -> bool:
	if email in ("Administrator", "administrator"):
		return True
	licenses = get_user_licenses(email)
	return "pro" in licenses or license_key in licenses


@frappe.whitelist()
def get_current_user_licenses():
	return get_user_licenses(frappe.session.user)


@frappe.whitelist()
def get_site_license_info():
	"""Whitelisted — returns license status for the JS lock screen check."""
	return get_site_license_status()
