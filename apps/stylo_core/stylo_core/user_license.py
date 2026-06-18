"""
user_license.py — runs on CLIENT sites (not on cloud.stylo.io).

Enforces:
1. Site-level license validity (expiry, grace period, suspension)
2. Total user count against licensed user limit
3. Module access based on stylo_licensed_modules in site_config
"""

import os

import frappe
import requests

# ── Environment ───────────────────────────────────────────────────────────────

STYLO_CLOUD_URL = os.environ.get("STYLO_CLOUD_URL", "")
LICENSE_CACHE_KEY = "stylo:site_license_status"
LICENSE_CACHE_TTL = 86400  # 24 hours

# Control Center is kept for backward compatibility but no longer primary source
CONTROL_CENTER_URL = os.environ.get("STYLO_CONTROL_URL", "")
SITE_API_KEY = os.environ.get("STYLO_SITE_API_KEY", "")
CACHE_KEY = "stylo:user_licenses"
CACHE_TTL = 900  # 15 minutes


# ── Helper: is this a demo / unconfigured site? ───────────────────────────────

def _is_demo_or_unconfigured() -> bool:
	try:
		return bool(
			not STYLO_CLOUD_URL
			or frappe.conf.get("is_demo")
			or frappe.conf.get("skip_license_check")
		)
	except Exception:
		return True


# ── Site-level license status ─────────────────────────────────────────────────

def get_site_license_status() -> dict:
	"""
	Fetch site license status from Stylo Cloud master.
	Cached for 24 hours. Fails open if master is unreachable.
	"""
	if _is_demo_or_unconfigured():
		return {"status": "active", "user_limit": 9999}

	cached = frappe.cache.get_value(LICENSE_CACHE_KEY)
	if cached:
		return cached

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

	return cached or {"status": "active", "user_limit": 9999}


def invalidate_license_cache():
	frappe.cache.delete_value(LICENSE_CACHE_KEY)


# ── User count enforcement ────────────────────────────────────────────────────

def get_user_limit_from_config() -> int:
	"""Read user limit set during site provisioning."""
	try:
		limit = frappe.conf.get("stylo_user_limit")
		return int(limit) if limit else 9999
	except Exception:
		return 9999


def get_brain_user_limit_from_config() -> int:
	"""Read brAIn-specific user limit from site_config."""
	try:
		limit = frappe.conf.get("brain_user_limit")
		return int(limit) if limit else 0
	except Exception:
		return 0


def check_brain_user_limit():
	"""
	Block assigning the brAIn User role when the brain_user_limit is reached.
	Call this from the Has Role before_insert hook for the brAIn User role.
	"""
	brain_limit = get_brain_user_limit_from_config()
	if brain_limit == 0:
		frappe.throw(
			"brAIn is not licensed for this site. "
			"Contact your Stylo consultant to add the brAIn module.",
			frappe.PermissionError,
		)

	brain_users = frappe.db.count(
		"Has Role",
		{"role": "brAIn User", "parenttype": "User"},
	)
	if brain_users >= brain_limit:
		frappe.throw(
			f"brAIn user limit reached ({brain_users}/{brain_limit}). "
			"Contact your consultant to add more brAIn user slots.",
			frappe.PermissionError,
		)


def check_user_count_against_license():
	"""
	Block if TOTAL System Users (active + inactive) >= license limit.
	Every user slot is consumed whether the user is active or not.
	Administrator and Guest are excluded from the count.
	"""
	limit = get_user_limit_from_config()
	if limit >= 9999:
		return

	total_users = frappe.db.count("User", {
		"user_type": "System User",
		"name": ["not in", ["Administrator", "Guest"]],
	})

	if total_users >= limit:
		frappe.throw(
			f"User license limit reached ({total_users}/{limit} users). "
			"All user slots are consumed — active and inactive users both count. "
			"Contact your Stylo consultant to add more user licenses.",
			frappe.AuthenticationError,
		)


def check_brain_role_limit(doc, method=None):
	"""Hook on Has Role before_insert — blocks brAIn User role when limit reached."""
	if getattr(doc, "role", "") != "brAIn User":
		return
	if _is_demo_or_unconfigured():
		return
	check_brain_user_limit()


def check_user_count_on_user_create(doc, method=None):
	"""
	Blocks creating a new System User when the license limit is reached.
	Hooked on User before_insert and validate.
	"""
	if getattr(doc, "user_type", "") != "System User":
		return
	if getattr(doc, "name", "") in ("Administrator", "Guest"):
		return
	if _is_demo_or_unconfigured():
		return
	check_user_count_against_license()


# ── Module access (site-level) ────────────────────────────────────────────────

def get_licensed_modules() -> list[str]:
	"""
	Returns the list of module keys licensed for this site.
	Source priority:
	  1. site_config.stylo_licensed_modules  (set during provisioning)
	  2. Control Center per-user data        (legacy fallback)

	All users on the site share the same module access — licensing is
	site-level, not per-user.
	"""
	# Priority 1: site_config (primary — set by Stylo Cloud when creating the site)
	site_modules = frappe.conf.get("stylo_licensed_modules", "")
	if site_modules:
		return [m.strip() for m in site_modules.split(",") if m.strip()]

	# Priority 2: Control Center per-user data (legacy / development)
	if CONTROL_CENTER_URL:
		return _get_cc_licenses().get(frappe.session.user, [])

	return []


def get_user_licenses(email: str) -> list[str]:
	"""
	Returns module keys this user can access.
	Administrator always gets everything.
	All other users get the site-level licensed modules.
	"""
	from stylo_core.license_map import ALL_MODULE_KEYS
	if email in ("Administrator", "administrator"):
		return ALL_MODULE_KEYS + ["pro"]

	return get_licensed_modules()


def has_license(email: str, license_key: str) -> bool:
	"""True if the user (and therefore the site) has access to this module key."""
	if email in ("Administrator", "administrator"):
		return True
	modules = get_user_licenses(email)
	return "pro" in modules or license_key in modules


# ── Login hook ────────────────────────────────────────────────────────────────

def check_user_license_on_login(login_manager=None):
	"""
	on_login hook — enforces license on every login attempt.
	"""
	user = login_manager.user if login_manager else frappe.session.user
	if user in ("Administrator", "Guest"):
		return

	if _is_demo_or_unconfigured():
		return

	# 1. Site-level license status
	site_status = get_site_license_status()
	status = site_status.get("status", "active")

	if status == "expired":
		if login_manager:
			login_manager.logout()
		frappe.throw(
			"Your Stylo license has expired. "
			"Please contact your implementation consultant to renew.",
			frappe.AuthenticationError,
		)

	if status == "suspended":
		if login_manager:
			login_manager.logout()
		frappe.throw(
			"This site has been suspended. Please contact your Stylo consultant.",
			frappe.AuthenticationError,
		)

	# 2. Total user count (active + inactive both count)
	check_user_count_against_license()

	# 3. Grace period warning
	if status == "grace_period":
		end_date = site_status.get("end_date", "")
		grace_end = site_status.get("grace_end_date", "")
		frappe.msgprint(
			f"⚠ Your Stylo license expired on {end_date}. "
			f"Grace period ends {grace_end}. "
			"Please contact your consultant to renew.",
			alert=True,
			indicator="orange",
		)

	# 4. Must have at least one licensed module
	if not _is_demo_or_unconfigured() and not get_licensed_modules():
		if login_manager:
			login_manager.logout()
		frappe.throw(
			"No modules are licensed for this site. "
			"Contact your Stylo consultant.",
			frappe.AuthenticationError,
		)


# ── Control Center legacy ─────────────────────────────────────────────────────

def refresh_licensed_users():
	"""Scheduled: refresh Control Center data (legacy, kept for compatibility)."""
	if not CONTROL_CENTER_URL or not SITE_API_KEY:
		return
	try:
		resp = requests.get(
			f"{CONTROL_CENTER_URL}/api/sync/{frappe.local.site}/users",
			headers={"X-Site-Api-Key": SITE_API_KEY},
			timeout=10,
		)
		if resp.ok:
			data = resp.json()
			frappe.cache.set_value(CACHE_KEY, data.get("users", {}), expires_in_sec=CACHE_TTL)
	except Exception:
		pass


def _get_cc_licenses() -> dict:
	cached = frappe.cache.get_value(CACHE_KEY)
	if cached is None:
		refresh_licensed_users()
		cached = frappe.cache.get_value(CACHE_KEY) or {}
	return cached


# ── Whitelisted endpoints ─────────────────────────────────────────────────────

@frappe.whitelist()
def get_current_user_licenses():
	return get_user_licenses(frappe.session.user)


@frappe.whitelist()
def get_site_license_info():
	return get_site_license_status()
