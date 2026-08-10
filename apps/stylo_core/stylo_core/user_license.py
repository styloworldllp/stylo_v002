"""
user_license.py — runs on CLIENT sites (not on cloud.stylo.io).

Enforces (Stylo Licensing Architecture V1.0, Phase 1):
1. Site-level license validity (expiry, grace period, suspension, demo bypass)
2. Total user count against licensed user limit (@stylo.io internal users excluded)
3. Per-user module access based on that user's Stylo User License tier + assigned modules
   (module access is per-user, not site-wide — a Manager might have BMS+HR while another
   Manager on the same site has CRM+Desk; both are capped/validated against the site's
   Stylo License.entitled_modules)
4. brAIn is complimentary with every Active Stylo User License — never separately counted
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


def is_unlimited_access() -> bool:
	"""Combined bypass check: config-based demo/unconfigured OR the site's actual
	Stylo License record is in Demo status. Config check runs first (cheap, no DB/network)."""
	if _is_demo_or_unconfigured():
		return True
	return get_site_license_status().get("status") == "demo"


def _is_internal_user(email: str) -> bool:
	"""Verified @stylo.io accounts are Stylo Internal Users — consume zero customer
	licenses, but must still appear in audit logs (see check_user_license_on_login)."""
	if not email or not email.endswith("@stylo.io"):
		return False
	return bool(frappe.db.get_value("User", email, "enabled"))


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


def check_user_count_against_license():
	"""
	Block if TOTAL System Users (active + inactive) >= license limit.
	Every user slot is consumed whether the user is active or not.
	Administrator, Guest, and @stylo.io internal users are excluded from the count.
	"""
	limit = get_user_limit_from_config()
	if limit >= 9999:
		return

	total_users = frappe.db.count("User", {
		"user_type": "System User",
		"name": ["not in", ["Administrator", "Guest"]],
		"email": ["not like", "%@stylo.io"],
	})

	if total_users >= limit:
		frappe.throw(
			f"User license limit reached ({total_users}/{limit} users). "
			"All user slots are consumed — active and inactive users both count. "
			"Contact your Stylo consultant to add more user licenses.",
			frappe.AuthenticationError,
		)


def check_user_count_on_user_create(doc, method=None):
	"""
	Blocks creating a new System User when the license limit is reached.
	Hooked on User before_insert and validate.
	"""
	if getattr(doc, "user_type", "") != "System User":
		return
	if getattr(doc, "name", "") in ("Administrator", "Guest"):
		return
	if _is_internal_user(getattr(doc, "email", "") or getattr(doc, "name", "")):
		return
	if is_unlimited_access():
		return
	check_user_count_against_license()


# ── Module access (per-user) ──────────────────────────────────────────────────

def _get_local_license_doc():
	"""The site's current Stylo License, queried locally (this doctype lives on the same
	site as this code runs — no remote call needed for entitlement data, unlike the
	site-level status check above which is designed for a future multi-site master)."""
	from stylo_core.license_api import _get_active_license

	license_row = _get_active_license(frappe.local.site)
	return frappe.get_doc("Stylo License", license_row.name) if license_row else None


def get_licensed_modules() -> list[str]:
	"""Module keys commercially entitled to this site (Stylo License.entitled_modules).
	This is the company-wide entitlement ceiling — individual users are further capped by
	their own Stylo User License tier/assignment, see get_user_licenses()."""
	license_doc = _get_local_license_doc()
	if license_doc:
		return [m.module_key for m in (license_doc.entitled_modules or [])]

	# Legacy fallback for sites without a local Stylo License record yet.
	if CONTROL_CENTER_URL:
		return _get_cc_licenses().get(frappe.session.user, [])

	return []


def get_user_licenses(email: str) -> list[str]:
	"""
	Returns module keys this user can access, always including "core" and "brain"
	(both automatic — Core is mandatory infra, brAIn is complimentary with every Active
	license, neither is ever gated or counted).

	Administrator always gets everything. A user with an Active Stylo User License gets
	exactly their assigned_modules. A user with NO Stylo User License record yet gets the
	site's full entitled_modules as a temporary rollout safety net (equivalent to implicit
	Pro) — this is deliberate short-term technical debt so existing users aren't locked out
	on deploy day; explicit per-user assignment should close this gap over time.
	"""
	from stylo_core.license_map import ALL_MODULE_KEYS

	if email in ("Administrator", "administrator"):
		return ALL_MODULE_KEYS + ["pro"]

	always_on = ["core", "brain"]

	user_license_name = frappe.db.get_value(
		"Stylo User License", {"user": email, "status": "Active"}, "name"
	)
	if user_license_name:
		doc = frappe.get_cached_doc("Stylo User License", user_license_name)
		return always_on + [m.module_key for m in (doc.assigned_modules or [])]

	return always_on + get_licensed_modules()


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

	if _is_internal_user(user):
		# Zero license consumption, but must still appear in audit logs.
		frappe.logger("stylo_licensing").info(f"Internal user login (unenforced): {user}")
		return

	if is_unlimited_access():
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

	if status in ("suspended", "terminated"):
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
	if not get_licensed_modules():
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
